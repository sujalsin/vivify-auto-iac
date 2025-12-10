"""Terraform service for GCP IaC generation and management"""

import os
import json
import subprocess
import tempfile
import shutil
from typing import Dict, Any, Optional, List
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class GCPTerraformService:
    """Service for GCP Terraform operations"""
    
    def __init__(self, work_dir: Optional[str] = None):
        self.work_dir = work_dir or os.path.join(tempfile.gettempdir(), "terraform_workspaces_gcp")
        os.makedirs(self.work_dir, exist_ok=True)
    
    def generate_terraform_config(
        self,
        resources: List[Dict[str, Any]],
        project_id: str,
        variables: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate Terraform configuration for GCP resources"""
        
        config = f"""terraform {{
  required_providers {{
    google = {{
      source  = "hashicorp/google"
      version = "~> 5.0"
    }}
  }}
}}

provider "google" {{
  project = "{project_id}"
  region  = var.gcp_region
}}
"""
        
        # Add variables
        if variables:
            config += "\nvariable \"gcp_region\" {\n"
            config += f'  default = "{variables.get("gcp_region", "us-central1")}"\n'
            config += "}\n\n"
            
            for var_name, var_value in variables.items():
                if var_name != "gcp_region":
                    config += f'variable "{var_name}" {{\n'
                    if isinstance(var_value, str):
                        config += f'  default = "{var_value}"\n'
                    else:
                        config += f'  default = {json.dumps(var_value)}\n'
                    config += "}\n\n"
        else:
            config += "\nvariable \"gcp_region\" {\n"
            config += '  default = "us-central1"\n'
            config += "}\n\n"
        
        # Generate resources - prioritize google_storage_bucket and google_pubsub_topic
        for resource in resources:
            resource_type = resource.get("type", "")
            resource_id = resource.get("id", "resource")
            config_data = resource.get("config", {})
            
            if resource_type == "google_storage_bucket" or resource_type == "s3":
                # Map s3 to google_storage_bucket for compatibility
                bucket_name = config_data.get("bucket_name", resource_id)
                # Ensure unique bucket name (GCP requires globally unique names)
                if not bucket_name.startswith("vivify-"):
                    bucket_name = f"vivify-{bucket_name}"
                
                config += f'resource "google_storage_bucket" "{resource_id}" {{\n'
                config += f'  name     = "{bucket_name}"\n'
                config += f'  location = "{config_data.get("location", "US")}"\n'
                if config_data.get("storage_class"):
                    config += f'  storage_class = "{config_data["storage_class"]}"\n'
                # Add uniform bucket-level access for security
                config += '  uniform_bucket_level_access = true\n'
                config += "}\n\n"
            
            elif resource_type == "google_pubsub_topic" or resource_type == "pubsub_topic":
                config += f'resource "google_pubsub_topic" "{resource_id}" {{\n'
                config += f'  name = "{config_data.get("name", resource_id)}"\n'
                config += "}\n\n"
            
            elif resource_type == "google_compute_instance":
                config += f'resource "google_compute_instance" "{resource_id}" {{\n'
                config += f'  name         = "{config_data.get("name", resource_id)}"\n'
                config += f'  machine_type = "{config_data.get("machine_type", "e2-micro")}"\n'
                config += f'  zone         = "{config_data.get("zone", "us-central1-a")}"\n'
                config += '  boot_disk {\n'
                config += '    initialize_params {\n'
                config += '      image = "debian-cloud/debian-11"\n'
                config += '    }\n'
                config += '  }\n'
                config += '  network_interface {\n'
                config += '    network = "default"\n'
                config += '    access_config {\n'
                config += '    }\n'
                config += '  }\n'
                config += "}\n\n"
            
            elif resource_type == "google_compute_network" or resource_type == "vpc":
                config += f'resource "google_compute_network" "{resource_id}" {{\n'
                config += f'  name                    = "{config_data.get("name", resource_id)}"\n'
                config += f'  auto_create_subnetworks = {str(config_data.get("auto_create_subnetworks", False)).lower()}\n'
                config += "}\n\n"
            
            elif resource_type == "google_cloudfunctions_function" or resource_type == "lambda":
                config += f'resource "google_cloudfunctions_function" "{resource_id}" {{\n'
                config += f'  name        = "{config_data.get("name", resource_id)}"\n'
                config += f'  runtime     = "{config_data.get("runtime", "python39")}"\n'
                config += f'  entry_point = "{config_data.get("entry_point", "hello_world")}"\n'
                config += '  source_archive_bucket = google_storage_bucket.function_source.name\n'
                config += '  source_archive_object = "function.zip"\n'
                config += '  trigger {\n'
                config += '    http_trigger {}\n'
                config += '  }\n'
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
            if result.returncode != 0:
                logger.error(f"Terraform init failed: {result.stderr}")
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Terraform init failed: {str(e)}")
            return False
    
    def plan_terraform(self, workspace_path: str) -> Dict[str, Any]:
        """Run terraform plan"""
        try:
            result = subprocess.run(
                ["terraform", "plan", "-out=tfplan"],
                cwd=workspace_path,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None
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
                ["terraform", "apply", "-auto-approve", "tfplan"],
                cwd=workspace_path,
                capture_output=True,
                text=True,
                timeout=600
            )
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None
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
                ["terraform", "destroy", "-auto-approve"],
                cwd=workspace_path,
                capture_output=True,
                text=True,
                timeout=600
            )
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None
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
            has_drift = "No changes" not in output and "No changes" not in output.lower()
        
        return {
            "has_drift": has_drift,
            "plan_result": plan_result
        }
    
    def cleanup_workspace(self, workspace_path: str):
        """Clean up workspace directory"""
        if os.path.exists(workspace_path):
            shutil.rmtree(workspace_path)

