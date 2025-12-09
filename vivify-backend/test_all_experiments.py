#!/usr/bin/env python3
"""Test all experiments end-to-end"""

import asyncio
import os
import sys

# Set database URL
os.environ["DATABASE_URL"] = "postgres://postgres:postgres@localhost:5433/vivify"

from experiments.e1_parallelism import E1ParallelismExperiment
from experiments.e2_deployability import E2DeployabilityExperiment
from experiments.e3_concurrency import E3ConcurrencyExperiment
from experiments.e4_canvas import E4CanvasExperiment

async def test_experiment(name, experiment, config):
    """Test a single experiment"""
    print(f"\n{'='*60}")
    print(f"Testing {name}")
    print(f"{'='*60}")
    
    try:
        results = await experiment.run(config)
        print(f"✓ {name} completed successfully")
        
        # Print key metrics
        if name == "E1":
            print(f"  Throughput: {results.get('throughput', 0):.2f} tasks/s")
            print(f"  Speedup: {results.get('speedup', 0):.2f}x")
        elif name == "E2":
            pass_itr_5 = results.get('passItr@5', 0)
            if isinstance(pass_itr_5, (int, float)):
                print(f"  passItr@5: {pass_itr_5:.2%}")
            else:
                print(f"  passItr@5: {pass_itr_5}")
            results_data = results.get('results', {})
            if isinstance(results_data, dict):
                print(f"  Successful deployments: {results_data.get('successful_deployments', 0)}")
            else:
                print(f"  Results: {len(results_data) if isinstance(results_data, list) else 'N/A'}")
        elif name == "E3":
            print(f"  Convergence time: {results.get('convergence_time', 0):.2f}s")
            print(f"  Rollback success rate: {results.get('rollback_success_rate', 0):.2%}")
        elif name == "E4":
            canvas_100 = results.get('canvas_100', {})
            print(f"  Canvas 100 nodes - FPS: {canvas_100.get('fps', 0):.2f}")
            print(f"  Canvas 100 nodes - P95 Latency: {canvas_100.get('p95_latency', 0):.2f}ms")
        
        return True
    except Exception as e:
        print(f"✗ {name} failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all experiments"""
    print("\n" + "="*60)
    print("End-to-End Experiment Testing")
    print("="*60)
    
    results = {}
    
    # Test E1
    e1 = E1ParallelismExperiment()
    results['E1'] = await test_experiment("E1", e1, {"num_tasks": 20, "max_parallel": 5})
    
    # Test E2
    e2 = E2DeployabilityExperiment()
    results['E2'] = await test_experiment("E2", e2, {"max_iterations": 3})
    
    # Test E3
    e3 = E3ConcurrencyExperiment()
    results['E3'] = await test_experiment("E3", e3, {"num_stacks": 5})
    
    # Test E4
    e4 = E4CanvasExperiment()
    results['E4'] = await test_experiment("E4", e4, {"num_sessions": 50, "canvas_sizes": [100, 500]})
    
    # Summary
    print(f"\n{'='*60}")
    print("Test Summary")
    print(f"{'='*60}")
    
    for name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n✅ All experiments passed! Ready for AWS testing.")
        return 0
    else:
        print("\n⚠️  Some experiments failed. Please fix issues before AWS testing.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

