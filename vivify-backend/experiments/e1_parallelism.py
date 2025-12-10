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
            
            # Register test agents - 10% real LLM, 90% CPU-bound
            from services.agents import RequirementsAgent, ArchitectureAgent
            import hashlib
            import json
            
            llm_agent_available = False
            try:
                requirements_agent = RequirementsAgent()
                llm_agent_available = True
            except:
                logger.warning("LLM agent not available, using CPU-bound tasks only")
            
            async def real_llm_agent(input_data):
                """10% of tasks - real LLM agent call"""
                try:
                    task_id = input_data.get("task_id", 0)
                    prompt = f"Extract requirements from: Task {task_id} needs infrastructure"
                    result = await requirements_agent.extract_requirements(prompt)
                    return {"result": result, "type": "llm", "input": input_data}
                except Exception as e:
                    logger.error(f"LLM agent failed: {e}")
                    return {"result": {"error": str(e)}, "type": "llm_failed", "input": input_data}
            
            async def cpu_bound_agent(input_data):
                """90% of tasks - CPU-bound work (hashing, validation)"""
                task_id = input_data.get("task_id", 0)
                # CPU-intensive work: hash computation and data validation
                data = json.dumps(input_data).encode('utf-8')
                # Multiple hash iterations for CPU load
                hash_result = hashlib.sha256(data).hexdigest()
                for _ in range(100):  # Additional CPU work
                    hash_result = hashlib.sha256(hash_result.encode('utf-8')).hexdigest()
                # Data validation
                validation_result = {
                    "valid": len(hash_result) == 64,
                    "checksum": hash_result[:8]
                }
                return {"result": validation_result, "type": "cpu_bound", "input": input_data}
            
            # Register both agent types
            if llm_agent_available:
                orchestrator.register_agent("llm_task", real_llm_agent)
            orchestrator.register_agent("cpu_task", cpu_bound_agent)
            
            # Assign agent types: 10% LLM, 90% CPU-bound
            llm_count = int(num_tasks * 0.1)
            for i, task in enumerate(tasks):
                if i < llm_count and llm_agent_available:
                    task["agent_type"] = "llm_task"
                else:
                    task["agent_type"] = "cpu_task"
            
            # Run sequential baseline with real work
            start_time = time.time()
            sequential_results = await self._run_sequential(tasks[:10], llm_agent_available)  # Sample
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
    
    async def _run_sequential(self, tasks: List[Dict[str, Any]], llm_available: bool) -> List[Dict[str, Any]]:
        """Run tasks sequentially for baseline with real work"""
        import hashlib
        import json
        from services.agents import RequirementsAgent
        
        results = []
        requirements_agent = None
        if llm_available:
            try:
                requirements_agent = RequirementsAgent()
            except:
                pass
        
        for task in tasks:
            agent_type = task.get("agent_type", "cpu_task")
            input_data = task.get("input_data", {})
            
            if agent_type == "llm_task" and requirements_agent:
                # Real LLM work
                try:
                    prompt = f"Extract requirements from: Task {input_data.get('task_id', 0)}"
                    await requirements_agent.extract_requirements(prompt)
                except:
                    pass
            else:
                # CPU-bound work
                data = json.dumps(input_data).encode('utf-8')
                hash_result = hashlib.sha256(data).hexdigest()
                for _ in range(100):
                    hash_result = hashlib.sha256(hash_result.encode('utf-8')).hexdigest()
            
            results.append({"task_id": task["id"], "status": "completed"})
        return results

