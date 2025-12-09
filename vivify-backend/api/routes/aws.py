"""AWS API routes"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional
from services.aws.discovery import AWSDiscoveryService
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/discover")
async def discover_aws_resources(regions: Optional[List[str]] = None):
    """Discover AWS resources"""
    try:
        use_localstack = True  # Can be configured via env
        discovery = AWSDiscoveryService(use_localstack=use_localstack)
        resources = await discovery.discover_all(regions)
        return resources
        
    except Exception as e:
        logger.error(f"AWS discovery failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

