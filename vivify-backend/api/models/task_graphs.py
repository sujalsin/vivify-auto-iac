"""Pydantic models for task graphs"""

from pydantic import BaseModel
from typing import Dict, Any, Optional, List


class TaskDefinition(BaseModel):
    """Task definition"""
    id: Optional[str] = None
    name: str
    agent_type: Optional[str] = None
    input_data: Optional[Dict[str, Any]] = None


class TaskDependencyDefinition(BaseModel):
    """Task dependency definition"""
    task_id: str
    depends_on_task_id: str


class CreateTaskGraphRequest(BaseModel):
    """Request to create a task graph"""
    name: str
    tasks: List[TaskDefinition]
    dependencies: List[TaskDependencyDefinition]


class TaskGraphResponse(BaseModel):
    """Task graph response"""
    graph_id: str
    name: str
    status: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class TaskGraphStatusResponse(BaseModel):
    """Task graph status response"""
    graph_id: str
    status: str
    completed: int
    failed: int
    total: int
    duration_seconds: Optional[float] = None

