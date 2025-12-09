"""Test LocalStack connectivity and basic AWS operations"""

import asyncio
import boto3
import os
from services.aws.discovery import AWSDiscoveryService
from services.aws.terraform import TerraformService
from services.aws.deployment import DeploymentService

async def test_localstack_connection():
    """Test LocalStack connection"""
    print("=" * 60)
    print("Testing LocalStack Connection")
    print("=" * 60)
    
    endpoint = os.getenv("LOCALSTACK_ENDPOINT", "http://localhost:4566")
    print(f"Endpoint: {endpoint}")
    
    # Test S3
    try:
        s3 = boto3.client(
            's3',
            endpoint_url=endpoint,
            aws_access_key_id='test',
            aws_secret_access_key='test',
            region_name='us-east-1'
        )
        buckets = s3.list_buckets()
        print("✓ S3 connection successful")
        print(f"  Buckets: {len(buckets.get('Buckets', []))}")
    except Exception as e:
        print(f"✗ S3 connection failed: {str(e)}")
        return False
    
    # Test EC2
    try:
        ec2 = boto3.client(
            'ec2',
            endpoint_url=endpoint,
            aws_access_key_id='test',
            aws_secret_access_key='test',
            region_name='us-east-1'
        )
        vpcs = ec2.describe_vpcs()
        print("✓ EC2 connection successful")
        print(f"  VPCs: {len(vpcs.get('Vpcs', []))}")
    except Exception as e:
        print(f"✗ EC2 connection failed: {str(e)}")
        return False
    
    # Test Lambda
    try:
        lambda_client = boto3.client(
            'lambda',
            endpoint_url=endpoint,
            aws_access_key_id='test',
            aws_secret_access_key='test',
            region_name='us-east-1'
        )
        functions = lambda_client.list_functions()
        print("✓ Lambda connection successful")
        print(f"  Functions: {len(functions.get('Functions', []))}")
    except Exception as e:
        print(f"✗ Lambda connection failed: {str(e)}")
        return False
    
    return True


async def test_discovery_service():
    """Test AWS discovery service"""
    print("\n" + "=" * 60)
    print("Testing Discovery Service")
    print("=" * 60)
    
    try:
        discovery = AWSDiscoveryService(use_localstack=True)
        resources = await discovery.discover_all(["us-east-1"])
        print("✓ Discovery service working")
        print(f"  Total resources: {resources.get('total_count', 0)}")
        return True
    except Exception as e:
        print(f"✗ Discovery service failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_terraform_service():
    """Test Terraform service"""
    print("\n" + "=" * 60)
    print("Testing Terraform Service")
    print("=" * 60)
    
    try:
        terraform = TerraformService()
        
        # Generate a simple config
        resources = [
            {
                "type": "s3",
                "id": "test-bucket",
                "config": {"bucket_name": "test-bucket-123"}
            }
        ]
        
        config = terraform.generate_terraform_config(resources)
        print("✓ Terraform config generation working")
        print(f"  Config length: {len(config)} characters")
        
        # Check if terraform is installed
        import subprocess
        try:
            result = subprocess.run(
                ["terraform", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print("✓ Terraform CLI is installed")
                print(f"  Version: {result.stdout.strip().split()[1]}")
            else:
                print("⚠ Terraform CLI not found or error")
        except FileNotFoundError:
            print("⚠ Terraform CLI not found in PATH")
        except Exception as e:
            print(f"⚠ Error checking Terraform: {str(e)}")
        
        return True
    except Exception as e:
        print(f"✗ Terraform service failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_deployment_service():
    """Test deployment service (without actually deploying)"""
    print("\n" + "=" * 60)
    print("Testing Deployment Service")
    print("=" * 60)
    
    try:
        deployment = DeploymentService()
        print("✓ Deployment service initialized")
        return True
    except Exception as e:
        print(f"✗ Deployment service failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_agents():
    """Test agent initialization"""
    print("\n" + "=" * 60)
    print("Testing Agents")
    print("=" * 60)
    
    try:
        from services.agents import (
            RequirementsAgent,
            ArchitectureAgent,
            IaCAgent,
            DeploymentAgent,
            MonitoringAgent,
            ComplianceAgent
        )
        
        # Check if GEMINI_API_KEY is set
        if not os.getenv("GEMINI_API_KEY"):
            print("⚠ GEMINI_API_KEY not set - agents requiring LLM will fail")
        
        # Test agents that don't need API key
        iac_agent = IaCAgent()
        print("✓ IaC Agent initialized")
        
        deployment_agent = DeploymentAgent()
        print("✓ Deployment Agent initialized")
        
        monitoring_agent = MonitoringAgent()
        print("✓ Monitoring Agent initialized")
        
        compliance_agent = ComplianceAgent()
        print("✓ Compliance Agent initialized")
        
        # Test agents that need API key (if available)
        if os.getenv("GEMINI_API_KEY"):
            try:
                req_agent = RequirementsAgent()
                print("✓ Requirements Agent initialized")
            except Exception as e:
                print(f"⚠ Requirements Agent failed: {str(e)}")
            
            try:
                arch_agent = ArchitectureAgent()
                print("✓ Architecture Agent initialized")
            except Exception as e:
                print(f"⚠ Architecture Agent failed: {str(e)}")
        else:
            print("⚠ Skipping Requirements/Architecture agents (no API key)")
        
        return True
    except Exception as e:
        print(f"✗ Agent initialization failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_database():
    """Test database connection"""
    print("\n" + "=" * 60)
    print("Testing Database Connection")
    print("=" * 60)
    
    try:
        from database.connection import get_db_pool, init_db
        
        # Initialize database
        await init_db()
        print("✓ Database schema initialized")
        
        # Test connection
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
            if result == 1:
                print("✓ Database connection successful")
                return True
            else:
                print("✗ Database query failed")
                return False
    except Exception as e:
        print(f"✗ Database connection failed: {str(e)}")
        print("  Make sure PostgreSQL is running: docker-compose up -d postgres")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("LocalStack Integration Tests")
    print("=" * 60)
    print("\nMake sure LocalStack is running:")
    print("  docker-compose up -d localstack")
    print("  or")
    print("  docker run -d -p 4566:4566 localstack/localstack\n")
    
    results = []
    
    # Test database first (required for most operations)
    results.append(("Database", await test_database()))
    
    # Test LocalStack connection
    localstack_ok = await test_localstack_connection()
    results.append(("LocalStack Connection", localstack_ok))
    
    if localstack_ok:
        # Test services
        results.append(("Discovery Service", await test_discovery_service()))
        results.append(("Terraform Service", await test_terraform_service()))
        results.append(("Deployment Service", await test_deployment_service()))
    
    # Test agents
    results.append(("Agents", await test_agents()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n✓ All tests passed! Ready to run experiments.")
    else:
        print("\n⚠ Some tests failed. Please fix issues before running experiments.")
    
    return all_passed


if __name__ == "__main__":
    asyncio.run(main())

