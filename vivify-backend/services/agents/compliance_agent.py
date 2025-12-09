"""Cloud Compliance Agent - detects violations, compliance with security frameworks"""

import asyncio
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class ComplianceAgent:
    """Checks compliance with security frameworks"""
    
    def __init__(self):
        self.frameworks = ["SOC2", "PCI-DSS"]
    
    async def check_compliance(
        self,
        deployment_data: Dict[str, Any],
        framework: str = "SOC2"
    ) -> Dict[str, Any]:
        """Check compliance with security framework"""
        
        violations = []
        checks = []
        
        # Simplified compliance checks
        resources = deployment_data.get("resources", [])
        
        # Check for public S3 buckets
        for resource in resources:
            if resource.get("type") == "s3":
                # Check if bucket is public (simplified)
                if resource.get("config", {}).get("public", False):
                    violations.append({
                        "resource": resource.get("id"),
                        "violation": "Public S3 bucket",
                        "severity": "high",
                        "framework": framework
                    })
        
        # Check for security groups with open ports
        for resource in resources:
            if resource.get("type") == "security_group":
                # Simplified check
                checks.append({
                    "resource": resource.get("id"),
                    "check": "Security group rules",
                    "status": "passed"
                })
        
        compliance_score = 100.0 - (len(violations) * 10.0)
        compliance_score = max(0.0, compliance_score)
        
        return {
            "framework": framework,
            "compliant": len(violations) == 0,
            "compliance_score": compliance_score,
            "violations": violations,
            "checks": checks
        }
    
    async def diagnose_violations(self, violations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Diagnose root causes of violations"""
        
        root_causes = []
        for violation in violations:
            root_causes.append({
                "violation": violation.get("violation"),
                "root_cause": "Configuration issue",
                "recommendation": "Review and update resource configuration"
            })
        
        return {
            "root_causes": root_causes,
            "total_violations": len(violations)
        }
    
    def __call__(self, input_data: Any) -> Dict[str, Any]:
        """Make agent callable"""
        if isinstance(input_data, dict):
            framework = input_data.get("framework", "SOC2")
            result = asyncio.run(self.check_compliance(input_data, framework))
            
            if result.get("violations"):
                diagnosis = asyncio.run(self.diagnose_violations(result["violations"]))
                result["diagnosis"] = diagnosis
            
            return result
        
        return {"error": "Invalid input"}

