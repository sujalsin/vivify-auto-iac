#!/usr/bin/env python3
"""Quick test of E1 experiment with LocalStack"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from experiments.e1_parallelism import E1ParallelismExperiment

async def main():
    """Run a quick E1 test"""
    print("=" * 60)
    print("Quick E1 Experiment Test")
    print("=" * 60)
    print("\nThis will run E1 with minimal configuration...\n")
    
    experiment = E1ParallelismExperiment()
    
    # Small test configuration
    config = {
        "num_tasks": 10,  # Small number for quick test
        "max_parallel": 5
    }
    
    try:
        print("Starting experiment...")
        results = await experiment.run(config)
        
        print("\n" + "=" * 60)
        print("Results")
        print("=" * 60)
        print(f"Status: {results.get('parallel_results', {}).get('status', 'unknown')}")
        print(f"Completed: {results.get('parallel_results', {}).get('completed', 0)}")
        print(f"Failed: {results.get('parallel_results', {}).get('failed', 0)}")
        print(f"Throughput: {results.get('throughput', 0):.2f} tasks/second")
        print(f"Speedup: {results.get('speedup', 0):.2f}x")
        
        print("\n✓ Experiment completed successfully!")
        return 0
        
    except Exception as e:
        print(f"\n✗ Experiment failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

