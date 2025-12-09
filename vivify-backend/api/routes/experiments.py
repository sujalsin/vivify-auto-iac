"""Experiment API routes"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from api.models.experiments import (
    ExperimentRunRequest,
    ExperimentRunResponse,
    MetricResponse
)
from experiments import (
    E1ParallelismExperiment,
    E2DeployabilityExperiment,
    E3ConcurrencyExperiment,
    E4CanvasExperiment
)
from database.connection import get_db_pool
from database.models import ExperimentRun, Metric
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/run", response_model=ExperimentRunResponse)
async def run_experiment(request: ExperimentRunRequest):
    """Run an experiment"""
    try:
        # Create experiment instance
        if request.experiment_type == "e1":
            experiment = E1ParallelismExperiment()
        elif request.experiment_type == "e2":
            experiment = E2DeployabilityExperiment()
        elif request.experiment_type == "e3":
            experiment = E3ConcurrencyExperiment()
        elif request.experiment_type == "e4":
            experiment = E4CanvasExperiment()
        else:
            raise HTTPException(status_code=400, detail=f"Unknown experiment type: {request.experiment_type}")
        
        # Start experiment run
        run_id = await experiment.start_run(request.config)
        
        # Run experiment in background
        async def run_in_background():
            try:
                results = await experiment.run(request.config)
                await experiment.complete_run(results)
            except Exception as e:
                logger.error(f"Experiment {run_id} failed: {str(e)}")
                await experiment.fail_run(str(e))
        
        import asyncio
        asyncio.create_task(run_in_background())
        
        return ExperimentRunResponse(
            run_id=run_id,
            experiment_type=request.experiment_type,
            status="running",
            results=None
        )
        
    except Exception as e:
        logger.error(f"Experiment run failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/results/{run_id}", response_model=Dict[str, Any])
async def get_experiment_results(run_id: str):
    """Get experiment results"""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            run_row = await conn.fetchrow(
                "SELECT * FROM experiment_runs WHERE id = $1", run_id
            )
            
            if not run_row:
                raise HTTPException(status_code=404, detail="Experiment run not found")
            
            # Get metrics
            metric_rows = await conn.fetch(
                "SELECT * FROM metrics WHERE run_id = $1 ORDER BY timestamp", run_id
            )
            
            metrics = [Metric.from_row(row).to_dict() for row in metric_rows]
            
            run = ExperimentRun.from_row(run_row)
            
            return {
                "run_id": run.id,
                "experiment_id": run.experiment_id,
                "status": run.status,
                "results": run.results,
                "metrics": metrics
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get results: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_experiments():
    """List all experiments"""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            exp_rows = await conn.fetch("SELECT * FROM experiments ORDER BY created_at DESC")
            
            experiments = []
            for row in exp_rows:
                experiments.append({
                    "id": row["id"],
                    "name": row["name"],
                    "description": row.get("description"),
                    "experiment_type": row["experiment_type"],
                    "created_at": row.get("created_at").isoformat() if row.get("created_at") else None
                })
            
            return {"experiments": experiments}
            
    except Exception as e:
        logger.error(f"Failed to list experiments: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/runs/{experiment_id}")
async def get_experiment_runs(experiment_id: str):
    """Get runs for an experiment"""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            run_rows = await conn.fetch(
                "SELECT * FROM experiment_runs WHERE experiment_id = $1 ORDER BY started_at DESC",
                experiment_id
            )
            
            runs = []
            for row in run_rows:
                run = ExperimentRun.from_row(row)
                runs.append({
                    "id": run.id,
                    "status": run.status,
                    "started_at": run.started_at.isoformat() if run.started_at else None,
                    "completed_at": run.completed_at.isoformat() if run.completed_at else None
                })
            
            return {"runs": runs}
            
    except Exception as e:
        logger.error(f"Failed to get runs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

