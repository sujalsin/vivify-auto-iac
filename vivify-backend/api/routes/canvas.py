"""Canvas WebSocket endpoint for E4 experiment"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Set
import asyncio
import json
import time
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Store active connections
active_connections: Set[WebSocket] = set()
connection_metrics: Dict[str, Dict] = {}


@router.websocket("/ws/canvas")
async def websocket_canvas(websocket: WebSocket):
    """WebSocket endpoint for canvas updates"""
    await websocket.accept()
    active_connections.add(websocket)
    connection_id = id(websocket)
    connection_metrics[connection_id] = {
        "messages_sent": 0,
        "messages_received": 0,
        "latencies": [],
        "start_time": time.time()
    }
    
    logger.info(f"WebSocket connection established: {connection_id}")
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            recv_time = time.time()
            
            try:
                message = json.loads(data)
                message_type = message.get("type", "unknown")
                
                # Track received message
                connection_metrics[connection_id]["messages_received"] += 1
                
                # Handle different message types
                if message_type == "ping":
                    # Respond with pong
                    response = {
                        "type": "pong",
                        "timestamp": recv_time,
                        "session_id": message.get("session_id")
                    }
                    await websocket.send_text(json.dumps(response))
                    connection_metrics[connection_id]["messages_sent"] += 1
                
                elif message_type == "update":
                    # Broadcast update to all connected clients
                    broadcast_message = {
                        "type": "canvas_update",
                        "data": message.get("data", {}),
                        "timestamp": recv_time,
                        "session_id": message.get("session_id")
                    }
                    
                    # Measure latency: send and wait for acknowledgment
                    send_start = time.time()
                    await websocket.send_text(json.dumps(broadcast_message))
                    send_time = time.time() - send_start
                    
                    connection_metrics[connection_id]["messages_sent"] += 1
                    connection_metrics[connection_id]["latencies"].append(send_time * 1000)  # Convert to ms
                    
                    # Keep only last 100 latencies
                    if len(connection_metrics[connection_id]["latencies"]) > 100:
                        connection_metrics[connection_id]["latencies"] = connection_metrics[connection_id]["latencies"][-100:]
                
                elif message_type == "echo":
                    # Echo back for latency measurement
                    echo_response = {
                        "type": "echo_response",
                        "original_timestamp": message.get("timestamp"),
                        "response_timestamp": recv_time,
                        "session_id": message.get("session_id")
                    }
                    await websocket.send_text(json.dumps(echo_response))
                    connection_metrics[connection_id]["messages_sent"] += 1
                    
                    # Calculate round-trip latency
                    if "timestamp" in message:
                        latency = (recv_time - message["timestamp"]) * 1000  # Convert to ms
                        connection_metrics[connection_id]["latencies"].append(latency)
                
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received from {connection_id}")
            except Exception as e:
                logger.error(f"Error processing message: {e}")
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        active_connections.discard(websocket)
        if connection_id in connection_metrics:
            del connection_metrics[connection_id]


@router.get("/ws/canvas/metrics")
async def get_websocket_metrics():
    """Get WebSocket connection metrics"""
    total_connections = len(active_connections)
    total_messages_sent = sum(m["messages_sent"] for m in connection_metrics.values())
    total_messages_received = sum(m["messages_received"] for m in connection_metrics.values())
    
    all_latencies = []
    for metrics in connection_metrics.values():
        all_latencies.extend(metrics["latencies"])
    
    avg_latency = sum(all_latencies) / len(all_latencies) if all_latencies else 0
    
    return {
        "active_connections": total_connections,
        "total_messages_sent": total_messages_sent,
        "total_messages_received": total_messages_received,
        "avg_latency_ms": avg_latency,
        "connection_details": {
            str(conn_id): {
                "messages_sent": m["messages_sent"],
                "messages_received": m["messages_received"],
                "avg_latency_ms": sum(m["latencies"]) / len(m["latencies"]) if m["latencies"] else 0
            }
            for conn_id, m in connection_metrics.items()
        }
    }

