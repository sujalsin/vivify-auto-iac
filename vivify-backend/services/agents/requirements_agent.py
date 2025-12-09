"""Requirements Agent - extracts services/SLAs/constraints from natural language"""

import os
import json
import asyncio
from typing import Dict, Any
import google.generativeai as genai
import logging

logger = logging.getLogger(__name__)


class RequirementsAgent:
    """Extracts structured requirements from natural language"""
    
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
    
    async def extract_requirements(self, user_input: str) -> Dict[str, Any]:
        """Extract services, SLAs, and constraints from natural language"""
        
        system_prompt = """You are a Requirements Agent. Extract structured requirements from user input.
Return a JSON object with:
- services: list of AWS services needed (e.g., ["S3", "Lambda", "VPC"])
- slas: service level agreements (availability, latency, etc.)
- constraints: technical or business constraints
- requirements: detailed requirements as structured data"""
        
        full_prompt = f"{system_prompt}\n\nUser input: {user_input}"
        
        try:
            response = await asyncio.to_thread(self.model.generate_content, full_prompt)
            
            # Parse response
            text = response.text
            # Try to extract JSON from response
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
                # Fallback: create structured response
                result = {
                    "services": ["S3", "Lambda"],  # Default
                    "slas": {},
                    "constraints": {},
                    "requirements": {"description": text}
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Requirements extraction failed: {str(e)}")
            return {
                "services": [],
                "slas": {},
                "constraints": {},
                "requirements": {"error": str(e)}
            }
    
    def __call__(self, input_data: Any) -> Dict[str, Any]:
        """Make agent callable"""
        if isinstance(input_data, str):
            import asyncio
            return asyncio.run(self.extract_requirements(input_data))
        elif isinstance(input_data, dict):
            user_input = input_data.get("user_input", "")
            import asyncio
            return asyncio.run(self.extract_requirements(user_input))
        return {"error": "Invalid input"}

