#!/usr/bin/env python3
"""
GCP Load Testing Script
Runs experiments with higher load to test GCP performance
"""

import asyncio
import os
import sys
import time
from datetime import datetime
from typing import Dict, Any

# Set environment variables
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/vivify")

from experiments.e1_parallelism import E1ParallelismExperiment
from experiments.e2_deployability import E2DeployabilityExperiment
from experiments.e3_concurrency import E3ConcurrencyExperiment
from experiments.e4_canvas import E4CanvasExperiment
from database.connection import init_db


async def run_load_test():
    """Run GCP load testing with higher load configurations"""
    
    print("\n" + "="*70)
    print("🚀 GCP Load Testing")
    print("="*70)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Initialize database
    await init_db()
    
    results = {}
    start_time = time.time()
    
    # E1 - High Parallelism Load Test
    print("\n" + "="*70)
    print("📊 E1: High Parallelism Load Test")
    print("="*70)
    print("Configuration: 500 tasks, 50 max parallel")
    try:
        e1 = E1ParallelismExperiment()
        e1_results = await e1.run({"num_tasks": 500, "max_parallel": 50})
        results['e1'] = {
            "status": "success",
            "throughput": e1_results.get('throughput', 0),
            "speedup": e1_results.get('speedup', 0),
            "completed_tasks": e1_results.get('completed_tasks', 0)
        }
        print(f"✅ E1 Completed: Throughput={results['e1']['throughput']:.2f} tasks/s")
    except Exception as e:
        results['e1'] = {"status": "failed", "error": str(e)}
        print(f"❌ E1 Failed: {str(e)}")
    
    # E2 - High Deployability Load Test
    print("\n" + "="*70)
    print("📊 E2: High Deployability Load Test")
    print("="*70)
    print("Configuration: 20 prompts, 10 max iterations")
    try:
        e2 = E2DeployabilityExperiment()
        e2_results = await e2.run({"max_iterations": 10})
        results['e2'] = {
            "status": "success",
            "passItr@5": e2_results.get('passItr@5', 0),
            "passItr@10": e2_results.get('passItr@10', 0),
            "total_prompts": e2_results.get('total_prompts', 0)
        }
        print(f"✅ E2 Completed: passItr@5={results['e2']['passItr@5']:.2%}")
    except Exception as e:
        results['e2'] = {"status": "failed", "error": str(e)}
        print(f"❌ E2 Failed: {str(e)}")
    
    # E3 - High Concurrency Load Test
    print("\n" + "="*70)
    print("📊 E3: High Concurrency Load Test")
    print("="*70)
    print("Configuration: 50 concurrent stacks")
    try:
        e3 = E3ConcurrencyExperiment()
        e3_results = await e3.run({"num_stacks": 50})
        results['e3'] = {
            "status": "success",
            "convergence_time": e3_results.get('convergence_time', 0),
            "rollback_success_rate": e3_results.get('rollback_success_rate', 0),
            "num_stacks": e3_results.get('num_stacks', 0)
        }
        print(f"✅ E3 Completed: Convergence time={results['e3']['convergence_time']:.2f}s")
    except Exception as e:
        results['e3'] = {"status": "failed", "error": str(e)}
        print(f"❌ E3 Failed: {str(e)}")
    
    # E4 - High Canvas Load Test
    print("\n" + "="*70)
    print("📊 E4: High Canvas Load Test")
    print("="*70)
    print("Configuration: 2000 sessions, 30 events/sec")
    try:
        e4 = E4CanvasExperiment()
        e4_results = await e4.run({
            "num_sessions": 2000,
            "events_per_sec": 30,
            "canvas_sizes": [100, 500, 1500],
            "duration_seconds": 15
        })
        results['e4'] = {
            "status": "success",
            "num_sessions": e4_results.get('num_sessions', 0),
            "events_per_sec": e4_results.get('events_per_sec', 0)
        }
        print(f"✅ E4 Completed: {results['e4']['num_sessions']} sessions")
    except Exception as e:
        results['e4'] = {"status": "failed", "error": str(e)}
        print(f"❌ E4 Failed: {str(e)}")
    
    # Summary
    total_time = time.time() - start_time
    print("\n" + "="*70)
    print("📈 Load Test Summary")
    print("="*70)
    print(f"Total time: {total_time:.2f} seconds")
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    for exp_name, exp_results in results.items():
        status = "✅" if exp_results.get("status") == "success" else "❌"
        print(f"{status} {exp_name.upper()}: {exp_results.get('status', 'unknown')}")
        if exp_results.get("status") == "success":
            for key, value in exp_results.items():
                if key != "status":
                    print(f"   {key}: {value}")
        else:
            print(f"   Error: {exp_results.get('error', 'Unknown error')}")
    
    print("\n" + "="*70)
    print("✅ GCP Load Testing Complete!")
    print("="*70)
    
    return results


if __name__ == "__main__":
    try:
        results = asyncio.run(run_load_test())
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n⚠️  Load test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Load test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

