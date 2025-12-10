"""E3 - IaC Apply Concurrency, Drift, and Rollback"""

import asyncio
import time
import uuid
import random
from typing import Dict, Any, List, Optional
from .base import BaseExperiment
from services.gcp.deployment import GCPDeploymentService
import logging
import os

logger = logging.getLogger(__name__)


class E3ConcurrencyExperiment(BaseExperiment):
    """E3: IaC concurrency, drift detection, and rollback"""
    
    def __init__(self):
        super().__init__(
            experiment_type="e3",
            name="IaC Concurrency, Drift, and Rollback",
            description="Measure convergence time, state lock contention, rollback success rate"
        )
        self.deployment_service = GCPDeploymentService()
        self.project_id = os.getenv("GCP_PROJECT_ID")
        if not self.project_id:
            logger.warning("GCP_PROJECT_ID not set")
    
    async def run(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Run E3 experiment"""
        config = config or {}
        num_stacks = config.get("num_stacks", 10)
        regions = config.get("regions", ["us-central1", "us-east1", "us-west1"])
        inject_drift = config.get("inject_drift", True)
        
        if not self.project_id:
            raise ValueError("GCP_PROJECT_ID not set")
        
        await self.start_run(config)
        
        try:
            # Create stacks
            stacks = []
            for i in range(num_stacks):
                stack_name = f"e3-stack-{uuid.uuid4()}"
                region = random.choice(regions)
                
                # Generate simple Terraform config
                terraform_config = self._generate_stack_config(stack_name, region)
                
                stacks.append({
                    "name": stack_name,
                    "region": region,
                    "config": terraform_config
                })
            
            # Deploy stacks concurrently
            start_time = time.time()
            deployment_tasks = [
                self._deploy_stack(stack) for stack in stacks
            ]
            deployment_results = await asyncio.gather(*deployment_tasks, return_exceptions=True)
            deployment_time = time.time() - start_time
            
            await self.record_metric("deployment_time", deployment_time, "seconds")
            await self.record_metric("num_stacks", num_stacks)
            
            successful_deployments = sum(1 for r in deployment_results if isinstance(r, dict) and r.get("success", False))
            await self.record_metric("successful_deployments", successful_deployments)
            await self.record_metric("failed_deployments", num_stacks - successful_deployments)
            
            # Inject drift
            if inject_drift:
                drift_results = await self._inject_drift(stacks[:min(5, len(stacks))])
                await self.record_metric("drift_detected", sum(1 for r in drift_results if r.get("has_drift", False)))
            
            # Test rollback
            rollback_results = await self._test_rollbacks(stacks[:min(3, len(stacks))])
            successful_rollbacks = sum(1 for r in rollback_results if r.get("success", False))
            await self.record_metric("rollback_success_rate", successful_rollbacks / len(rollback_results) if rollback_results else 0)
            
            # Convergence time
            convergence_time = time.time() - start_time
            await self.record_metric("convergence_time", convergence_time, "seconds")
            
            results = {
                "num_stacks": num_stacks,
                "deployment_time": deployment_time,
                "convergence_time": convergence_time,
                "successful_deployments": successful_deployments,
                "rollback_success_rate": successful_rollbacks / len(rollback_results) if rollback_results else 0,
                "deployment_results": [r for r in deployment_results if isinstance(r, dict)],
                "rollback_results": rollback_results
            }
            
            await self.complete_run(results)
            return results
            
        except Exception as e:
            logger.error(f"E3 experiment failed: {str(e)}")
            await self.fail_run(str(e))
            raise
    
    def _generate_stack_config(self, stack_name: str, region: str) -> str:
        """Generate Terraform config for Pub/Sub topic (hardcoded for fast provisioning)"""
        topic_name = f"{stack_name}-topic"
        # Pub/Sub topics provision in <2 seconds, perfect for concurrency testing
        return f"""terraform {{
  required_providers {{
    google = {{
      source  = "hashicorp/google"
      version = "~> 5.0"
    }}
  }}
}}

provider "google" {{
  project = "{self.project_id}"
  region  = "{region}"
}}

resource "google_pubsub_topic" "test" {{
  name = "{topic_name}"
}}
"""
    
    async def _deploy_stack(self, stack: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy a single stack - no failure injection, only real failures"""
        try:
            result = await self.deployment_service.deploy_stack(
                stack_name=stack["name"],
                terraform_config=stack["config"],
                project_id=self.project_id,
                variables={"gcp_region": stack["region"]}
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Stack deployment failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "stack_name": stack["name"]
            }
    
    async def _inject_drift(self, stacks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect drift in stacks (with consistency wait built into service)"""
        results = []
        for stack in stacks:
            try:
                drift_result = await self.deployment_service.detect_drift(stack["name"])
                results.append({
                    "stack_name": stack["name"],
                    "has_drift": drift_result.get("has_drift", False),
                    "plan_output": drift_result.get("plan_result", {}).get("output", "")
                })
            except Exception as e:
                results.append({
                    "stack_name": stack["name"],
                    "has_drift": False,
                    "error": str(e)
                })
        return results
    
    async def _test_rollbacks(self, stacks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Test rollback functionality"""
        results = []
        for stack in stacks:
            try:
                rollback_result = await self.deployment_service.rollback_stack(stack["name"])
                results.append({
                    "stack_name": stack["name"],
                    "success": rollback_result.get("success", False),
                    "error": rollback_result.get("error")
                })
            except Exception as e:
                results.append({
                    "stack_name": stack["name"],
                    "success": False,
                    "error": str(e)
                })
        return results

