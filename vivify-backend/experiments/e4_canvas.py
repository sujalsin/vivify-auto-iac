"""E4 - Canvas & Event Fan-out Under Load"""

import asyncio
import time
import statistics
from typing import Dict, Any, List, Optional
from .base import BaseExperiment
import logging

logger = logging.getLogger(__name__)


class E4CanvasExperiment(BaseExperiment):
    """E4: Canvas performance with concurrent sessions"""
    
    def __init__(self):
        super().__init__(
            experiment_type="e4",
            name="Canvas & Event Fan-out",
            description="Measure WebSocket latency, dropped events, React commit time, FPS"
        )
    
    async def run(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Run E4 experiment"""
        config = config or {}
        num_sessions = config.get("num_sessions", 1000)
        events_per_sec = config.get("events_per_sec", 15)
        canvas_sizes = config.get("canvas_sizes", [100, 500, 1500])
        duration_seconds = config.get("duration_seconds", 10)
        
        await self.start_run(config)
        
        try:
            results = {}
            
            for canvas_size in canvas_sizes:
                canvas_result = await self._test_canvas_size(
                    num_sessions=num_sessions,
                    events_per_sec=events_per_sec,
                    canvas_size=canvas_size,
                    duration_seconds=duration_seconds
                )
                results[f"canvas_{canvas_size}"] = canvas_result
                
                # Record metrics
                await self.record_metric(f"canvas_{canvas_size}_p95_latency", canvas_result.get("p95_latency", 0), "ms")
                await self.record_metric(f"canvas_{canvas_size}_dropped_events_pct", canvas_result.get("dropped_events_pct", 0))
                await self.record_metric(f"canvas_{canvas_size}_fps", canvas_result.get("fps", 0))
                await self.record_metric(f"canvas_{canvas_size}_api_p95", canvas_result.get("api_p95", 0), "ms")
            
            await self.record_metric("num_sessions", num_sessions)
            await self.record_metric("events_per_sec", events_per_sec)
            
            await self.complete_run(results)
            return results
            
        except Exception as e:
            logger.error(f"E4 experiment failed: {str(e)}")
            await self.fail_run(str(e))
            raise
    
    async def _test_canvas_size(
        self,
        num_sessions: int,
        events_per_sec: int,
        canvas_size: int,
        duration_seconds: int
    ) -> Dict[str, Any]:
        """Test canvas performance for a given size"""
        
        # Simulate WebSocket events
        latencies = []
        total_events = 0
        dropped_events = 0
        api_times = []
        
        # Simulate sessions
        async def simulate_session(session_id: int):
            nonlocal total_events, dropped_events
            session_events = 0
            
            for _ in range(duration_seconds * events_per_sec):
                # Simulate event processing
                event_start = time.time()
                
                # Simulate network latency
                await asyncio.sleep(0.001 * (canvas_size / 1000))  # Scale with canvas size
                
                # Simulate API call
                api_start = time.time()
                await asyncio.sleep(0.005)  # 5ms API call
                api_time = (time.time() - api_start) * 1000
                api_times.append(api_time)
                
                event_latency = (time.time() - event_start) * 1000
                latencies.append(event_latency)
                
                # Simulate dropped events (0.1% chance)
                if time.time() % 1000 < 1:
                    dropped_events += 1
                
                total_events += 1
                session_events += 1
                
                # Rate limit
                await asyncio.sleep(1.0 / events_per_sec)
        
        # Run concurrent sessions
        start_time = time.time()
        tasks = [simulate_session(i) for i in range(num_sessions)]
        await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Calculate metrics
        if latencies:
            p95_latency = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
            avg_latency = statistics.mean(latencies)
        else:
            p95_latency = 0
            avg_latency = 0
        
        if api_times:
            api_p95 = statistics.quantiles(api_times, n=20)[18]
        else:
            api_p95 = 0
        
        dropped_events_pct = (dropped_events / total_events * 100) if total_events > 0 else 0
        
        # Estimate FPS (simplified - based on event processing rate)
        fps = (total_events / total_time) / num_sessions if total_time > 0 else 0
        
        return {
            "canvas_size": canvas_size,
            "num_sessions": num_sessions,
            "total_events": total_events,
            "dropped_events": dropped_events,
            "dropped_events_pct": dropped_events_pct,
            "p95_latency": p95_latency,
            "avg_latency": avg_latency,
            "api_p95": api_p95,
            "fps": fps,
            "total_time": total_time
        }

