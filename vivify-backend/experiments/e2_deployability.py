"""E2 - Deployability Feedback Loop: Measure passItr@n"""

import asyncio
import time
import uuid
from typing import Dict, Any, List, Optional
from .base import BaseExperiment
from services.agents import RequirementsAgent, ArchitectureAgent, IaCAgent, DeploymentAgent
from services.gcp.deployment import GCPDeploymentService
import logging
import os

logger = logging.getLogger(__name__)


class E2DeployabilityExperiment(BaseExperiment):
    """E2: Deployability feedback loop with iterative fixes"""
    
    def __init__(self):
        super().__init__(
            experiment_type="e2",
            name="Deployability Feedback Loop",
            description="Measure passItr@n - probability template deploys within n iterations"
        )
        # Initialize agents only if API key is available
        import os
        if os.getenv("GEMINI_API_KEY"):
            self.requirements_agent = RequirementsAgent()
            self.architecture_agent = ArchitectureAgent()
        else:
            self.requirements_agent = None
            self.architecture_agent = None
            logger.warning("GEMINI_API_KEY not set - E2 will use simplified agents")
        self.iac_agent = IaCAgent()
        self.deployment_agent = DeploymentAgent()
        self.deployment_service = GCPDeploymentService()
        self.project_id = os.getenv("GCP_PROJECT_ID")
    
    async def run(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Run E2 experiment"""
        config = config or {}
        prompts = config.get("prompts", self._get_default_prompts())
        max_iterations = config.get("max_iterations", 5)
        
        await self.start_run(config)
        
        try:
            results = []
            
            for prompt_data in prompts:
                prompt = prompt_data["prompt"]
                difficulty = prompt_data.get("difficulty", "medium")
                
                prompt_result = await self._test_prompt(
                    prompt=prompt,
                    difficulty=difficulty,
                    max_iterations=max_iterations
                )
                results.append(prompt_result)
            
            # Calculate passItr@n
            pass_itr_1 = sum(1 for r in results if r.get("iterations_to_success", 0) <= 1)
            pass_itr_5 = sum(1 for r in results if r.get("iterations_to_success", 0) <= 5)
            pass_itr_10 = sum(1 for r in results if r.get("iterations_to_success", 0) <= 10)
            total = len(results)
            
            await self.record_metric("passItr@1", pass_itr_1 / total if total > 0 else 0)
            await self.record_metric("passItr@5", pass_itr_5 / total if total > 0 else 0)
            await self.record_metric("passItr@10", pass_itr_10 / total if total > 0 else 0)
            await self.record_metric("total_prompts", total)
            await self.record_metric("successful_deployments", sum(1 for r in results if r.get("success", False)))
            
            experiment_results = {
                "results": results,
                "passItr@1": pass_itr_1 / total if total > 0 else 0,
                "passItr@5": pass_itr_5 / total if total > 0 else 0,
                "passItr@10": pass_itr_10 / total if total > 0 else 0
            }
            
            await self.complete_run(experiment_results)
            return experiment_results
            
        except Exception as e:
            logger.error(f"E2 experiment failed: {str(e)}")
            await self.fail_run(str(e))
            raise
    
    async def _test_prompt(
        self,
        prompt: str,
        difficulty: str,
        max_iterations: int
    ) -> Dict[str, Any]:
        """Test a single prompt with iterative fixes"""
        
        iterations = []
        success = False
        iterations_to_success = 0
        
        for iteration in range(1, max_iterations + 1):
            iteration_start = time.time()
            
            try:
                # Step 1: Extract requirements
                if self.requirements_agent:
                    requirements = await self.requirements_agent.extract_requirements(prompt)
                else:
                    # Simplified requirements extraction without LLM
                    requirements = {
                        "services": ["S3"] if "S3" in prompt or "bucket" in prompt.lower() else ["VPC"],
                        "slas": {},
                        "constraints": {}
                    }
                
                # Step 2: Design architecture
                if self.architecture_agent:
                    architecture = await self.architecture_agent.propose_architecture(requirements)
                else:
                    # Simplified architecture without LLM - use GCP storage bucket
                    architecture = {
                        "architecture": [
                            {"type": "google_storage_bucket", "id": "test-bucket", "config": {"bucket_name": f"vivify-test-{uuid.uuid4().hex[:8]}"}}
                        ] if "bucket" in prompt.lower() or "storage" in prompt.lower() else [
                            {"type": "google_compute_network", "id": "test-vpc", "config": {"name": f"test-vpc-{uuid.uuid4().hex[:8]}"}}
                        ]
                    }
                
                # Step 3: Generate IaC with project_id
                if not self.project_id:
                    raise ValueError("GCP_PROJECT_ID not set")
                
                iac_data = await self.iac_agent.generate_iac(architecture, project_id=self.project_id)
                
                # Step 4: Attempt deployment to GCP
                stack_name = f"e2-{uuid.uuid4().hex[:8]}"
                terraform_config = iac_data.get("terraform_config", "")
                
                deployment_result = await self.deployment_service.deploy_stack(
                    stack_name=stack_name,
                    terraform_config=terraform_config,
                    project_id=self.project_id,
                    variables={"gcp_region": os.getenv("GCP_REGION", "us-central1")}
                )
                
                iteration_time = time.time() - iteration_start
                
                iterations.append({
                    "iteration": iteration,
                    "success": deployment_result.get("success", False),
                    "error": deployment_result.get("error"),
                    "time": iteration_time
                })
                
                if deployment_result.get("success", False):
                    success = True
                    iterations_to_success = iteration
                    break
                else:
                    # Extract error and try to fix (simplified)
                    error = deployment_result.get("error", "")
                    # In real implementation, would use LLM to fix errors
                    prompt = f"{prompt} Fix error: {error[:100]}"
                
            except Exception as e:
                iteration_time = time.time() - iteration_start
                iterations.append({
                    "iteration": iteration,
                    "success": False,
                    "error": str(e),
                    "time": iteration_time
                })
            
            await self.record_metric(f"iteration_{iteration}_time", iteration_time, "seconds")
        
        # Cleanup
        if success:
            try:
                await self.deployment_service.rollback_stack(stack_name)
            except:
                pass
        
        return {
            "prompt": prompt[:100],  # Truncate
            "difficulty": difficulty,
            "success": success,
            "iterations_to_success": iterations_to_success if success else max_iterations,
            "iterations": iterations,
            "failure_class": self._classify_failure(iterations[-1].get("error", "")) if not success else None
        }
    
    def _classify_failure(self, error: str) -> str:
        """Classify failure type"""
        error_lower = error.lower()
        if "missing" in error_lower or "required" in error_lower:
            return "missing_params"
        elif "invalid" in error_lower or "property" in error_lower:
            return "invalid_properties"
        elif "permission" in error_lower or "access" in error_lower:
            return "permissions"
        else:
            return "other"
    
    def _get_default_prompts(self) -> List[Dict[str, Any]]:
        """Get default test prompts for GCP"""
        return [
            {
                "prompt": "Create a storage bucket for storing application data",
                "difficulty": "level-1"
            },
            {
                "prompt": "Create a storage bucket with invalid_property='true'",
                "difficulty": "level-1"
            },
            {
                "prompt": "Create a VPC network with subnets",
                "difficulty": "level-2"
            },
            {
                "prompt": "Create a Cloud Function with storage trigger",
                "difficulty": "level-3"
            }
        ]

