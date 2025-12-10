"""Deployment service for GCP infrastructure"""

import os
import asyncio
from typing import Dict, Any, Optional
import logging
from .terraform import GCPTerraformService

logger = logging.getLogger(__name__)


class GCPDeploymentService:
    """Service for deploying GCP infrastructure"""
    
    def __init__(self):
        self.terraform = GCPTerraformService()
        self.active_deployments: Dict[str, Dict[str, Any]] = {}
    
    async def deploy_stack(
        self,
        stack_name: str,
        terraform_config: str,
        project_id: str,
        variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Deploy a Terraform stack to GCP"""
        
        try:
            # Create workspace
            workspace_path = self.terraform.create_workspace(stack_name)
            
            # Write Terraform config
            with open(os.path.join(workspace_path, "main.tf"), "w") as f:
                f.write(terraform_config)
            
            # Write variables if provided
            if variables:
                with open(os.path.join(workspace_path, "terraform.tfvars"), "w") as f:
                    for key, value in variables.items():
                        if isinstance(value, str):
                            f.write(f'{key} = "{value}"\n')
                        else:
                            f.write(f'{key} = {value}\n')
            
            # Initialize
            if not self.terraform.init_terraform(workspace_path):
                return {
                    "success": False,
                    "error": "Terraform initialization failed"
                }
            
            # Plan
            plan_result = self.terraform.plan_terraform(workspace_path)
            if not plan_result["success"]:
                return {
                    "success": False,
                    "error": f"Terraform plan failed: {plan_result.get('error')}"
                }
            
            # Apply
            apply_result = self.terraform.apply_terraform(workspace_path)
            
            self.active_deployments[stack_name] = {
                "workspace_path": workspace_path,
                "status": "deployed" if apply_result["success"] else "failed",
                "project_id": project_id
            }
            
            return {
                "success": apply_result["success"],
                "stack_name": stack_name,
                "output": apply_result.get("output"),
                "error": apply_result.get("error")
            }
            
        except Exception as e:
            logger.error(f"Deployment failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def detect_drift(self, stack_name: str) -> Dict[str, Any]:
        """Detect drift in deployed stack with consistency wait"""
        try:
            if stack_name not in self.active_deployments:
                return {"has_drift": False, "error": "Stack not found"}
            
            workspace_path = self.active_deployments[stack_name]["workspace_path"]
            
            # Consistency wait: GCP APIs have latency, resource might take 5-10 seconds to appear
            # Wait before checking drift to ensure API consistency
            await asyncio.sleep(5)
            
            # Run terraform plan to detect drift
            drift_result = self.terraform.detect_drift(workspace_path)
            
            return drift_result
            
        except Exception as e:
            logger.error(f"Drift detection failed: {str(e)}")
            return {"has_drift": False, "error": str(e)}
    
    async def rollback_stack(self, stack_name: str) -> Dict[str, Any]:
        """Rollback (destroy) a stack"""
        try:
            if stack_name not in self.active_deployments:
                return {"success": False, "error": "Stack not found"}
            
            workspace_path = self.active_deployments[stack_name]["workspace_path"]
            destroy_result = self.terraform.destroy_terraform(workspace_path)
            
            if destroy_result["success"]:
                del self.active_deployments[stack_name]
                self.terraform.cleanup_workspace(workspace_path)
            
            return destroy_result
            
        except Exception as e:
            logger.error(f"Rollback failed: {str(e)}")
            return {"success": False, "error": str(e)}

