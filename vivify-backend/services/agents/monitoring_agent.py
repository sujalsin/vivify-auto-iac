"""Monitoring/Cost Agent - wires alarms/dashboards and estimates cost"""

import os
import asyncio
from typing import Dict, Any, Optional
import logging
from google.cloud import monitoring_v3
from google.oauth2 import service_account

logger = logging.getLogger(__name__)


class MonitoringAgent:
    """Sets up monitoring and cost estimation using Cloud Monitoring"""
    
    def __init__(self):
        self.project_id = os.getenv("GCP_PROJECT_ID")
        self.credentials = None
        
        # Load credentials if available
        creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if creds_path and os.path.exists(creds_path):
            try:
                self.credentials = service_account.Credentials.from_service_account_file(creds_path)
            except Exception as e:
                logger.warning(f"Failed to load credentials: {e}")
    
    async def setup_monitoring(self, deployment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Setup Cloud Monitoring alert policies and dashboards"""
        
        if not self.project_id:
            logger.warning("GCP_PROJECT_ID not set, returning mock data")
            return {
                "alarms": [],
                "dashboards": [],
                "error": "GCP_PROJECT_ID not configured"
            }
        
        try:
            # Create alert policy client
            alert_client = monitoring_v3.AlertPolicyServiceClient(credentials=self.credentials)
            project_name = f"projects/{self.project_id}"
            
            # Create a simple alert policy for high CPU
            alert_policy = monitoring_v3.AlertPolicy()
            alert_policy.display_name = "high-cpu-alarm"
            alert_policy.combiner = monitoring_v3.AlertPolicy.ConditionCombinerType.OR
            
            # Create condition for CPU utilization
            condition = monitoring_v3.AlertPolicy.Condition()
            condition.display_name = "CPU utilization is above 80%"
            
            # Create metric threshold condition
            condition.condition_threshold = monitoring_v3.AlertPolicy.Condition.MetricThreshold()
            condition.condition_threshold.filter = 'resource.type="gce_instance" AND metric.type="compute.googleapis.com/instance/cpu/utilization"'
            condition.condition_threshold.comparison = monitoring_v3.ComparisonType.COMPARISON_GT
            condition.condition_threshold.threshold_value = 0.8
            condition.condition_threshold.duration = {"seconds": 300}  # 5 minutes
            
            alert_policy.conditions = [condition]
            
            # Create the alert policy
            try:
                created_policy = alert_client.create_alert_policy(
                    name=project_name,
                    alert_policy=alert_policy
                )
                policy_id = created_policy.name.split("/")[-1]
            except Exception as e:
                logger.warning(f"Failed to create alert policy: {e}")
                policy_id = None
            
            # For dashboards, we'll return a placeholder (dashboard creation is more complex)
            return {
                "alarms": [
                    {
                        "name": "high-cpu-alarm",
                        "id": policy_id,
                        "metric": "compute.googleapis.com/instance/cpu/utilization",
                        "threshold": 80
                    }
                ] if policy_id else [],
                "dashboards": [
                    {
                        "name": "infrastructure-dashboard",
                        "note": "Dashboard creation requires manual setup via Cloud Console or API"
                    }
                ]
            }
            
        except Exception as e:
            logger.error(f"Monitoring setup failed: {str(e)}")
            return {
                "alarms": [],
                "dashboards": [],
                "error": str(e)
            }
    
    async def estimate_cost(self, resources: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate infrastructure costs"""
        
        # Simplified cost estimation
        cost_per_resource = {
            "s3": 0.023,  # per GB/month
            "lambda": 0.20,  # per 1M requests
            "ec2": 10.0,  # per instance/month (t2.micro)
            "vpc": 0.0  # free
        }
        
        total_cost = 0.0
        breakdown = {}
        
        resource_list = resources.get("resources", [])
        for resource in resource_list:
            resource_type = resource.get("type", "").lower()
            cost = cost_per_resource.get(resource_type, 0.0)
            total_cost += cost
            breakdown[resource.get("id", "")] = cost
        
        return {
            "total_monthly_cost": total_cost,
            "breakdown": breakdown,
            "currency": "USD"
        }
    
    def __call__(self, input_data: Any) -> Dict[str, Any]:
        """Make agent callable"""
        if isinstance(input_data, dict):
            if "action" in input_data:
                if input_data["action"] == "estimate_cost":
                    return asyncio.run(self.estimate_cost(input_data))
            
            # Default: setup monitoring
            return asyncio.run(self.setup_monitoring(input_data))
        
        return {"error": "Invalid input"}

