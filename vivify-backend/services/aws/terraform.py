"""Terraform service for IaC generation and management"""

import os
import json
import subprocess
import tempfile
import shutil
from typing import Dict, Any, Optional, List
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class TerraformService:
    """Service for Terraform operations"""
    
    def __init__(self, work_dir: Optional[str] = None):
        self.work_dir = work_dir or os.path.join(tempfile.gettempdir(), "terraform_workspaces")
        os.makedirs(self.work_dir, exist_ok=True)
    
    def generate_terraform_config(
        self,
        resources: List[Dict[str, Any]],
        variables: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate Terraform configuration from resource definitions"""
        
        config = """terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
"""
        
        # Add endpoint for LocalStack if needed
        if os.getenv("AWS_PROVIDER", "localstack") == "localstack":
            config += '  endpoints {\n'
            config += '    s3 = "http://localhost:4566"\n'
            config += '    ec2 = "http://localhost:4566"\n'
            config += '    lambda = "http://localhost:4566"\n'
            config += '    iam = "http://localhost:4566"\n'
            config += '  }\n'
            config += '  skip_credentials_validation = true\n'
            config += '  skip_metadata_api_check = true\n'
            config += '  skip_region_validation = true\n'
        
        config += "}\n\n"
        
        # Add variables
        if variables:
            config += "variable \"aws_region\" {\n"
            config += '  default = "us-east-1"\n'
            config += "}\n\n"
            
            for var_name, var_value in variables.items():
                if var_name != "aws_region":
                    config += f'variable "{var_name}" {{\n'
                    if isinstance(var_value, str):
                        config += f'  default = "{var_value}"\n'
                    else:
                        config += f'  default = {json.dumps(var_value)}\n'
                    config += "}\n\n"
        
        # Generate resources
        for resource in resources:
            resource_type = resource.get("type")
            resource_id = resource.get("id", "resource")
            config_data = resource.get("config", {})
            
            if resource_type == "s3":
                config += f'resource "aws_s3_bucket" "{resource_id}" {{\n'
                config += f'  bucket = "{config_data.get("bucket_name", resource_id)}"\n'
                config += "}\n\n"
            
            elif resource_type == "lambda":
                config += f'resource "aws_lambda_function" "{resource_id}" {{\n'
                config += f'  function_name = "{config_data.get("function_name", resource_id)}"\n'
                config += f'  runtime = "{config_data.get("runtime", "python3.9")}"\n'
                config += f'  handler = "{config_data.get("handler", "index.handler")}"\n'
                config += '  filename = "lambda.zip"\n'
                config += '  source_code_hash = filebase64sha256("lambda.zip")\n'
                config += "}\n\n"
            
            elif resource_type == "vpc":
                config += f'resource "aws_vpc" "{resource_id}" {{\n'
                config += f'  cidr_block = "{config_data.get("cidr_block", "10.0.0.0/16")}"\n'
                config += f'  tags = {{\n'
                config += f'    Name = "{config_data.get("name", resource_id)}"\n'
                config += '  }\n'
                config += "}\n\n"
            
            elif resource_type == "security_group":
                config += f'resource "aws_security_group" "{resource_id}" {{\n'
                config += f'  name = "{config_data.get("name", resource_id)}"\n'
                config += f'  vpc_id = {config_data.get("vpc_id", "aws_vpc.main.id")}\n'
                config += "}\n\n"
        
        return config
    
    def create_workspace(self, stack_name: str) -> str:
        """Create a Terraform workspace directory"""
        workspace_path = os.path.join(self.work_dir, stack_name)
        os.makedirs(workspace_path, exist_ok=True)
        return workspace_path
    
    def init_terraform(self, workspace_path: str) -> bool:
        """Initialize Terraform in workspace"""
        try:
            result = subprocess.run(
                ["terraform", "init"],
                cwd=workspace_path,
                capture_output=True,
                text=True,
                timeout=60
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Terraform init failed: {str(e)}")
            return False
    
    def plan_terraform(self, workspace_path: str) -> Dict[str, Any]:
        """Run terraform plan"""
        try:
            result = subprocess.run(
                ["terraform", "plan", "-out=tfplan", "-json"],
                cwd=workspace_path,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr
            }
        except Exception as e:
            logger.error(f"Terraform plan failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def apply_terraform(self, workspace_path: str) -> Dict[str, Any]:
        """Run terraform apply"""
        try:
            result = subprocess.run(
                ["terraform", "apply", "-auto-approve", "-json"],
                cwd=workspace_path,
                capture_output=True,
                text=True,
                timeout=600
            )
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr
            }
        except Exception as e:
            logger.error(f"Terraform apply failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def destroy_terraform(self, workspace_path: str) -> Dict[str, Any]:
        """Run terraform destroy"""
        try:
            result = subprocess.run(
                ["terraform", "destroy", "-auto-approve", "-json"],
                cwd=workspace_path,
                capture_output=True,
                text=True,
                timeout=600
            )
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr
            }
        except Exception as e:
            logger.error(f"Terraform destroy failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def detect_drift(self, workspace_path: str) -> Dict[str, Any]:
        """Detect Terraform drift"""
        plan_result = self.plan_terraform(workspace_path)
        
        # Parse plan output to detect changes
        has_drift = False
        if plan_result["success"]:
            # Simple check - if plan shows changes, there's drift
            output = plan_result.get("output", "")
            has_drift = "No changes" not in output
        
        return {
            "has_drift": has_drift,
            "plan_result": plan_result
        }
    
    def cleanup_workspace(self, workspace_path: str):
        """Clean up workspace directory"""
        if os.path.exists(workspace_path):
            shutil.rmtree(workspace_path)

