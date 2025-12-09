"""Cloud Architecture Agent - proposes Well-Architected AWS designs"""

import os
import json
import asyncio
from typing import Dict, Any
import google.generativeai as genai
import logging

logger = logging.getLogger(__name__)


class ArchitectureAgent:
    """Proposes Well-Architected AWS designs"""
    
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
    
    async def propose_architecture(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Propose Well-Architected AWS architecture"""
        
        services = requirements.get("services", [])
        constraints = requirements.get("constraints", {})
        
        system_prompt = """You are a Cloud Architecture Agent. Design Well-Architected AWS infrastructure.
Return a JSON object with:
- architecture: list of AWS resources with their configurations
- design_principles: Well-Architected Framework principles applied
- network_design: VPC, subnets, security groups
- high_availability: HA strategy
- security: security considerations"""
        
        user_prompt = f"Design AWS architecture for services: {services}. Constraints: {constraints}"
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        
        try:
            response = await asyncio.to_thread(self.model.generate_content, full_prompt)
            
            text = response.text
            # Extract JSON
            if "```json" in text:
                json_start = text.find("```json") + 7
                json_end = text.find("```", json_start)
                text = text[json_start:json_end].strip()
            elif "```" in text:
                json_start = text.find("```") + 3
                json_end = text.find("```", json_start)
                text = text[json_start:json_end].strip()
            
            try:
                result = json.loads(text)
            except json.JSONDecodeError:
                # Fallback architecture
                result = {
                    "architecture": [
                        {"type": "vpc", "config": {"cidr_block": "10.0.0.0/16"}},
                        {"type": "s3", "config": {"bucket_name": "app-bucket"}}
                    ],
                    "design_principles": ["Cost Optimization", "Security"],
                    "network_design": {"vpc": "10.0.0.0/16"},
                    "high_availability": "Multi-AZ",
                    "security": "Security groups and IAM"
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Architecture proposal failed: {str(e)}")
            return {
                "architecture": [],
                "error": str(e)
            }
    
    def __call__(self, input_data: Any) -> Dict[str, Any]:
        """Make agent callable"""
        if isinstance(input_data, dict):
            return asyncio.run(self.propose_architecture(input_data))
        return {"error": "Invalid input"}

