"""Monitoring/Cost Agent - wires alarms/dashboards and estimates cost"""

import asyncio
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class MonitoringAgent:
    """Sets up monitoring and cost estimation"""
    
    def __init__(self):
        pass
    
    async def setup_monitoring(self, deployment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Setup CloudWatch alarms and dashboards"""
        
        # Simplified monitoring setup
        return {
            "alarms": [
                {
                    "name": "high-cpu-alarm",
                    "metric": "CPUUtilization",
                    "threshold": 80
                }
            ],
            "dashboards": [
                {
                    "name": "infrastructure-dashboard",
                    "widgets": ["CPU", "Memory", "Network"]
                }
            ]
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

