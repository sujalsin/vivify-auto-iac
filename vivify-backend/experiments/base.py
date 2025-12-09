"""Base experiment class"""

import uuid
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from abc import ABC, abstractmethod
from database.connection import get_db_pool
from database.models import Experiment, ExperimentRun, Metric
import logging

logger = logging.getLogger(__name__)


class BaseExperiment(ABC):
    """Base class for all experiments"""
    
    def __init__(self, experiment_type: str, name: str, description: str = ""):
        self.experiment_type = experiment_type
        self.name = name
        self.description = description
        self.run_id: Optional[str] = None
        self.metrics: List[Dict[str, Any]] = []
    
    async def record_metric(
        self,
        metric_name: str,
        metric_value: float,
        metric_unit: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Record a metric"""
        metric = {
            "metric_name": metric_name,
            "metric_value": metric_value,
            "metric_unit": metric_unit,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        self.metrics.append(metric)
        
        # Save to database
        if self.run_id:
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO metrics (run_id, metric_name, metric_value, metric_unit, metadata)
                    VALUES ($1, $2, $3, $4, $5)
                """, self.run_id, metric_name, metric_value, metric_unit, json.dumps(metadata or {}))
    
    async def start_run(self, config: Optional[Dict[str, Any]] = None) -> str:
        """Start an experiment run"""
        self.run_id = str(uuid.uuid4())
        pool = await get_db_pool()
        
        # Get or create experiment
        async with pool.acquire() as conn:
            exp_row = await conn.fetchrow(
                "SELECT id FROM experiments WHERE experiment_type = $1",
                self.experiment_type
            )
            
            if not exp_row:
                exp_id = str(uuid.uuid4())
                await conn.execute("""
                    INSERT INTO experiments (id, name, description, experiment_type, config)
                    VALUES ($1, $2, $3, $4, $5)
                """, exp_id, self.name, self.description, self.experiment_type, json.dumps(config or {}))
            else:
                exp_id = exp_row['id']
            
            # Create run
            await conn.execute("""
                INSERT INTO experiment_runs (id, experiment_id, status, config)
                VALUES ($1, $2, $3, $4)
            """, self.run_id, exp_id, "running", json.dumps(config or {}))
        
        logger.info(f"Started experiment run: {self.run_id}")
        return self.run_id
    
    async def complete_run(self, results: Optional[Dict[str, Any]] = None):
        """Complete an experiment run"""
        if not self.run_id:
            return
        
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute("""
                UPDATE experiment_runs
                SET status = $1, completed_at = $2, results = $3
                WHERE id = $4
            """, "completed", datetime.now(), json.dumps(results or {}), self.run_id)
        
        logger.info(f"Completed experiment run: {self.run_id}")
    
    async def fail_run(self, error: str):
        """Mark run as failed"""
        if not self.run_id:
            return
        
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute("""
                UPDATE experiment_runs
                SET status = $1, completed_at = $2, results = $3
                WHERE id = $4
            """, "failed", datetime.now(), json.dumps({"error": error}), self.run_id)
        
        logger.error(f"Failed experiment run: {self.run_id} - {error}")
    
    def export_results(self, format: str = "json") -> str:
        """Export results"""
        results = {
            "run_id": self.run_id,
            "experiment_type": self.experiment_type,
            "name": self.name,
            "metrics": self.metrics,
            "summary": self._calculate_summary()
        }
        
        if format == "json":
            return json.dumps(results, indent=2)
        elif format == "csv":
            # Simple CSV export
            lines = ["metric_name,metric_value,metric_unit,timestamp"]
            for metric in self.metrics:
                lines.append(
                    f"{metric['metric_name']},{metric['metric_value']},"
                    f"{metric.get('metric_unit', '')},{metric['timestamp']}"
                )
            return "\n".join(lines)
        
        return str(results)
    
    def _calculate_summary(self) -> Dict[str, Any]:
        """Calculate summary statistics"""
        if not self.metrics:
            return {}
        
        # Group by metric name
        by_name: Dict[str, List[float]] = {}
        for metric in self.metrics:
            name = metric["metric_name"]
            value = metric["metric_value"]
            if name not in by_name:
                by_name[name] = []
            by_name[name].append(value)
        
        summary = {}
        for name, values in by_name.items():
            if values:
                summary[name] = {
                    "count": len(values),
                    "min": min(values),
                    "max": max(values),
                    "avg": sum(values) / len(values),
                    "p95": self._percentile(values, 95) if len(values) > 1 else values[0]
                }
        
        return summary
    
    @staticmethod
    def _percentile(values: List[float], p: float) -> float:
        """Calculate percentile"""
        sorted_values = sorted(values)
        index = int(len(sorted_values) * p / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    @abstractmethod
    async def run(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Run the experiment"""
        pass

