"""Experiment runner CLI"""

import asyncio
import argparse
import json
from typing import Optional
from .e1_parallelism import E1ParallelismExperiment
from .e2_deployability import E2DeployabilityExperiment
from .e3_concurrency import E3ConcurrencyExperiment
from .e4_canvas import E4CanvasExperiment
from database.connection import init_db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_experiment(experiment_type: str, config: Optional[dict] = None):
    """Run a single experiment"""
    
    # Initialize database
    await init_db()
    
    # Create experiment instance
    if experiment_type == "e1":
        experiment = E1ParallelismExperiment()
    elif experiment_type == "e2":
        experiment = E2DeployabilityExperiment()
    elif experiment_type == "e3":
        experiment = E3ConcurrencyExperiment()
    elif experiment_type == "e4":
        experiment = E4CanvasExperiment()
    else:
        raise ValueError(f"Unknown experiment type: {experiment_type}")
    
    # Run experiment
    logger.info(f"Running experiment: {experiment_type}")
    results = await experiment.run(config)
    
    # Export results
    json_results = experiment.export_results("json")
    print("\n=== Results ===")
    print(json_results)
    
    return results


async def run_all_experiments():
    """Run all experiments"""
    await init_db()
    
    experiments = [
        ("e1", {"num_tasks": 100, "max_parallel": 10}),
        ("e2", {"max_iterations": 5}),
        ("e3", {"num_stacks": 10}),
        ("e4", {"num_sessions": 100, "canvas_sizes": [100, 500]})  # Reduced for testing
    ]
    
    all_results = {}
    
    for exp_type, config in experiments:
        try:
            logger.info(f"\n{'='*60}")
            logger.info(f"Running {exp_type}")
            logger.info(f"{'='*60}")
            
            if exp_type == "e1":
                experiment = E1ParallelismExperiment()
            elif exp_type == "e2":
                experiment = E2DeployabilityExperiment()
            elif exp_type == "e3":
                experiment = E3ConcurrencyExperiment()
            elif exp_type == "e4":
                experiment = E4CanvasExperiment()
            
            results = await experiment.run(config)
            all_results[exp_type] = results
            
            logger.info(f"✓ {exp_type} completed")
            
        except Exception as e:
            logger.error(f"✗ {exp_type} failed: {str(e)}")
            all_results[exp_type] = {"error": str(e)}
    
    # Print summary
    print("\n=== Summary ===")
    print(json.dumps(all_results, indent=2, default=str))
    
    return all_results


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(description="Run experiments")
    parser.add_argument("experiment", nargs="?", choices=["e1", "e2", "e3", "e4", "all"], help="Experiment to run")
    parser.add_argument("--config", type=str, help="JSON config file")
    
    args = parser.parse_args()
    
    config = None
    if args.config:
        with open(args.config, "r") as f:
            config = json.load(f)
    
    if args.experiment == "all" or not args.experiment:
        asyncio.run(run_all_experiments())
    else:
        asyncio.run(run_experiment(args.experiment, config))


if __name__ == "__main__":
    main()

