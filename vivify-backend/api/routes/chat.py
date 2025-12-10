"""
Chat API Routes
Handles conversational agent interactions
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from api.models.chat import ChatMessage
import json
import logging

logger = logging.getLogger(__name__)

try:
    from services.agent_service import get_agent
except ImportError as e:
    logger.warning(f"Agent service not available: {e}")
    def get_agent():
        raise ValueError("Agent service not available due to dependency issues")

router = APIRouter()


@router.post("/message")
async def send_message(request: ChatMessage):
    """
    Send a message and get streaming response
    
    Returns Server-Sent Events (SSE) stream with:
    - thinking: Agent reasoning steps
    - tool_call: Tool being called
    - tool_result: Tool execution result
    - final_answer: Final response
    - error: Error message
    """
    
    try:
        agent = get_agent()
    except (ValueError, ImportError) as e:
        raise HTTPException(
            status_code=500,
            detail=f"Agent not available: {str(e)}"
        )
    
    logger.info(f"Received message from session {request.session_id}: {request.message[:50]}...")
    
    async def event_stream():
        """Generate SSE events"""
        try:
            async for event in agent.stream_response(request.message, request.session_id):
                # Format as SSE
                data = json.dumps(event)
                yield f"data: {data}\n\n"
                
                # Log events
                event_type = event.get("type")
                if event_type == "thinking":
                    logger.debug(f"Thinking: {event.get('thought', '')[:50]}...")
                elif event_type == "tool_call":
                    logger.info(f"Tool call: {event.get('toolName')}")
                elif event_type == "final_answer":
                    logger.info(f"Final answer: {event.get('text', '')[:50]}...")
        
        except Exception as e:
            logger.error(f"Stream error: {str(e)}")
            error_event = {"type": "error", "message": str(e)}
            yield f"data: {json.dumps(error_event)}\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


@router.delete("/sessions/{session_id}")
async def clear_session(session_id: str):
    """Clear chat session memory"""
    try:
        agent = get_agent()
        agent.clear_session(session_id)
        logger.info(f"Cleared session: {session_id}")
        return {"message": f"Session {session_id} cleared successfully"}
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health():
    """Check if agent is configured and healthy"""
    try:
        agent = get_agent()
        return {
            "status": "healthy",
            "configured": True,
            "tools": [tool.name for tool in agent.tools]
        }
    except ValueError:
        return {
            "status": "not_configured",
            "configured": False,
            "message": "GEMINI_API_KEY not set"
        }
