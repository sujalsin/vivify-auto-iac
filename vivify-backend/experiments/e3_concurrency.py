"""E3 - IaC Apply Concurrency, Drift, and Rollback"""

import asyncio
import time
import uuid
import random
from typing import Dict, Any, List, Optional
from .base import BaseExperiment
from services.aws.deployment import DeploymentService
from services.aws.terraform import TerraformService
import logging

logger = logging.getLogger(__name__)


class E3ConcurrencyExperiment(BaseExperiment):
    """E3: IaC concurrency, drift detection, and rollback"""
    
    def __init__(self):
        super().__init__(
            experiment_type="e3",
            name="IaC Concurrency, Drift, and Rollback",
            description="Measure convergence time, state lock contention, rollback success rate"
        )
        self.deployment_service = DeploymentService()
        self.terraform_service = TerraformService()
    
    async def run(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Run E3 experiment"""
        config = config or {}
        num_stacks = config.get("num_stacks", 10)
        regions = config.get("regions", ["us-east-1", "us-west-1", "us-west-2"])
        inject_drift = config.get("inject_drift", True)
        inject_failures = config.get("inject_failures", True)
        
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
                self._deploy_stack(stack, inject_failures) for stack in stacks
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
        """Generate a simple Terraform stack config"""
        return f"""terraform {{
  required_providers {{
    aws = {{
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }}
  }}
}}

provider "aws" {{
  region = "{region}"
  endpoints {{
    s3 = "http://localhost:4566"
    ec2 = "http://localhost:4566"
  }}
  skip_credentials_validation = true
  skip_metadata_api_check = true
  skip_region_validation = true
}}

resource "aws_s3_bucket" "test" {{
  bucket = "{stack_name}-bucket"
}}
"""
    
    async def _deploy_stack(self, stack: Dict[str, Any], inject_failure: bool) -> Dict[str, Any]:
        """Deploy a single stack"""
        try:
            # Randomly inject failure
            if inject_failure and random.random() < 0.1:  # 10% failure rate
                return {
                    "success": False,
                    "error": "Simulated failure",
                    "stack_name": stack["name"]
                }
            
            result = await self.deployment_service.deploy_stack(
                stack_name=stack["name"],
                terraform_config=stack["config"],
                variables={"aws_region": stack["region"]}
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
        """Inject drift into stacks"""
        results = []
        for stack in stacks:
            try:
                drift_result = await self.deployment_service.detect_drift(stack["name"])
                results.append({
                    "stack_name": stack["name"],
                    "has_drift": drift_result.get("has_drift", False)
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

