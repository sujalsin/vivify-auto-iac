"""AWS resource discovery service"""

import boto3
import os
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class AWSDiscoveryService:
    """Service for discovering AWS resources"""
    
    def __init__(self, region: str = "us-east-1", use_localstack: bool = True):
        self.region = region
        self.use_localstack = use_localstack
        
        # Configure endpoint for LocalStack
        endpoint_url = None
        if use_localstack:
            endpoint_url = os.getenv("LOCALSTACK_ENDPOINT", "http://localhost:4566")
        
        # Initialize clients
        self.ec2 = boto3.client(
            'ec2',
            region_name=region,
            endpoint_url=endpoint_url,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "test"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "test")
        )
        
        self.s3 = boto3.client(
            's3',
            region_name=region,
            endpoint_url=endpoint_url,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "test"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "test")
        )
        
        self.lambda_client = boto3.client(
            'lambda',
            region_name=region,
            endpoint_url=endpoint_url,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "test"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "test")
        )
        
        self.iam = boto3.client(
            'iam',
            endpoint_url=endpoint_url,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "test"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "test")
        )
    
    async def discover_all(self, regions: Optional[List[str]] = None) -> Dict[str, Any]:
        """Discover all AWS resources"""
        if regions is None:
            regions = [self.region]
        
        resources = {
            "resources": [],
            "regions": regions,
            "total_count": 0
        }
        
        # Discover S3 buckets (once, not per region)
        try:
            s3_resources = await self._discover_s3()
            resources["resources"].extend(s3_resources)
        except Exception as e:
            logger.error(f"Error discovering S3: {str(e)}")
        
        for region in regions:
            try:
                # Discover EC2 instances
                ec2_resources = await self._discover_ec2(region)
                resources["resources"].extend(ec2_resources)
                
                # Discover Lambda functions
                lambda_resources = await self._discover_lambda(region)
                resources["resources"].extend(lambda_resources)
                
                # Discover VPCs
                vpc_resources = await self._discover_vpc(region)
                resources["resources"].extend(vpc_resources)
                
            except Exception as e:
                logger.error(f"Error discovering resources in {region}: {str(e)}")
        
        resources["total_count"] = len(resources["resources"])
        return resources
    
    async def _discover_ec2(self, region: str) -> List[Dict[str, Any]]:
        """Discover EC2 instances"""
        try:
            # Update region for this call
            if self.use_localstack:
                endpoint_url = os.getenv("LOCALSTACK_ENDPOINT", "http://localhost:4566")
                ec2_client = boto3.client(
                    'ec2',
                    region_name=region,
                    endpoint_url=endpoint_url,
                    aws_access_key_id='test',
                    aws_secret_access_key='test'
                )
            else:
                ec2_client = boto3.client(
                    'ec2',
                    region_name=region,
                    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "test"),
                    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "test")
                )
            
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, ec2_client.describe_instances)
            resources = []
            
            for reservation in response.get('Reservations', []):
                for instance in reservation.get('Instances', []):
                    resources.append({
                        "type": "ec2",
                        "id": instance.get('InstanceId'),
                        "name": next(
                            (tag['Value'] for tag in instance.get('Tags', []) if tag['Key'] == 'Name'),
                            instance.get('InstanceId')
                        ),
                        "region": region,
                        "status": instance.get('State', {}).get('Name'),
                        "instance_type": instance.get('InstanceType'),
                        "metadata": {
                            "vpc_id": instance.get('VpcId'),
                            "subnet_id": instance.get('SubnetId'),
                            "security_groups": [sg['GroupId'] for sg in instance.get('SecurityGroups', [])]
                        }
                    })
            
            return resources
        except Exception as e:
            logger.error(f"Error discovering EC2: {str(e)}")
            return []
    
    async def _discover_s3(self) -> List[Dict[str, Any]]:
        """Discover S3 buckets"""
        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, self.s3.list_buckets)
            resources = []
            
            for bucket in response.get('Buckets', []):
                created_date = bucket.get('CreationDate')
                created_str = created_date.isoformat() if created_date else None
                
                resources.append({
                    "type": "s3",
                    "id": bucket.get('Name'),
                    "name": bucket.get('Name'),
                    "region": "global",
                    "status": "active",
                    "metadata": {
                        "created": created_str
                    }
                })
            
            return resources
        except Exception as e:
            logger.error(f"Error discovering S3: {str(e)}")
            return []
    
    async def _discover_lambda(self, region: str) -> List[Dict[str, Any]]:
        """Discover Lambda functions"""
        try:
            # Update region for this call
            if self.use_localstack:
                endpoint_url = os.getenv("LOCALSTACK_ENDPOINT", "http://localhost:4566")
                lambda_client = boto3.client(
                    'lambda',
                    region_name=region,
                    endpoint_url=endpoint_url,
                    aws_access_key_id='test',
                    aws_secret_access_key='test'
                )
            else:
                lambda_client = self.lambda_client
            
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda_client.list_functions)
            resources = []
            
            for func in response.get('Functions', []):
                resources.append({
                    "type": "lambda",
                    "id": func.get('FunctionName'),
                    "name": func.get('FunctionName'),
                    "region": region,
                    "status": "active",
                    "metadata": {
                        "runtime": func.get('Runtime'),
                        "memory_size": func.get('MemorySize'),
                        "timeout": func.get('Timeout')
                    }
                })
            
            return resources
        except Exception as e:
            logger.error(f"Error discovering Lambda: {str(e)}")
            return []
    
    async def _discover_vpc(self, region: str) -> List[Dict[str, Any]]:
        """Discover VPCs"""
        try:
            # Create EC2 client for this region
            if self.use_localstack:
                endpoint_url = os.getenv("LOCALSTACK_ENDPOINT", "http://localhost:4566")
                ec2_client = boto3.client(
                    'ec2',
                    region_name=region,
                    endpoint_url=endpoint_url,
                    aws_access_key_id='test',
                    aws_secret_access_key='test'
                )
            else:
                ec2_client = boto3.client(
                    'ec2',
                    region_name=region,
                    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "test"),
                    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "test")
                )
            
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, ec2_client.describe_vpcs)
            resources = []
            
            for vpc in response.get('Vpcs', []):
                resources.append({
                    "type": "vpc",
                    "id": vpc.get('VpcId'),
                    "name": next(
                        (tag['Value'] for tag in vpc.get('Tags', []) if tag['Key'] == 'Name'),
                        vpc.get('VpcId')
                    ),
                    "region": region,
                    "status": vpc.get('State'),
                    "metadata": {
                        "cidr": vpc.get('CidrBlock'),
                        "is_default": vpc.get('IsDefault', False)
                    }
                })
            
            return resources
        except Exception as e:
            logger.error(f"Error discovering VPC: {str(e)}")
            return []

