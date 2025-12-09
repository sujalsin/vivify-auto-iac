"""Pydantic models for experiments"""

from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from datetime import datetime


class ExperimentConfig(BaseModel):
    """Experiment configuration"""
    num_tasks: Optional[int] = None
    max_parallel: Optional[int] = None
    max_iterations: Optional[int] = None
    num_stacks: Optional[int] = None
    num_sessions: Optional[int] = None
    canvas_sizes: Optional[List[int]] = None
    prompts: Optional[List[Dict[str, Any]]] = None


class ExperimentRunRequest(BaseModel):
    """Request to run an experiment"""
    experiment_type: str  # e1, e2, e3, e4
    config: Optional[Dict[str, Any]] = None


class ExperimentRunResponse(BaseModel):
    """Response from experiment run"""
    run_id: str
    experiment_type: str
    status: str
    results: Optional[Dict[str, Any]] = None


class MetricResponse(BaseModel):
    """Metric response"""
    metric_name: str
    metric_value: float
    metric_unit: Optional[str] = None
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None

