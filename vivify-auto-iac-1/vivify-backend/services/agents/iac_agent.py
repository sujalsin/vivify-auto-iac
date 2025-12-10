"""IaC Generation Agent - emits Terraform/CloudFormation with module graph"""

import os
from typing import Dict, Any, List
from services.aws.terraform import TerraformService
import logging

logger = logging.getLogger(__name__)


class IaCAgent:
    """Generates Terraform/CloudFormation templates"""
    
    def __init__(self):
        self.terraform = TerraformService()
    
    async def generate_iac(self, architecture: Dict[str, Any]) -> Dict[str, Any]:
        """Generate IaC templates from architecture"""
        
        try:
            resources = architecture.get("architecture", [])
            variables = architecture.get("variables", {})
            
            # Generate Terraform config
            terraform_config = self.terraform.generate_terraform_config(
                resources=resources,
                variables=variables
            )
            
            # Extract module graph
            module_graph = self._extract_module_graph(resources)
            
            return {
                "terraform_config": terraform_config,
                "cloudformation_template": None,  # Can be added later
                "module_graph": module_graph,
                "variables": variables,
                "resources": resources
            }
            
        except Exception as e:
            logger.error(f"IaC generation failed: {str(e)}")
            return {
                "error": str(e),
                "terraform_config": "",
                "module_graph": {}
            }
    
    def _extract_module_graph(self, resources: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract module dependency graph"""
        graph = {
            "nodes": [],
            "edges": []
        }
        
        for resource in resources:
            graph["nodes"].append({
                "id": resource.get("id", ""),
                "type": resource.get("type", ""),
                "name": resource.get("name", "")
            })
            
            # Extract dependencies from metadata
            deps = resource.get("metadata", {}).get("depends_on", [])
            for dep in deps:
                graph["edges"].append({
                    "from": resource.get("id", ""),
                    "to": dep
                })
        
        return graph
    
    def __call__(self, input_data: Any) -> Dict[str, Any]:
        """Make agent callable"""
        if isinstance(input_data, dict):
            import asyncio
            return asyncio.run(self.generate_iac(input_data))
        return {"error": "Invalid input"}

