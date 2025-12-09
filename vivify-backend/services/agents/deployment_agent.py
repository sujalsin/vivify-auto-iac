"""Deployment Agent - plans, applies, rolls back; handles drift"""

import asyncio
from typing import Dict, Any
from services.aws.deployment import DeploymentService
import logging

logger = logging.getLogger(__name__)


class DeploymentAgent:
    """Deploys infrastructure and handles drift"""
    
    def __init__(self):
        self.deployment = DeploymentService()
    
    async def deploy(self, iac_data: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy infrastructure from IaC"""
        
        try:
            terraform_config = iac_data.get("terraform_config", "")
            variables = iac_data.get("variables", {})
            stack_name = iac_data.get("stack_name", "default-stack")
            
            result = await self.deployment.deploy_stack(
                stack_name=stack_name,
                terraform_config=terraform_config,
                variables=variables
            )
            
            return {
                "success": result.get("success", False),
                "stack_name": stack_name,
                "output": result.get("output"),
                "error": result.get("error")
            }
            
        except Exception as e:
            logger.error(f"Deployment failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def detect_drift(self, stack_name: str) -> Dict[str, Any]:
        """Detect infrastructure drift"""
        return await self.deployment.detect_drift(stack_name)
    
    async def rollback(self, stack_name: str) -> Dict[str, Any]:
        """Rollback a deployment"""
        return await self.deployment.rollback_stack(stack_name)
    
    def __call__(self, input_data: Any) -> Dict[str, Any]:
        """Make agent callable"""
        if isinstance(input_data, dict):
            if "stack_name" in input_data and "action" in input_data:
                action = input_data["action"]
                stack_name = input_data["stack_name"]
                
                if action == "deploy":
                    return asyncio.run(self.deploy(input_data))
                elif action == "rollback":
                    return asyncio.run(self.rollback(stack_name))
                elif action == "drift":
                    return asyncio.run(self.detect_drift(stack_name))
            
            # Default: deploy
            return asyncio.run(self.deploy(input_data))
        
        return {"error": "Invalid input"}

