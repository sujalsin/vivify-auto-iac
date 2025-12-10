"""Cloud Compliance Agent - detects violations, compliance with security frameworks"""

import os
import asyncio
from typing import Dict, Any, List, Optional
import logging
from google.cloud import storage
from google.cloud import securitycenter_v1
from google.oauth2 import service_account

logger = logging.getLogger(__name__)


class ComplianceAgent:
    """Checks compliance with security frameworks using Security Command Center or IAM policies"""
    
    def __init__(self):
        self.frameworks = ["SOC2", "PCI-DSS"]
        self.project_id = os.getenv("GCP_PROJECT_ID")
        self.credentials = None
        
        # Load credentials if available
        creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if creds_path and os.path.exists(creds_path):
            try:
                self.credentials = service_account.Credentials.from_service_account_file(creds_path)
            except Exception as e:
                logger.warning(f"Failed to load credentials: {e}")
    
    async def check_compliance(
        self,
        deployment_data: Dict[str, Any],
        framework: str = "SOC2"
    ) -> Dict[str, Any]:
        """Check compliance with security framework using SCC or IAM fallback"""
        
        violations = []
        checks = []
        
        # Try Security Command Center first
        scc_violations = await self._check_scc(framework)
        if scc_violations is not None:
            violations.extend(scc_violations)
        else:
            # Fallback to IAM policy checks if SCC unavailable
            logger.info("SCC unavailable, using IAM policy checks")
            iam_violations = await self._check_iam_policies(deployment_data)
            violations.extend(iam_violations)
        
        compliance_score = 100.0 - (len(violations) * 10.0)
        compliance_score = max(0.0, compliance_score)
        
        return {
            "framework": framework,
            "compliant": len(violations) == 0,
            "compliance_score": compliance_score,
            "violations": violations,
            "checks": checks,
            "method": "scc" if scc_violations is not None else "iam"
        }
    
    async def _check_scc(self, framework: str) -> Optional[List[Dict[str, Any]]]:
        """Check Security Command Center for findings"""
        if not self.project_id:
            return None
        
        try:
            client = securitycenter_v1.SecurityCenterClient(credentials=self.credentials)
            
            # Try to get organization ID from project
            # Note: SCC requires organization-level setup
            parent = f"projects/{self.project_id}"
            
            # List findings
            findings = client.list_findings(
                parent=parent,
                filter='state="ACTIVE"'
            )
            
            violations = []
            for finding in findings:
                if finding.severity in [securitycenter_v1.Finding.Severity.HIGH, 
                                       securitycenter_v1.Finding.Severity.CRITICAL]:
                    violations.append({
                        "resource": finding.resource_name,
                        "violation": finding.category,
                        "severity": finding.severity.name,
                        "framework": framework,
                        "description": finding.description
                    })
            
            return violations
            
        except Exception as e:
            # SCC might not be available (personal projects, no org setup)
            logger.info(f"SCC check failed (may not be available): {e}")
            return None
    
    async def _check_iam_policies(self, deployment_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check IAM policies for compliance violations (fallback method)"""
        violations = []
        
        if not self.project_id:
            return violations
        
        try:
            storage_client = storage.Client(
                project=self.project_id,
                credentials=self.credentials
            )
            
            resources = deployment_data.get("resources", [])
            
            # Check storage buckets for public access
            for resource in resources:
                resource_type = resource.get("type", "")
                resource_id = resource.get("id", "")
                
                if resource_type in ["google_storage_bucket", "s3"]:
                    bucket_name = resource.get("config", {}).get("bucket_name", resource_id)
                    # Remove prefix if present
                    if bucket_name.startswith("vivify-"):
                        bucket_name = bucket_name.replace("vivify-", "", 1)
                    
                    try:
                        bucket = storage_client.bucket(bucket_name)
                        iam_policy = bucket.get_iam_policy(requested_policy_version=3)
                        
                        # Check for public access
                        for binding in iam_policy.bindings:
                            if binding.role in ["roles/storage.objectViewer", "roles/storage.objectCreator", "roles/storage.legacyBucketReader"]:
                                if "allUsers" in binding.members or "allAuthenticatedUsers" in binding.members:
                                    violations.append({
                                        "resource": resource_id,
                                        "violation": f"Public access to storage bucket {bucket_name}",
                                        "severity": "high",
                                        "framework": "SOC2",
                                        "details": f"Role {binding.role} granted to {binding.members}"
                                    })
                    except Exception as e:
                        logger.warning(f"Failed to check IAM for bucket {bucket_name}: {e}")
                        # Bucket might not exist yet, continue
                        continue
            
            return violations
            
        except Exception as e:
            logger.error(f"IAM policy check failed: {e}")
            return violations
    
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

