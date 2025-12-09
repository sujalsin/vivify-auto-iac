"""Vibe Orchestrator - Multi-agent coordination"""

import asyncio
import uuid
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
import logging
from database.connection import get_db_pool
from database.models import TaskGraph, Task, TaskDependency

logger = logging.getLogger(__name__)


class OrchestratorState:
    """State for orchestrator graph"""
    def __init__(self):
        self.graph_id: Optional[str] = None
        self.tasks: Dict[str, Task] = {}
        self.completed_tasks: List[str] = []
        self.failed_tasks: List[str] = []
        self.current_task_id: Optional[str] = None
        self.results: Dict[str, Any] = {}


class VibeOrchestrator:
    """Central controller that delegates work to specialist agents"""
    
    def __init__(self):
        self.agents: Dict[str, Callable] = {}
        self.graph = self._build_graph()
    
    def register_agent(self, agent_type: str, agent_func: Callable):
        """Register a specialist agent"""
        self.agents[agent_type] = agent_func
        logger.info(f"Registered agent: {agent_type}")
    
    def _build_graph(self):
        """Build workflow graph (simplified without LangGraph)"""
        # Simplified workflow - just return None, we'll use direct execution
        return None
    
    async def _run_requirements_agent(self, state: OrchestratorState):
        """Run requirements agent"""
        if "requirements" in self.agents:
            agent = self.agents["requirements"]
            result = await agent(state.results.get("input", ""))
            state.results["requirements"] = result
        return state
    
    async def _run_architecture_agent(self, state: OrchestratorState):
        """Run architecture agent"""
        if "architecture" in self.agents:
            agent = self.agents["architecture"]
            result = await agent(state.results.get("requirements", {}))
            state.results["architecture"] = result
        return state
    
    async def _run_iac_agent(self, state: OrchestratorState):
        """Run IaC generation agent"""
        if "iac" in self.agents:
            agent = self.agents["iac"]
            result = await agent(state.results.get("architecture", {}))
            state.results["iac"] = result
        return state
    
    async def _run_deployment_agent(self, state: OrchestratorState):
        """Run deployment agent"""
        if "deployment" in self.agents:
            agent = self.agents["deployment"]
            result = await agent(state.results.get("iac", {}))
            state.results["deployment"] = result
        return state
    
    async def _run_monitoring_agent(self, state: OrchestratorState):
        """Run monitoring agent"""
        if "monitoring" in self.agents:
            agent = self.agents["monitoring"]
            result = await agent(state.results.get("deployment", {}))
            state.results["monitoring"] = result
        return state
    
    async def _run_compliance_agent(self, state: OrchestratorState):
        """Run compliance agent"""
        if "compliance" in self.agents:
            agent = self.agents["compliance"]
            result = await agent(state.results.get("deployment", {}))
            state.results["compliance"] = result
        return state
    
    async def create_task_graph(
        self,
        name: str,
        tasks: List[Dict[str, Any]],
        dependencies: List[Dict[str, str]]
    ) -> str:
        """Create a task graph with tasks and dependencies"""
        graph_id = str(uuid.uuid4())
        pool = await get_db_pool()
        
        async with pool.acquire() as conn:
            # Create graph
            import json
            await conn.execute("""
                INSERT INTO task_graphs (id, name, status, metadata)
                VALUES ($1, $2, $3, $4::jsonb)
            """, graph_id, name, "pending", json.dumps({}))
            
            # Create tasks
            for task_data in tasks:
                task_id = task_data.get("id", str(uuid.uuid4()))
                import json
                await conn.execute("""
                    INSERT INTO tasks (
                        id, graph_id, name, status, agent_type, input_data
                    ) VALUES ($1, $2, $3, $4, $5, $6::jsonb)
                """, 
                    task_id,
                    graph_id,
                    task_data.get("name", ""),
                    "pending",
                    task_data.get("agent_type"),
                    json.dumps(task_data.get("input_data", {}))
                )
            
            # Create dependencies
            for dep in dependencies:
                await conn.execute("""
                    INSERT INTO task_dependencies (task_id, depends_on_task_id)
                    VALUES ($1, $2)
                    ON CONFLICT DO NOTHING
                """, dep["task_id"], dep["depends_on_task_id"])
        
        logger.info(f"Created task graph: {graph_id} with {len(tasks)} tasks")
        return graph_id
    
    async def execute_task_graph(
        self,
        graph_id: str,
        max_parallel: int = 10
    ) -> Dict[str, Any]:
        """Execute task graph with parallel execution"""
        pool = await get_db_pool()
        start_time = datetime.now()
        
        # Get graph and tasks
        async with pool.acquire() as conn:
            graph_row = await conn.fetchrow(
                "SELECT * FROM task_graphs WHERE id = $1", graph_id
            )
            if not graph_row:
                raise ValueError(f"Task graph {graph_id} not found")
            
            task_rows = await conn.fetch(
                "SELECT * FROM tasks WHERE graph_id = $1", graph_id
            )
            dep_rows = await conn.fetch(
                "SELECT * FROM task_dependencies WHERE task_id IN "
                "(SELECT id FROM tasks WHERE graph_id = $1)", graph_id
            )
        
        # Build dependency graph
        tasks = {row['id']: Task.from_row(row) for row in task_rows}
        dependencies: Dict[str, List[str]] = {task_id: [] for task_id in tasks.keys()}
        
        for dep_row in dep_rows:
            task_id = dep_row['task_id']
            depends_on = dep_row['depends_on_task_id']
            dependencies[task_id].append(depends_on)
        
        # Update graph status
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE task_graphs SET status = $1 WHERE id = $2",
                "running", graph_id
            )
        
        # Execute tasks in parallel respecting dependencies
        completed = set()
        running = set()
        failed = set()
        semaphore = asyncio.Semaphore(max_parallel)
        
        async def execute_task(task_id: str):
            """Execute a single task"""
            async with semaphore:
                task = tasks[task_id]
                
                # Check if dependencies are met
                deps = dependencies[task_id]
                if not all(dep_id in completed for dep_id in deps):
                    return False
                
                # Mark as running
                async with pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE tasks SET status = $1, started_at = $2 WHERE id = $3",
                        "running", datetime.now(), task_id
                    )
                
                running.add(task_id)
                
                try:
                    # Execute agent
                    if task.agent_type and task.agent_type in self.agents:
                        agent = self.agents[task.agent_type]
                        result = await agent(task.input_data or {})
                        
                        # Update task
                        import json
                        async with pool.acquire() as conn:
                            await conn.execute("""
                                UPDATE tasks 
                                SET status = $1, output_data = $2::jsonb, completed_at = $3
                                WHERE id = $4
                            """, "completed", json.dumps(result), datetime.now(), task_id)
                        
                        completed.add(task_id)
                        return True
                    else:
                        # No agent, mark as completed
                        async with pool.acquire() as conn:
                            await conn.execute(
                                "UPDATE tasks SET status = $1, completed_at = $2 WHERE id = $3",
                                "completed", datetime.now(), task_id
                            )
                        completed.add(task_id)
                        return True
                        
                except Exception as e:
                    logger.error(f"Task {task_id} failed: {str(e)}")
                    async with pool.acquire() as conn:
                        await conn.execute("""
                            UPDATE tasks 
                            SET status = $1, error_message = $2, completed_at = $3
                            WHERE id = $4
                        """, "failed", str(e), datetime.now(), task_id)
                    failed.add(task_id)
                    return False
                finally:
                    running.discard(task_id)
        
        # Main execution loop
        while len(completed) + len(failed) < len(tasks):
            # Find ready tasks
            ready_tasks = [
                task_id for task_id in tasks.keys()
                if task_id not in completed and task_id not in failed and task_id not in running
                and all(dep_id in completed for dep_id in dependencies[task_id])
            ]
            
            if not ready_tasks and not running:
                # Deadlock or all failed
                break
            
            # Execute ready tasks
            await asyncio.gather(*[execute_task(task_id) for task_id in ready_tasks])
            await asyncio.sleep(0.1)  # Small delay to prevent busy waiting
        
        # Update graph status
        end_time = datetime.now()
        final_status = "completed" if len(failed) == 0 else "failed"
        
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE task_graphs SET status = $1, updated_at = $2 WHERE id = $3",
                final_status, end_time, graph_id
            )
        
        return {
            "graph_id": graph_id,
            "status": final_status,
            "completed": len(completed),
            "failed": len(failed),
            "total": len(tasks),
            "duration_seconds": (end_time - start_time).total_seconds()
        }


# Global orchestrator instance
_orchestrator: Optional[VibeOrchestrator] = None


def get_orchestrator() -> VibeOrchestrator:
    """Get or create orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = VibeOrchestrator()
    return _orchestrator

