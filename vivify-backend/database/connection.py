"""Database connection pool management"""

import os
import asyncpg
from typing import Optional
import logging

logger = logging.getLogger(__name__)

_db_pool: Optional[asyncpg.Pool] = None


async def get_db_pool() -> asyncpg.Pool:
    """Get or create database connection pool"""
    global _db_pool
    
    if _db_pool is None:
        database_url = os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres@localhost:5432/vivify"
        )
        
        # Parse connection string and use explicit parameters
        import re
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgres://", 1)
        
        # Extract connection parameters
        match = re.match(r'postgres://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', database_url)
        if match:
            user, password, host, port, database = match.groups()
            _db_pool = await asyncpg.create_pool(
                host=host,
                port=int(port),
                user=user,
                password=password,
                database=database,
                min_size=2,
                max_size=10,
                command_timeout=60
            )
        else:
            # Fallback to URL string
            _db_pool = await asyncpg.create_pool(
                database_url,
                min_size=2,
                max_size=10,
                command_timeout=60
            )
        logger.info("Database connection pool created")
    
    return _db_pool


async def init_db():
    """Initialize database schema"""
    pool = await get_db_pool()
    
    async with pool.acquire() as conn:
        # Create task_graphs table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS task_graphs (
                id VARCHAR(255) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                status VARCHAR(50) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata JSONB
            )
        """)
        
        # Create tasks table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id VARCHAR(255) PRIMARY KEY,
                graph_id VARCHAR(255) NOT NULL REFERENCES task_graphs(id) ON DELETE CASCADE,
                name VARCHAR(255) NOT NULL,
                status VARCHAR(50) NOT NULL,
                agent_type VARCHAR(100),
                input_data JSONB,
                output_data JSONB,
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (graph_id) REFERENCES task_graphs(id)
            )
        """)
        
        # Create task_dependencies table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS task_dependencies (
                id SERIAL PRIMARY KEY,
                task_id VARCHAR(255) NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                depends_on_task_id VARCHAR(255) NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                UNIQUE(task_id, depends_on_task_id)
            )
        """)
        
        # Create experiments table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS experiments (
                id VARCHAR(255) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                experiment_type VARCHAR(50) NOT NULL,
                config JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create experiment_runs table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS experiment_runs (
                id VARCHAR(255) PRIMARY KEY,
                experiment_id VARCHAR(255) NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
                status VARCHAR(50) NOT NULL,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                config JSONB,
                results JSONB
            )
        """)
        
        # Create metrics table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                id SERIAL PRIMARY KEY,
                run_id VARCHAR(255) NOT NULL REFERENCES experiment_runs(id) ON DELETE CASCADE,
                metric_name VARCHAR(255) NOT NULL,
                metric_value DOUBLE PRECISION,
                metric_unit VARCHAR(50),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata JSONB
            )
        """)
        
        # Create indexes
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_graph_id ON tasks(graph_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_task_deps_task_id ON task_dependencies(task_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_task_deps_depends_on ON task_dependencies(depends_on_task_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_experiment_runs_experiment_id ON experiment_runs(experiment_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_metrics_run_id ON metrics(run_id)")
        
        logger.info("Database schema initialized")


async def close_db():
    """Close database connection pool"""
    global _db_pool
    if _db_pool:
        await _db_pool.close()
        _db_pool = None
        logger.info("Database connection pool closed")

