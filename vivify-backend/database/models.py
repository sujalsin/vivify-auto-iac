"""Database models for task graphs, experiments, and metrics"""

from typing import Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass, asdict
import json


@dataclass
class TaskGraph:
    """Task graph model"""
    id: str
    name: str
    status: str  # pending, running, completed, failed
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @classmethod
    def from_row(cls, row):
        """Create from database row"""
        return cls(
            id=row['id'],
            name=row['name'],
            status=row['status'],
            created_at=row.get('created_at'),
            updated_at=row.get('updated_at'),
            metadata=row.get('metadata') or {}
        )
    
    def to_dict(self):
        result = asdict(self)
        # Convert datetime to ISO string
        for key, value in result.items():
            if isinstance(value, datetime):
                result[key] = value.isoformat()
        return result


@dataclass
class Task:
    """Task model"""
    id: str
    graph_id: str
    name: str
    status: str  # pending, running, completed, failed, retrying
    agent_type: Optional[str] = None
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    @classmethod
    def from_row(cls, row):
        """Create from database row"""
        return cls(
            id=row['id'],
            graph_id=row['graph_id'],
            name=row['name'],
            status=row['status'],
            agent_type=row.get('agent_type'),
            input_data=row.get('input_data') or {},
            output_data=row.get('output_data') or {},
            error_message=row.get('error_message'),
            retry_count=row.get('retry_count', 0),
            created_at=row.get('created_at'),
            started_at=row.get('started_at'),
            completed_at=row.get('completed_at')
        )
    
    def to_dict(self):
        result = asdict(self)
        # Convert datetime to ISO string
        for key, value in result.items():
            if isinstance(value, datetime):
                result[key] = value.isoformat()
        return result


@dataclass
class TaskDependency:
    """Task dependency model"""
    id: Optional[int] = None
    task_id: Optional[str] = None
    depends_on_task_id: Optional[str] = None
    
    @classmethod
    def from_row(cls, row):
        """Create from database row"""
        return cls(
            id=row.get('id'),
            task_id=row.get('task_id'),
            depends_on_task_id=row.get('depends_on_task_id')
        )


@dataclass
class Experiment:
    """Experiment model"""
    id: str
    name: str
    description: Optional[str] = None
    experiment_type: str = ""  # e1, e2, e3, e4
    config: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    
    @classmethod
    def from_row(cls, row):
        """Create from database row"""
        return cls(
            id=row['id'],
            name=row['name'],
            description=row.get('description'),
            experiment_type=row['experiment_type'],
            config=row.get('config') or {},
            created_at=row.get('created_at')
        )


@dataclass
class ExperimentRun:
    """Experiment run model"""
    id: str
    experiment_id: str
    status: str  # running, completed, failed
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    config: Optional[Dict[str, Any]] = None
    results: Optional[Dict[str, Any]] = None
    
    @classmethod
    def from_row(cls, row):
        """Create from database row"""
        return cls(
            id=row['id'],
            experiment_id=row['experiment_id'],
            status=row['status'],
            started_at=row.get('started_at'),
            completed_at=row.get('completed_at'),
            config=row.get('config') or {},
            results=row.get('results') or {}
        )


@dataclass
class Metric:
    """Metric model"""
    id: Optional[int] = None
    run_id: Optional[str] = None
    metric_name: Optional[str] = None
    metric_value: Optional[float] = None
    metric_unit: Optional[str] = None
    timestamp: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @classmethod
    def from_row(cls, row):
        """Create from database row"""
        return cls(
            id=row.get('id'),
            run_id=row.get('run_id'),
            metric_name=row.get('metric_name'),
            metric_value=row.get('metric_value'),
            metric_unit=row.get('metric_unit'),
            timestamp=row.get('timestamp'),
            metadata=row.get('metadata') or {}
        )

