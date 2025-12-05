#!/usr/bin/env python3
"""
SynapScribe AgentCore - FastAPI Service
Main entrypoint for Q&A orchestration
"""

import os
import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from agents.query_agent import QueryAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="SynapScribe AgentCore",
    description="Q&A orchestration service for SynapScribe MVP",
    version="1.0.0"
)

# Initialize QueryAgent
query_agent = QueryAgent()

@app.post("/invoke")
async def invoke(payload: dict):
    """
    Main entrypoint for AgentCore

    Payload format for query:
    {
        "type": "query",
        "sessionId": str,
        "lectureId": str,
        "s3Key": str,
        "connectionId": str
    }
    """
    try:
        request_type = payload.get("type")

        if not request_type:
            raise HTTPException(status_code=400, detail="Missing 'type' field in payload")

        if request_type == "query":
            # Return streaming response for Q&A
            return StreamingResponse(
                query_agent.process(payload),
                media_type="application/json"
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown request type: {request_type}"
            )

    except Exception as e:
        logger.error(f"Error in /invoke endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/end_session")
async def end_session(payload: dict):
    """
    Handle session end and batch transcription

    Payload format:
    {
        "sessionId": str,
        "lectureId": str
    }
    """
    try:
        session_id = payload.get("sessionId")
        lecture_id = payload.get("lectureId")

        if not session_id or not lecture_id:
            raise HTTPException(
                status_code=400,
                detail="Missing sessionId or lectureId"
            )

        result = await query_agent.end_session(payload)
        return result

    except Exception as e:
        logger.error(f"Error in /end_session endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "agentcore",
        "version": "1.0.0"
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "SynapScribe AgentCore",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "invoke": "/invoke (POST)",
            "end_session": "/end_session (POST)"
        }
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 5000))
    host = os.getenv("HOST", "0.0.0.0")

    logger.info(f"Starting AgentCore on {host}:{port}")

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )
