"""Task graph API routes"""

import asyncio
from fastapi import APIRouter, HTTPException, WebSocket
from typing import Dict, Any
from api.models.task_graphs import (
    CreateTaskGraphRequest,
    TaskGraphResponse,
    TaskGraphStatusResponse
)
from services.orchestrator import get_orchestrator
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/create", response_model=TaskGraphResponse)
async def create_task_graph(request: CreateTaskGraphRequest):
    """Create a task graph"""
    try:
        orchestrator = get_orchestrator()
        
        # Convert request to task format
        tasks = []
        for task_def in request.tasks:
            tasks.append({
                "id": task_def.id,
                "name": task_def.name,
                "agent_type": task_def.agent_type,
                "input_data": task_def.input_data or {}
            })
        
        dependencies = [
            {"task_id": dep.task_id, "depends_on_task_id": dep.depends_on_task_id}
            for dep in request.dependencies
        ]
        
        graph_id = await orchestrator.create_task_graph(
            name=request.name,
            tasks=tasks,
            dependencies=dependencies
        )
        
        return TaskGraphResponse(
            graph_id=graph_id,
            name=request.name,
            status="pending"
        )
        
    except Exception as e:
        logger.error(f"Failed to create task graph: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{graph_id}/status", response_model=TaskGraphStatusResponse)
async def get_task_graph_status(graph_id: str):
    """Get task graph status"""
    try:
        from database.connection import get_db_pool
        from database.models import TaskGraph
        
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            graph_row = await conn.fetchrow(
                "SELECT * FROM task_graphs WHERE id = $1", graph_id
            )
            
            if not graph_row:
                raise HTTPException(status_code=404, detail="Task graph not found")
            
            # Count tasks
            task_counts = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
                FROM tasks WHERE graph_id = $1
            """, graph_id)
            
            graph = TaskGraph.from_row(graph_row)
            
            return TaskGraphStatusResponse(
                graph_id=graph_id,
                status=graph.status,
                completed=task_counts["completed"] or 0,
                failed=task_counts["failed"] or 0,
                total=task_counts["total"] or 0
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{graph_id}/execute")
async def execute_task_graph(graph_id: str, max_parallel: int = 10):
    """Execute a task graph"""
    try:
        orchestrator = get_orchestrator()
        results = await orchestrator.execute_task_graph(graph_id, max_parallel)
        return results
        
    except Exception as e:
        logger.error(f"Failed to execute task graph: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/{graph_id}/stream")
async def task_graph_stream(websocket: WebSocket, graph_id: str):
    """WebSocket stream for task graph updates"""
    await websocket.accept()
    
    try:
        from database.connection import get_db_pool
        
        pool = await get_db_pool()
        last_status = None
        
        while True:
            # Get current status
            async with pool.acquire() as conn:
                graph_row = await conn.fetchrow(
                    "SELECT * FROM task_graphs WHERE id = $1", graph_id
                )
                
                if not graph_row:
                    await websocket.send_json({"error": "Task graph not found"})
                    break
                
                current_status = graph_row["status"]
                
                # Send update if status changed
                if current_status != last_status:
                    await websocket.send_json({
                        "graph_id": graph_id,
                        "status": current_status,
                        "timestamp": graph_row.get("updated_at").isoformat() if graph_row.get("updated_at") else None
                    })
                    last_status = current_status
                
                # Break if completed or failed
                if current_status in ["completed", "failed"]:
                    break
            
            await asyncio.sleep(1)  # Poll every second
            
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        await websocket.send_json({"error": str(e)})
    finally:
        await websocket.close()

