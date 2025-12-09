"""E1 - Parallelism Experiment: Measure throughput and speedup"""

import asyncio
import time
import uuid
from typing import Dict, Any, List, Optional
from .base import BaseExperiment
from services.orchestrator import get_orchestrator
import logging

logger = logging.getLogger(__name__)


class E1ParallelismExperiment(BaseExperiment):
    """E1: Parallelism experiment measuring throughput and speedup"""
    
    def __init__(self):
        super().__init__(
            experiment_type="e1",
            name="Parallelism Experiment",
            description="Measure task throughput, p95 queue wait, p95 run time, speedup vs sequential"
        )
    
    async def run(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Run E1 experiment"""
        config = config or {}
        num_tasks = config.get("num_tasks", 100)
        max_parallel = config.get("max_parallel", 10)
        
        await self.start_run(config)
        
        try:
            # Generate task graph
            orchestrator = get_orchestrator()
            
            # Create tasks with unique IDs
            import uuid
            tasks = []
            for i in range(num_tasks):
                tasks.append({
                    "id": f"e1-{uuid.uuid4()}",
                    "name": f"Task {i}",
                    "agent_type": "test",
                    "input_data": {"task_id": i}
                })
            
            # Create dependencies (simple chain for some tasks)
            dependencies = []
            # Make first 10 tasks depend on each other in a chain
            for i in range(1, min(10, num_tasks)):
                dependencies.append({
                    "task_id": tasks[i]["id"],
                    "depends_on_task_id": tasks[i-1]["id"]
                })
            
            graph_id = await orchestrator.create_task_graph(
                name=f"E1-{uuid.uuid4()}",
                tasks=tasks,
                dependencies=dependencies
            )
            
            # Register test agent
            async def test_agent(input_data):
                await asyncio.sleep(0.1)  # Simulate work
                return {"result": "success", "input": input_data}
            
            orchestrator.register_agent("test", test_agent)
            
            # Run sequential baseline
            start_time = time.time()
            sequential_results = await self._run_sequential(tasks[:10])  # Sample
            sequential_time = time.time() - start_time
            await self.record_metric("sequential_time", sequential_time, "seconds")
            
            # Run parallel execution
            start_time = time.time()
            parallel_results = await orchestrator.execute_task_graph(graph_id, max_parallel)
            parallel_time = time.time() - start_time
            
            # Record metrics
            await self.record_metric("parallel_time", parallel_time, "seconds")
            await self.record_metric("throughput", num_tasks / parallel_time, "tasks/second")
            await self.record_metric("speedup", sequential_time / parallel_time if parallel_time > 0 else 0)
            await self.record_metric("num_tasks", num_tasks)
            await self.record_metric("max_parallel", max_parallel)
            await self.record_metric("completed_tasks", parallel_results.get("completed", 0))
            await self.record_metric("failed_tasks", parallel_results.get("failed", 0))
            
            results = {
                "graph_id": graph_id,
                "sequential_time": sequential_time,
                "parallel_time": parallel_time,
                "speedup": sequential_time / parallel_time if parallel_time > 0 else 0,
                "throughput": num_tasks / parallel_time if parallel_time > 0 else 0,
                "parallel_results": parallel_results
            }
            
            await self.complete_run(results)
            return results
            
        except Exception as e:
            logger.error(f"E1 experiment failed: {str(e)}")
            await self.fail_run(str(e))
            raise
    
    async def _run_sequential(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Run tasks sequentially for baseline"""
        results = []
        for task in tasks:
            await asyncio.sleep(0.1)  # Simulate work
            results.append({"task_id": task["id"], "status": "completed"})
        return results

