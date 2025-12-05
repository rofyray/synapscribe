# SynapScribe MVP/PoC Implementation Plan

**Version:** 3.0 (Simplified Architecture)
**Date:** January 2025
**Status:** Ready for Implementation

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Critical Design Changes](#critical-design-changes)
3. [Simplified Architecture](#simplified-architecture)
4. [Detailed Flows](#detailed-flows)
5. [AgentCore + Strands Implementation](#agentcore--strands-implementation)
6. [Lambda Functions](#lambda-functions)
7. [Error Handling & Resilience](#error-handling--resilience)
8. [DynamoDB Schema](#dynamodb-schema)
9. [Implementation Phases](#implementation-phases)
10. [Cost Estimates](#cost-estimates)
11. [Success Criteria](#success-criteria)
12. [Next Steps](#next-steps)

---

## Executive Summary

**SynapScribe** is a voice-first learning assistant using Qwen2.5-Omni-3B orchestrated by **Amazon Bedrock AgentCore** to enable real-time voice-to-voice Q&A on uploaded lecture audio.

**Core Use Case**: A student uploads a lecture audio file (≤25 minutes). The system automatically validates and loads it into the model's 16K context window. The student can immediately ask questions via voice and get spoken answers based on the lecture content.

**Key Design Principles**:
- ✅ **Maximum simplicity** - Minimum AWS services, single model, single agent
- ✅ **Event-driven** - S3 events trigger automatic processing (no manual orchestration)
- ✅ **Real-time streaming** - WebSocket-based voice conversations
- ✅ **No embeddings** - Lecture audio fits directly in model context (16K tokens, optimized for 2x performance)
- ✅ **Serverless-first** - Lambda functions, pay-per-use
- ✅ **Fast iteration** - 1-minute session timeout for rapid MVP testing

---

## Critical Design Changes

### Version 3.0 Simplifications

**🔴 REMOVED:**
- ❌ **IngestionAgent** - Replaced with S3 event → Lambda
- ❌ **Qwen3-Embedding-8B** - No embeddings needed (≤50 min lectures fit in context)
- ❌ **OpenSearch Serverless** - No vector storage
- ❌ **Complex ingestion pipeline** - No 7-step ASR → embeddings → summary flow
- ❌ **AWS Amplify Auth UI** - No login/signup pages
- ❌ **Cognito User Pools** - Replaced with Identity Pools (unauthenticated access)
- ❌ **DynamoDB Lectures table** - Simplified to Sessions table only
- ❌ **5-minute timeout** - Now 1 minute for faster testing

**✅ KEPT (Simplified):**
- ✅ React SPA (minimal UI, no auth forms)
- ✅ Cognito Identity Pools (automatic guest credentials)
- ✅ WebSocket API Gateway (real-time Q&A)
- ✅ Lambda functions (2 total: WebSocketHandler + ValidateLectureFunction)
- ✅ S3 (lectures/, queries/, responses/)
- ✅ EC2 g5.2xlarge + vLLM + Qwen2.5-Omni-3B (single model)
- ✅ AgentCore + **QueryAgent only** (renamed from QAAgent)
- ✅ DynamoDB Sessions table (conversation transcripts)

**🆕 ADDED:**
- 🆕 S3 PutObject event trigger (automatic lecture processing)
- 🆕 ValidateLectureFunction Lambda (validates + loads audio context)
- 🆕 1-minute inactivity timeout (fast MVP testing loop)
- 🆕 25-minute lecture limit (fits in 16K token context window - 2x performance vs 32K)
- 🆕 Post-session batch transcription

---

## Simplified Architecture

### Tech Stack Overview

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Frontend** | React (Vite) + TypeScript | SPA with audio recording and playback |
| **Authentication** | Amazon Cognito Identity Pools | Unauthenticated access (no login UI) |
| **API Layer** | WebSocket API Gateway | Real-time communication |
| **Compute** | EC2 g5.2xlarge (24GB VRAM) | GPU instance for model inference |
| **Inference Server** | vLLM (>=0.8.5) | Serves Qwen2.5-Omni-3B (ASR + Q&A) |
| **AI Model** | Qwen2.5-Omni-3B | Audio-to-audio (ASR via prompting, Chat) |
| **TTS Service** | gTTS (>=2.5.0) | Text-to-Speech generation (lightweight) |
| **Agent Framework** | Amazon Bedrock AgentCore + Strands | Single QueryAgent |
| **Storage** | S3, DynamoDB | Audio files + conversation transcripts |
| **Observability** | CloudWatch, X-Ray | Monitoring and tracing |

### Audio Processing

**vLLM (>=0.8.5)**
- Serves Qwen2.5-Omni-3B for Q&A and ASR
- ASR via prompt engineering (no separate endpoint needed)
- Uses `/v1/chat/completions` with transcription prompts
- Performance: ~2s for 30s audio
- Port: 8000

**gTTS (>=2.5.0)**
- Text-to-Speech generation
- Lightweight, no model downloads required
- OpenAI-compatible API (`/v1/audio/speech`)
- Performance: <2s for short text
- Port: 8001

**Architecture Decision:**
- Qwen2.5-Omni model has native audio generation capability
- vLLM API does not expose audio output (API limitation)
- Therefore: Use gTTS for TTS, vLLM handles ASR via prompting
- See: `docs/QWEN_INVESTIGATION_FINDINGS.md` for complete investigation details

### Components Removed for Maximum Simplicity

- ❌ **SQS** - No async queues
- ❌ **ElastiCache** - DynamoDB handles sessions
- ❌ **IngestionAgent** - S3 event → Lambda instead
- ❌ **Qwen3-Embedding-8B** - No embeddings
- ❌ **OpenSearch** - No vector storage
- ❌ **Multiple agents** - Only QueryAgent remains

### Simplified Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      FRONTEND (React + Vite)                     │
│           No Login UI - Auto Guest Credentials                   │
│    • File upload for lecture audio (≤25 min, 16K context)        │
│    • Voice recorder (MediaRecorder API)                          │
│    • Audio playback with wave animations                         │
│    • WebSocket client (persistent connection)                    │
└───────────────────────────┬─────────────────────────────────────┘
                            │ wss:// (WebSocket)
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                   AWS CLOUD                                      │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Amazon Cognito Identity Pool                                │ │
│  │ (Unauthenticated access enabled)                            │ │
│  │ → Auto-generates temporary AWS credentials                  │ │
│  └────────────────────────────────────────────────────────────┘ │
│                            │                                     │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ WebSocket API Gateway                                       │ │
│  │ • Cognito Identity Pool authorizer                          │ │
│  │ • Routes: $connect, request_upload, query                   │ │
│  └─────────────┬──────────────────────────────────────────────┘ │
│                │                                                 │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Lambda (WebSocketHandler)                                   │ │
│  │ • Connection management                                     │ │
│  │ • Generate presigned URLs for S3 uploads                    │ │
│  │ • Route query messages to AgentCore                         │ │
│  └────────────────────────────────────────────────────────────┘ │
│                            │                                     │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ S3 Bucket (synapscribe-audio)                               │ │
│  │ • lectures/  ← User uploads here via presigned URL          │ │
│  │ • queries/   ← Voice questions                              │ │
│  │ • responses/ ← TTS responses                                │ │
│  └──────┬─────────────────────────────────────────────────────┘ │
│         │                                                        │
│         │ S3 PutObject Event (lectures/* prefix)                │
│         │ Triggers automatically when lecture uploaded          │
│         ↓                                                        │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Lambda (ValidateLectureFunction)                            │ │
│  │ • Auto-triggered by S3 event (serverless automation)        │ │
│  │ • Validates: duration (≤25min), format, integrity           │ │
│  │ • Loads audio into Qwen2.5-Omni 16K context via HTTP        │ │
│  │ • Saves metadata to DynamoDB                                │ │
│  │ • Notifies frontend: "lecture_ready" via WebSocket          │ │
│  └────────────────┬───────────────────────────────────────────┘ │
│                   │ HTTP POST                                    │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ EC2 g5.2xlarge (24GB VRAM)                                  │ │
│  │                                                              │ │
│  │  ┌──────────────────────────────────────────────────────┐  │ │
│  │  │ AgentCore (Bedrock Serverless Runtime)                │  │ │
│  │  │  • QueryAgent (Strands) - ONLY AGENT                  │  │ │
│  │  └──────────────────────────────────────────────────────┘  │ │
│  │                                                              │ │
│  │  ┌──────────────────────────────────────────────────────┐  │ │
│  │  │ vLLM Inference Server (port 8000)                     │  │ │
│  │  │  • Qwen2.5-Omni-3B - SINGLE MODEL                     │  │ │
│  │  │    - ASR (Audio → Text)                               │  │ │
│  │  │    - Audio Context Loading (Lecture audio)            │  │ │
│  │  │    - Chat Completion (Q&A)                            │  │ │
│  │  │    - TTS (Text → Audio streaming, 24kHz)              │  │ │
│  │  └──────────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────┘ │
│                            │                                     │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ DynamoDB (Sessions Table)                                   │ │
│  │ • Conversation transcripts (query-response pairs)           │ │
│  │ • Lecture metadata (duration, status, s3Key)                │ │
│  │ • TTL: 7 days auto-cleanup                                  │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

**Key Architectural Decisions:**
- **Cognito Identity Pools**: Automatic guest credentials, no login UI
- **S3 Event Automation**: Lecture uploads trigger Lambda automatically (no manual orchestration)
- **Single Lambda for Lectures**: ValidateLectureFunction replaces entire IngestionAgent pipeline
- **Single Agent**: QueryAgent handles all Q&A (no IngestionAgent)
- **Single Model**: Qwen2.5-Omni-3B does ASR, TTS, Chat (no embeddings model)
- **1-Minute Timeout**: Fast session end for rapid MVP testing

---

## Detailed Flows

### Flow 1: Lecture Upload (Event-Driven with S3 Trigger)

**User Action**: Student uploads lecture audio file (≤25 minutes)

**Flow**:
```
Duration: ~5-10 seconds for 25-minute lecture

1. User selects audio file (mp3, wav, m4a, ogg, webm)
   ↓
2. Frontend validates client-side:
   - Duration: ≤ 1500 seconds (25 minutes)
   - Size: ≤ 50MB (25-min audio @ ~128kbps)
   - Format: supported audio types
   ↓
3. Frontend → WebSocket → "request_upload"
   {
     "type": "request_upload",
     "fileName": "lecture.mp3",
     "fileSize": 50000000,
     "duration": 2850,
     "connectionId": "abc123"
   }
   ↓
4. Lambda (WebSocketHandler):
   - Generates presigned S3 URL for lectures/ prefix
   - Attaches metadata: connectionId (for notification later)
   - Returns to frontend:
   {
     "type": "upload_url",
     "uploadUrl": "https://s3.../lectures/uuid.mp3?signature=...",
     "lectureId": "uuid",
     "expiresIn": 900  // 15 minutes
   }
   ↓
5. Frontend uploads directly to S3 using presigned URL
   - XHR/fetch with progress tracking
   - Shows progress bar: "Uploading... 45%"
   - No Lambda payload limits (direct S3 upload)
   ↓
6. **S3 PutObject event AUTOMATICALLY triggers Lambda** ⚡
   - Event type: s3:ObjectCreated:*
   - Filter: lectures/* prefix
   - No manual WebSocket message needed!
   ↓
7. Lambda (ValidateLectureFunction) - Auto-invoked by S3:

   a. Parse S3 event → extract bucket, key, size, metadata

   b. Download audio from S3 (streaming, not full download)

   c. Validate audio:
      - Format: mp3/wav/m4a/ogg/webm (check file header)
      - Duration: ≤ 1500 seconds (25 min) using librosa
      - Integrity: librosa.load() succeeds (not corrupted)
      - Sample rate: ≥ 8000Hz
      - Not silent: max amplitude > 0.001

   d. Load audio into Qwen2.5-Omni 16K context:
      POST http://ec2-private-ip:8000/v1/audio/context
      {
        "audio_file_s3": "s3://bucket/lectures/uuid.mp3",
        "lecture_id": "uuid",
        "max_context_tokens": 16384
      }
      Response: { "status": "loaded", "tokens_used": 14253 }

   e. Save lecture metadata to DynamoDB Sessions table:
      {
        "lectureId": "uuid",
        "s3Key": "lectures/uuid.mp3",
        "duration": 2850,
        "status": "ready",
        "tokensUsed": 28453,
        "createdAt": "2025-01-20T10:30:00Z"
      }

   f. Extract connectionId from S3 object metadata

   g. Notify frontend via API Gateway WebSocket Management API:
      POST https://{api-id}.execute-api.us-east-1.amazonaws.com/@connections/{connectionId}
      {
        "type": "lecture_ready",
        "lectureId": "uuid",
        "message": "Lecture loaded! Ready for questions.",
        "duration": 2850
      }
   ↓
8. Frontend receives "lecture_ready" notification
   - Hide upload UI
   - Show Q&A interface: "Ask me anything about this lecture"
   - Enable voice recording button
```

**Estimated Duration**: 5-10 seconds for 25-minute lecture

**Error Handling**:
- If validation fails: Notify frontend with error message
- If duration > 25 min: Return error "Lecture too long (max 25 min for 16K context)"
- If corrupt audio: Return error "Invalid audio file"

---

### Flow 2: Voice Q&A (Real-Time Streaming)

**User Action**: Student asks a question via voice recording

**Flow**:
```
Latency: <3 seconds to first audio chunk

1. User clicks "Ask Question" button
   - Frontend starts recording (MediaRecorder API)
   - Shows recording indicator with waveform animation
   ↓
2. User clicks "Stop Recording"
   - Frontend stops recording → gets Blob
   ↓
3. Frontend → WebSocket → "request_upload" (for query audio)
   {
     "type": "request_upload",
     "category": "query",
     "fileSize": 50000,
     "sessionId": "session-xyz",
     "lectureId": "lecture-uuid"
   }
   ↓
4. Lambda (WebSocketHandler) → Returns presigned URL for queries/ prefix
   ↓
5. Frontend uploads query audio to S3 (queries/{sessionId}/{timestamp}.webm)
   ↓
6. Frontend → WebSocket → "query"
   {
     "type": "query",
     "sessionId": "session-xyz",
     "lectureId": "lecture-uuid",
     "s3Key": "queries/session-xyz/query-1.webm",
     "connectionId": "abc123"
   }
   ↓
7. Lambda (WebSocketHandler) → HTTP POST to AgentCore on EC2
   ↓
8. AgentCore → QueryAgent (Strands)
   ↓
9. QueryAgent executes pipeline:

   Step 1: Load conversation history
   - Query DynamoDB Sessions table by sessionId
   - Retrieve last 10 Q&A pairs for context

   Step 2: Download and transcribe query
   - Download query audio from S3
   - Call vLLM: POST /v1/audio/transcriptions
     { "audio_file": "queries/session-xyz/query-1.webm" }
   - Response: { "text": "What is technical debt?" }
   - Send to frontend:
     {
       "type": "query_transcript",
       "text": "What is technical debt?"
     }

   Step 3: Generate answer with lecture context
   - Construct prompt:
     System: "Answer based on the lecture audio (lecture_id: {lectureId})"
     Context: [Last 3 Q&A pairs from DynamoDB history]
     User: "What is technical debt?"

   - Call vLLM: POST /v1/chat/completions
     {
       "model": "Qwen2.5-Omni-3B",
       "messages": [...],
       "lecture_id": "lecture-uuid",  // Reference loaded audio context
       "stream": false
     }
   - Response: { "text": "Technical debt refers to..." }

   - Send to frontend:
     {
       "type": "answer_text",
       "text": "Technical debt refers to..."
     }

   Step 4: Generate TTS audio
   - Call vLLM: POST /v1/audio/speech
     {
       "model": "Qwen2.5-Omni-3B",
       "input": "Technical debt refers to...",
       "voice": "Chelsie",
       "response_format": "wav",
       "sample_rate": 24000
     }
   - Response: Audio bytes (WAV format)

   Step 5: Stream audio chunks to frontend
   - Split audio into 4KB chunks
   - Base64 encode each chunk
   - Stream via WebSocket:
     {
       "type": "audio_chunk",
       "data": "UklGRiQAAABXQVZFZm10...",
       "sampleRate": 24000,
       "index": 0
     }
     {
       "type": "audio_chunk",
       "data": "...",
       "sampleRate": 24000,
       "index": 1
     }
     ...

   Step 6: End-of-stream signal
   - {
       "type": "audio_complete"
     }

   Step 7: Upload response audio to S3
   - Upload full audio to S3: responses/{sessionId}/{timestamp}.wav

   Step 8: Store Q&A metadata in memory (for later batch transcription)
   - Store in QueryAgent memory:
     {
       "sessionId": "session-xyz",
       "queryAudio": "queries/.../query-1.webm",
       "responseAudio": "responses/.../response-1.wav",
       "queryText": "What is technical debt?",
       "responseText": "Technical debt refers to...",
       "timestamp": "2025-01-20T10:35:00Z"
     }
   ↓
10. Frontend receives audio chunks
    - Decode base64 → ArrayBuffer
    - Play audio in real-time (Web Audio API or <audio> element)
    - Show animated waveform during playback
    ↓
11. User can ask follow-up questions (repeat steps 1-10)
    ↓
12. After **1 minute of inactivity** → Session automatically ends
    - Frontend timer resets on any user activity (recording, clicking)
    - On timeout: Frontend → WebSocket → "end_session"
      {
        "type": "end_session",
        "sessionId": "session-xyz"
      }
    ↓
13. Lambda → AgentCore → QueryAgent triggers batch transcription
    - Download all query + response audio files from S3
    - ASR each audio file (if not already transcribed)
    - Save complete conversation transcript to DynamoDB:
      {
        "sessionId": "session-xyz",
        "lectureId": "lecture-uuid",
        "conversation": [
          {
            "turn": 1,
            "queryText": "What is technical debt?",
            "responseText": "Technical debt refers to...",
            "timestamp": "2025-01-20T10:35:00Z"
          },
          ...
        ],
        "totalTurns": 5,
        "duration": 180,  // 3 minutes
        "createdAt": "2025-01-20T10:35:00Z",
        "expiresAt": 1737532500  // TTL: 7 days
      }
```

**Estimated Latency**:
- Time to first audio chunk: < 3 seconds
- Total response time: 5-10 seconds (depends on answer length)

---

## AgentCore + Strands Implementation

### Main AgentCore Application (Simplified)

```python
# app.py - Simplified AgentCore entrypoint
from bedrock_agentcore import BedrockAgentCoreApp
from agents.query_agent import QueryAgent
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = BedrockAgentCoreApp()

# Single agent only
query_agent = QueryAgent()

@app.entrypoint
def invoke(payload: dict) -> dict:
    """
    Simplified entrypoint - only handles queries
    Lecture uploads handled by S3 event → Lambda

    Args:
        payload: {
            "type": "query",
            "sessionId": str,
            "lectureId": str,
            "s3Key": str (query audio path)
        }

    Returns:
        Streaming response with query transcript, answer text, audio chunks
    """
    request_type = payload.get("type")

    logger.info(f"Received request: type={request_type}")

    try:
        if request_type == "query":
            return query_agent.process(payload)
        else:
            return {
                "error": f"Unknown request type: {request_type}",
                "supported_types": ["query"]
            }
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        return {
            "error": str(e),
            "type": "error"
        }

if __name__ == "__main__":
    # Local testing mode
    app.run()
```

---

### QueryAgent Implementation

```python
# agents/query_agent.py
from strands import Agent
import boto3
import requests
from typing import AsyncGenerator, Dict, List
import logging
from datetime import datetime, timedelta
import base64

logger = logging.getLogger(__name__)

class QueryAgent:
    """
    Strands Agent responsible for conversational Q&A.
    Handles: ASR, Q&A with lecture context, TTS streaming.
    """

    def __init__(self):
        self.agent = Agent()  # Strands agent
        self.s3 = boto3.client('s3')
        self.dynamodb = boto3.resource('dynamodb')
        self.vllm_endpoint = "http://localhost:8000"
        self.session_memory = {}  # In-memory storage for Q&A pairs

    async def process(self, payload: Dict) -> AsyncGenerator[Dict, None]:
        """
        Process Q&A query with streaming audio response

        Args:
            payload: {
                "sessionId": str,
                "lectureId": str,
                "s3Key": str (query audio path),
                "connectionId": str
            }

        Yields:
            Query text, answer text, audio chunks, completion signal
        """
        session_id = payload["sessionId"]
        lecture_id = payload["lectureId"]
        query_audio_path = payload["s3Key"]

        try:
            # Step 1: Load conversation history
            history = self._load_history(session_id, limit=10)

            # Step 2: Download and transcribe query
            query_audio = self._download_from_s3(query_audio_path)
            query_text = self._transcribe_audio(query_audio)

            yield {"type": "query_transcript", "text": query_text}

            # Step 3: Generate answer with lecture context
            answer_text = self._generate_answer(
                query_text,
                lecture_id,
                history
            )

            yield {"type": "answer_text", "text": answer_text}

            # Step 4: Generate TTS audio
            response_audio = self._text_to_speech(answer_text)

            # Step 5: Upload response audio to S3
            timestamp = int(datetime.now().timestamp() * 1000)
            response_s3_key = f"responses/{session_id}/{timestamp}.wav"
            self._upload_to_s3(response_audio, response_s3_key)

            # Step 6: Stream audio chunks to frontend
            async for chunk in self._stream_audio_chunks(response_audio):
                yield {
                    "type": "audio_chunk",
                    "data": chunk,
                    "sampleRate": 24000
                }

            yield {"type": "audio_complete"}

            # Step 7: Store Q&A in memory for later batch transcription
            self._store_qa_memory(
                session_id,
                query_audio_path,
                response_s3_key,
                query_text,
                answer_text
            )

        except Exception as e:
            logger.error(f"Q&A failed for session {session_id}: {str(e)}", exc_info=True)
            yield {
                "type": "error",
                "message": str(e)
            }

    def _load_history(self, session_id: str, limit: int = 10) -> List[Dict]:
        """Load recent conversation history from DynamoDB"""
        table = self.dynamodb.Table('SynapScribe-Sessions')

        try:
            response = table.get_item(Key={'sessionId': session_id})
            if 'Item' in response and 'conversation' in response['Item']:
                conversation = response['Item']['conversation']
                # Return last N turns
                return conversation[-limit:] if len(conversation) > limit else conversation
            return []
        except Exception as e:
            logger.warning(f"Failed to load history: {e}")
            return []

    def _transcribe_audio(self, audio_bytes: bytes) -> str:
        """Call vLLM for ASR"""
        response = requests.post(
            f"{self.vllm_endpoint}/v1/audio/transcriptions",
            files={"file": audio_bytes},
            data={"model": "Qwen2.5-Omni-3B"},
            timeout=30
        )
        response.raise_for_status()
        return response.json()["text"]

    def _generate_answer(self, query: str, lecture_id: str,
                        history: List[Dict]) -> str:
        """Generate answer using Strands agent with lecture context"""

        # Format conversation history (last 3 turns)
        history_text = ""
        if history:
            recent_history = history[-3:]
            history_text = "\n".join([
                f"Q: {turn.get('queryText', '')}\\nA: {turn.get('responseText', '')}"
                for turn in recent_history
            ])

        # Construct prompt
        prompt = f"""You are Qwen, a virtual human developed by the Qwen Team. You are a helpful AI learning assistant helping a student understand lecture content.

Answer the student's question based on the lecture audio you have in context (lecture_id: {lecture_id}).

{f'Previous conversation:\\n{history_text}\\n' if history_text else ''}

Student's question: {query}

Provide a clear, concise answer based on the lecture content. If the answer isn't in the lecture, say so honestly."""

        # Use Strands agent to generate response via vLLM
        result = self.agent(prompt, lecture_id=lecture_id)
        return result.message

    def _text_to_speech(self, text: str) -> bytes:
        """Call vLLM for TTS"""
        response = requests.post(
            f"{self.vllm_endpoint}/v1/audio/speech",
            json={
                "model": "Qwen2.5-Omni-3B",
                "input": text,
                "voice": "Chelsie",
                "response_format": "wav",
                "sample_rate": 24000
            },
            timeout=120
        )
        response.raise_for_status()
        return response.content

    async def _stream_audio_chunks(self, audio_data: bytes) -> AsyncGenerator[str, None]:
        """Stream audio in 4KB chunks (base64 encoded)"""
        chunk_size = 4096
        for i in range(0, len(audio_data), chunk_size):
            chunk = audio_data[i:i + chunk_size]
            if chunk:
                yield base64.b64encode(chunk).decode('utf-8')

    def _store_qa_memory(self, session_id: str, query_audio: str,
                        response_audio: str, query_text: str,
                        response_text: str):
        """Store Q&A pair in memory for later batch transcription"""
        if session_id not in self.session_memory:
            self.session_memory[session_id] = []

        self.session_memory[session_id].append({
            "queryAudio": query_audio,
            "responseAudio": response_audio,
            "queryText": query_text,
            "responseText": response_text,
            "timestamp": datetime.now().isoformat()
        })

    def end_session(self, session_id: str, lecture_id: str):
        """
        Called when session ends (1-minute inactivity)
        Saves conversation transcript to DynamoDB
        """
        if session_id not in self.session_memory:
            return

        conversation = self.session_memory[session_id]

        # Save to DynamoDB
        table = self.dynamodb.Table('SynapScribe-Sessions')

        # TTL: 7 days from now
        expires_at = int((datetime.now() + timedelta(days=7)).timestamp())

        table.put_item(
            Item={
                'sessionId': session_id,
                'lectureId': lecture_id,
                'conversation': conversation,
                'totalTurns': len(conversation),
                'createdAt': datetime.now().isoformat(),
                'expiresAt': expires_at
            }
        )

        # Clear memory
        del self.session_memory[session_id]

        logger.info(f"Session {session_id} ended and saved ({len(conversation)} turns)")

    def _download_from_s3(self, s3_path: str) -> bytes:
        """Download file from S3"""
        if s3_path.startswith('s3://'):
            s3_path = s3_path[5:]
        parts = s3_path.split('/', 1)
        bucket = parts[0]
        key = parts[1] if len(parts) > 1 else ''

        obj = self.s3.get_object(Bucket=bucket, Key=key)
        return obj['Body'].read()

    def _upload_to_s3(self, data: bytes, key: str):
        """Upload data to S3"""
        bucket = "synapscribe-audio"
        self.s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=data,
            ContentType='audio/wav'
        )
```

---

## Lambda Functions

### 1. WebSocketHandler (Connection Management + Routing)

```python
# lambda/websocket_handler.py
import json
import boto3
import os
from datetime import datetime
import uuid
import requests

s3_client = boto3.client('s3')
api_gateway = boto3.client('apigatewaymanagementapi')
dynamodb = boto3.resource('dynamodb')

AGENTCORE_ENDPOINT = os.environ['AGENTCORE_ENDPOINT']
S3_BUCKET = os.environ['S3_BUCKET']

def lambda_handler(event, context):
    """
    WebSocket handler for all routes
    """
    route_key = event['requestContext']['routeKey']
    connection_id = event['requestContext']['connectionId']

    if route_key == '$connect':
        return handle_connect(connection_id)

    elif route_key == '$disconnect':
        return handle_disconnect(connection_id)

    elif route_key == 'request_upload':
        body = json.loads(event['body'])
        return handle_request_upload(connection_id, body)

    elif route_key == 'query':
        body = json.loads(event['body'])
        return handle_query(connection_id, body)

    elif route_key == 'end_session':
        body = json.loads(event['body'])
        return handle_end_session(connection_id, body)

    else:
        return {'statusCode': 400, 'body': 'Unknown route'}

def handle_connect(connection_id):
    """Handle new WebSocket connection"""
    print(f"New connection: {connection_id}")
    return {'statusCode': 200, 'body': 'Connected'}

def handle_disconnect(connection_id):
    """Handle WebSocket disconnection"""
    print(f"Disconnected: {connection_id}")
    # TODO: Trigger session cleanup if needed
    return {'statusCode': 200, 'body': 'Disconnected'}

def handle_request_upload(connection_id, body):
    """
    Generate presigned URL for S3 upload

    Body: {
        "fileName": str,
        "fileSize": int,
        "duration": int (optional),
        "category": "lecture" | "query"
    }
    """
    file_name = body['fileName']
    file_size = body['fileSize']
    category = body.get('category', 'lecture')

    # Validate
    if file_size > 100 * 1024 * 1024:  # 100MB
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'File too large (max 100MB)'})
        }

    # Generate unique key
    file_id = str(uuid.uuid4())
    ext = file_name.split('.')[-1]

    if category == 'lecture':
        s3_key = f"lectures/{file_id}.{ext}"
        lecture_id = file_id
    else:  # query
        session_id = body.get('sessionId', 'default')
        s3_key = f"queries/{session_id}/{file_id}.{ext}"
        lecture_id = None

    # Generate presigned URL (valid for 15 minutes)
    presigned_url = s3_client.generate_presigned_url(
        'put_object',
        Params={
            'Bucket': S3_BUCKET,
            'Key': s3_key,
            'ContentType': f'audio/{ext}',
            'Metadata': {
                'connectionId': connection_id,
                'uploadedAt': datetime.now().isoformat()
            }
        },
        ExpiresIn=900
    )

    response = {
        'type': 'upload_url',
        'uploadUrl': presigned_url,
        's3Key': s3_key,
        'expiresIn': 900
    }

    if lecture_id:
        response['lectureId'] = lecture_id

    # Send response via WebSocket
    send_to_connection(connection_id, response)

    return {'statusCode': 200, 'body': 'OK'}

def handle_query(connection_id, body):
    """
    Route query to AgentCore

    Body: {
        "sessionId": str,
        "lectureId": str,
        "s3Key": str (query audio path)
    }
    """
    # Forward to AgentCore on EC2
    response = requests.post(
        f"{AGENTCORE_ENDPOINT}/invoke",
        json={
            'type': 'query',
            'sessionId': body['sessionId'],
            'lectureId': body['lectureId'],
            's3Key': body['s3Key'],
            'connectionId': connection_id
        },
        stream=True,  # Stream response
        timeout=120
    )

    # Stream AgentCore response back to frontend via WebSocket
    for line in response.iter_lines():
        if line:
            message = json.loads(line)
            send_to_connection(connection_id, message)

    return {'statusCode': 200, 'body': 'OK'}

def handle_end_session(connection_id, body):
    """
    Trigger session end and batch transcription

    Body: {
        "sessionId": str,
        "lectureId": str
    }
    """
    # Notify AgentCore to end session
    requests.post(
        f"{AGENTCORE_ENDPOINT}/end_session",
        json={
            'sessionId': body['sessionId'],
            'lectureId': body['lectureId']
        },
        timeout=30
    )

    send_to_connection(connection_id, {
        'type': 'session_ended',
        'message': 'Transcript saved to your history'
    })

    return {'statusCode': 200, 'body': 'OK'}

def send_to_connection(connection_id, message):
    """Send message to WebSocket connection"""
    endpoint_url = f"https://{os.environ['API_GATEWAY_ENDPOINT']}"
    api_gateway_client = boto3.client(
        'apigatewaymanagementapi',
        endpoint_url=endpoint_url
    )

    try:
        api_gateway_client.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(message).encode('utf-8')
        )
    except api_gateway_client.exceptions.GoneException:
        print(f"Connection {connection_id} is gone")
    except Exception as e:
        print(f"Error sending to {connection_id}: {e}")
```

---

### 2. ValidateLectureFunction (S3 Event-Triggered)

```python
# lambda/validate_lecture.py
import json
import boto3
import os
import tempfile
import librosa
import numpy as np
import requests
from datetime import datetime

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
api_gateway_client = None  # Initialized in handler

VLLM_ENDPOINT = os.environ['VLLM_ENDPOINT']
DYNAMODB_TABLE = os.environ['DYNAMODB_TABLE']
API_GATEWAY_ENDPOINT = os.environ['API_GATEWAY_ENDPOINT']

SUPPORTED_FORMATS = ['mp3', 'wav', 'm4a', 'mp4', 'ogg', 'flac', 'webm']
MAX_DURATION = 1500  # 25 minutes in seconds (16K context limit)
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

def lambda_handler(event, context):
    """
    Triggered automatically by S3 PutObject event

    Event structure:
    {
        "Records": [{
            "s3": {
                "bucket": {"name": "..."},
                "object": {"key": "lectures/uuid.mp3", "size": 50000000}
            }
        }]
    }
    """
    global api_gateway_client
    api_gateway_client = boto3.client(
        'apigatewaymanagementapi',
        endpoint_url=f"https://{API_GATEWAY_ENDPOINT}"
    )

    # Parse S3 event
    record = event['Records'][0]
    bucket = record['s3']['bucket']['name']
    s3_key = record['s3']['object']['key']
    file_size = record['s3']['object']['size']

    # Extract lectureId from key (lectures/{lectureId}.ext)
    lecture_id = s3_key.split('/')[1].split('.')[0]

    print(f"Processing lecture: {lecture_id} ({file_size} bytes)")

    try:
        # Get metadata (includes connectionId for notification)
        obj_metadata = s3_client.head_object(Bucket=bucket, Key=s3_key)
        connection_id = obj_metadata['Metadata'].get('connectionId')

        # Step 1: Validate file size
        if file_size > MAX_FILE_SIZE:
            raise ValueError(f"File too large: {file_size/1024/1024:.2f}MB (max: 100MB)")

        # Step 2: Validate format
        ext = s3_key.split('.')[-1].lower()
        if ext not in SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported format: {ext}")

        # Step 3: Download and validate audio integrity
        audio_data, metadata = validate_audio_integrity(bucket, s3_key, ext)
        duration = metadata['duration']

        # Step 4: Validate duration
        if duration > MAX_DURATION:
            raise ValueError(
                f"Lecture too long: {duration/60:.2f} minutes (max: 25 minutes for 16K context)"
            )

        # Step 5: Load audio into Qwen2.5-Omni context
        tokens_used = load_audio_context(bucket, s3_key, lecture_id)

        # Step 6: Save metadata to DynamoDB
        save_lecture_metadata(lecture_id, s3_key, duration, tokens_used)

        # Step 7: Notify frontend via WebSocket
        if connection_id:
            notify_frontend(connection_id, {
                'type': 'lecture_ready',
                'lectureId': lecture_id,
                'message': 'Lecture loaded! Ready for questions.',
                'duration': duration,
                'tokensUsed': tokens_used
            })

        print(f"Lecture {lecture_id} processed successfully")
        return {'statusCode': 200, 'body': 'Success'}

    except Exception as e:
        error_msg = str(e)
        print(f"Error processing lecture {lecture_id}: {error_msg}")

        # Notify frontend of error
        if connection_id:
            notify_frontend(connection_id, {
                'type': 'lecture_error',
                'lectureId': lecture_id,
                'error': error_msg
            })

        # Save error status to DynamoDB
        save_lecture_metadata(
            lecture_id,
            s3_key,
            duration=0,
            tokens_used=0,
            status='failed',
            error=error_msg
        )

        return {'statusCode': 500, 'body': error_msg}

def validate_audio_integrity(bucket, s3_key, ext):
    """
    Download audio and validate integrity
    Returns: (audio_data, metadata)
    """
    # Download to temp file
    with tempfile.NamedTemporaryFile(suffix=f'.{ext}', delete=False) as tmp:
        s3_client.download_fileobj(bucket, s3_key, tmp)
        tmp_path = tmp.name

    try:
        # Load with librosa
        audio_data, sample_rate = librosa.load(tmp_path, sr=None)
        duration = len(audio_data) / sample_rate

        # Check if audio is silent/corrupted
        if np.max(np.abs(audio_data)) < 0.001:
            raise ValueError("Audio appears to be silent or corrupted")

        # Check sample rate
        if sample_rate < 8000:
            raise ValueError(f"Sample rate too low: {sample_rate}Hz (min: 8000Hz)")

        metadata = {
            'duration': duration,
            'sample_rate': sample_rate,
            'format': ext
        }

        return audio_data, metadata

    finally:
        # Clean up temp file
        os.unlink(tmp_path)

def load_audio_context(bucket, s3_key, lecture_id):
    """
    Load audio into Qwen2.5-Omni 16K context via vLLM
    Returns: tokens_used
    """
    response = requests.post(
        f"{VLLM_ENDPOINT}/v1/audio/context",
        json={
            'audio_file_s3': f's3://{bucket}/{s3_key}',
            'lecture_id': lecture_id,
            'max_context_tokens': 16384
        },
        timeout=60
    )
    response.raise_for_status()

    result = response.json()
    return result.get('tokens_used', 0)

def save_lecture_metadata(lecture_id, s3_key, duration, tokens_used,
                         status='ready', error=None):
    """Save lecture metadata to DynamoDB"""
    table = dynamodb.Table(DYNAMODB_TABLE)

    item = {
        'lectureId': lecture_id,
        's3Key': s3_key,
        'duration': int(duration),
        'tokensUsed': int(tokens_used),
        'status': status,
        'createdAt': datetime.now().isoformat()
    }

    if error:
        item['errorMessage'] = error

    table.put_item(Item=item)

def notify_frontend(connection_id, message):
    """Send message to frontend via API Gateway WebSocket"""
    try:
        api_gateway_client.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(message).encode('utf-8')
        )
        print(f"Notified connection {connection_id}: {message['type']}")
    except api_gateway_client.exceptions.GoneException:
        print(f"Connection {connection_id} is gone")
    except Exception as e:
        print(f"Error notifying {connection_id}: {e}")
```

---

## Error Handling & Resilience

### Retry Mechanism

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import requests

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((requests.Timeout, requests.ConnectionError))
)
def call_vllm_with_retry(endpoint: str, **kwargs):
    """Retry vLLM calls with exponential backoff"""
    return requests.post(endpoint, **kwargs)
```

### Circuit Breaker

```python
from pybreaker import CircuitBreaker

vllm_breaker = CircuitBreaker(
    fail_max=5,
    timeout_duration=60,
    name="vllm_circuit"
)

@vllm_breaker
def call_vllm_protected(endpoint: str, **kwargs):
    """Call vLLM with circuit breaker protection"""
    return requests.post(endpoint, **kwargs)
```

### Audio Validation

```python
import librosa
import numpy as np

SUPPORTED_FORMATS = ['mp3', 'wav', 'm4a', 'mp4', 'ogg', 'flac', 'webm']
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_DURATION = 1500  # 25 minutes (16K context limit)

class AudioValidationError(Exception):
    pass

def validate_audio(file_path: str, file_size: int) -> dict:
    """
    Comprehensive audio validation

    Returns: {
        "valid": bool,
        "error": str | None,
        "metadata": dict
    }
    """
    # Check format
    ext = file_path.split('.')[-1].lower()
    if ext not in SUPPORTED_FORMATS:
        return {
            "valid": False,
            "error": f"Unsupported format: {ext}. Supported: {', '.join(SUPPORTED_FORMATS)}"
        }

    # Check size
    if file_size > MAX_FILE_SIZE:
        return {
            "valid": False,
            "error": f"File too large: {file_size/1024/1024:.2f}MB (max: 50MB)"
        }

    # Check audio integrity and duration
    try:
        audio_data, sample_rate = librosa.load(file_path, sr=None)
        duration = len(audio_data) / sample_rate

        if duration > MAX_DURATION:
            return {
                "valid": False,
                "error": f"Audio too long: {duration/60:.2f} minutes (max: 25 minutes for 16K context)"
            }

        # Check if audio is silent/corrupted
        if np.max(np.abs(audio_data)) < 0.001:
            return {
                "valid": False,
                "error": "Audio appears to be silent or corrupted"
            }

        # Check sample rate
        if sample_rate < 8000:
            return {
                "valid": False,
                "error": f"Sample rate too low: {sample_rate}Hz (min: 8000Hz)"
            }

        return {
            "valid": True,
            "error": None,
            "metadata": {
                "duration": duration,
                "sample_rate": sample_rate,
                "format": ext
            }
        }

    except Exception as e:
        return {
            "valid": False,
            "error": f"Failed to load audio: {str(e)}"
        }
```

---

## DynamoDB Schema

### Sessions Table (Simplified - Stores Everything)

```python
{
    'TableName': 'SynapScribe-Sessions',
    'KeySchema': [
        {'AttributeName': 'sessionId', 'KeyType': 'HASH'}
    ],
    'AttributeDefinitions': [
        {'AttributeName': 'sessionId', 'AttributeType': 'S'}
    ],
    'BillingMode': 'PAY_PER_REQUEST',
    'TimeToLiveSpecification': {
        'Enabled': True,
        'AttributeName': 'expiresAt'
    }
}
```

**Item Structure (Session + Conversation):**
```json
{
  "sessionId": "session-abc123",
  "lectureId": "lecture-xyz789",
  "conversation": [
    {
      "turn": 1,
      "queryText": "What is technical debt?",
      "responseText": "Technical debt refers to...",
      "queryAudio": "s3://bucket/queries/session-abc123/query-1.webm",
      "responseAudio": "s3://bucket/responses/session-abc123/response-1.wav",
      "timestamp": "2025-01-20T10:35:00Z"
    },
    {
      "turn": 2,
      "queryText": "Can you give an example?",
      "responseText": "Sure! For example...",
      "queryAudio": "s3://bucket/queries/session-abc123/query-2.webm",
      "responseAudio": "s3://bucket/responses/session-abc123/response-2.wav",
      "timestamp": "2025-01-20T10:36:30Z"
    }
  ],
  "totalTurns": 2,
  "duration": 90,
  "createdAt": "2025-01-20T10:35:00Z",
  "expiresAt": 1737532500
}
```

**Item Structure (Lecture Metadata):**
```json
{
  "lectureId": "lecture-xyz789",
  "s3Key": "lectures/lecture-xyz789.mp3",
  "duration": 2850,
  "tokensUsed": 28453,
  "status": "ready",
  "createdAt": "2025-01-20T10:30:00Z",
  "expiresAt": 1737532500
}
```

**Note:** Using single table design with different partition key patterns:
- Sessions: `sessionId = "session-{uuid}"`
- Lectures: `lectureId = "lecture-{uuid}"`

**TTL**: 7 days auto-cleanup

---

## Implementation Phases

### Phase 0: Model Validation (3-5 days)

**Objective**: Validate Qwen2.5-Omni-3B on EC2 and test audio context loading

**Tasks**:

1. **Launch EC2 g5.2xlarge (Spot instance for cost savings)**
   ```bash
   aws ec2 run-instances \
     --image-id ami-0c55b159cbfafe1f0 \
     --instance-type g5.2xlarge \
     --instance-market-options '{"MarketType":"spot","SpotOptions":{"SpotInstanceType":"persistent"}}' \
     --key-name synapscribe-key \
     --security-group-ids sg-xxxxx \
     --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":150,"VolumeType":"gp3"}}]'
   ```

2. **Install dependencies**
   ```bash
   ssh -i synapscribe-key.pem ubuntu@<ec2-ip>

   sudo apt-get update && sudo apt-get install -y \
     python3.11 python3-pip ffmpeg nvidia-driver-535 cuda-toolkit-12-2

   pip install vllm>=0.8.5 transformers>=4.51.3 torch boto3 librosa soundfile
   ```

3. **Download Qwen2.5-Omni-3B (single model only)**
   ```bash
   huggingface-cli download Qwen/Qwen2.5-Omni-3B \
     --local-dir /opt/models/qwen-omni
   ```

4. **Start vLLM server (16K context optimized)**
   ```bash
   vllm serve /opt/models/qwen-omni \
     --host 0.0.0.0 \
     --port 8000 \
     --dtype bfloat16 \
     --max-model-len 16384 \
     --trust-remote-code \
     --gpu-memory-utilization 0.85 \
     > /var/log/vllm.log 2>&1 &
   ```

5. **Create validation notebook**
   ```python
   # test_qwen_audio_context.ipynb

   # CRITICAL TEST: Can Qwen2.5-Omni load audio as persistent context?
   import requests

   # Test 1: Load 25-minute lecture audio (16K context)
   with open('lecture_25min.mp3', 'rb') as f:
       response = requests.post(
           'http://localhost:8000/v1/audio/context',
           files={'file': f},
           data={'lecture_id': 'test-123', 'max_tokens': 16384}
       )

   print(response.json())  # Expected: {"status": "loaded", "tokens_used": ~14000}

   # Test 2: Query with audio context
   response = requests.post(
       'http://localhost:8000/v1/chat/completions',
       json={
           'model': 'Qwen2.5-Omni-3B',
           'messages': [
               {
                   'role': 'system',
                   'content': 'Answer based on lecture audio (lecture_id: test-123)'
               },
               {'role': 'user', 'content': 'Summarize the main points'}
           ],
           'lecture_id': 'test-123'
       }
   )

   print(response.json())

   # Test 3: ASR
   # Test 4: TTS
   # Test 5: GPU memory usage
   ```

6. **Benchmark tests**
   - ASR: 30-second, 5-minute, 20-minute audio
   - Audio context: 10-min, 20-min, 25-min lectures (16K context limit)
   - TTS: Short (1 sentence), medium (1 paragraph), long (500 words)
   - GPU memory: Peak usage during each operation

**Deliverables**:
- ✅ Validation notebook with test results
- ✅ Performance benchmarks (latency, throughput)
- ✅ GPU memory usage report
- ✅ **CRITICAL: Confirm audio context loading works** (if not, fallback to ASR upfront)

**Decision Point**: If Qwen2.5-Omni **cannot** load raw audio as persistent context:
- **Fallback Plan**: ASR lecture upfront → Store transcript in DynamoDB → Use text context (still no embeddings for ≤25min lectures in 16K context)

---

### Phase 1: Core Infrastructure (✅ COMPLETE - 2025-12-03)

**Objective**: Deploy AWS infrastructure with IaC

**Status**: Successfully deployed on December 3, 2025 using AWS SAM. All infrastructure components are operational and ready for Phase 2 integration. See `PHASE1_REPORT.md` for detailed deployment information.

**Tasks**:

1. **Create SAM template** (template.yaml)

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Description: SynapScribe Simplified MVP

Globals:
  Function:
    Runtime: python3.11
    Timeout: 60
    MemorySize: 512
    Environment:
      Variables:
        S3_BUCKET: !Ref AudioBucket
        DYNAMODB_TABLE: !Ref SessionsTable
        VLLM_ENDPOINT: !Sub 'http://${EC2PrivateIP}:8000'

Resources:
  # Cognito Identity Pool (Unauthenticated)
  IdentityPool:
    Type: AWS::Cognito::IdentityPool
    Properties:
      AllowUnauthenticatedIdentities: true
      IdentityPoolName: synapscribe-identities

  # IAM Role for unauthenticated users
  UnauthRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Statement:
          - Effect: Allow
            Principal:
              Federated: cognito-identity.amazonaws.com
            Action: sts:AssumeRoleWithWebIdentity
            Condition:
              StringEquals:
                cognito-identity.amazonaws.com:aud: !Ref IdentityPool
      Policies:
        - PolicyName: UnauthPolicy
          PolicyDocument:
            Statement:
              - Effect: Allow
                Action: s3:PutObject
                Resource: !Sub '${AudioBucket.Arn}/uploads/*'
              - Effect: Allow
                Action: execute-api:Invoke
                Resource: !Sub 'arn:aws:execute-api:${AWS::Region}:${AWS::AccountId}:${WebSocketApi}/*'

  # S3 Bucket
  AudioBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: synapscribe-audio
      NotificationConfiguration:
        LambdaConfigurations:
          - Event: s3:ObjectCreated:*
            Function: !GetAtt ValidateLectureFunction.Arn
            Filter:
              S3Key:
                Rules:
                  - Name: prefix
                    Value: lectures/
      LifecycleConfiguration:
        Rules:
          - Id: DeleteQueriesAfter7Days
            Status: Enabled
            Prefix: queries/
            ExpirationInDays: 7
          - Id: DeleteResponsesAfter7Days
            Status: Enabled
            Prefix: responses/
            ExpirationInDays: 7

  # DynamoDB Sessions Table
  SessionsTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: SynapScribe-Sessions
      AttributeDefinitions:
        - AttributeName: sessionId
          AttributeType: S
      KeySchema:
        - AttributeName: sessionId
          KeyType: HASH
      BillingMode: PAY_PER_REQUEST
      TimeToLiveSpecification:
        Enabled: true
        AttributeName: expiresAt

  # WebSocket API Gateway
  WebSocketApi:
    Type: AWS::ApiGatewayV2::Api
    Properties:
      Name: SynapScribeWebSocket
      ProtocolType: WEBSOCKET
      RouteSelectionExpression: $request.body.type

  # Lambda: WebSocketHandler
  WebSocketHandler:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: lambda/websocket_handler/
      Handler: websocket_handler.lambda_handler
      Policies:
        - S3CrudPolicy:
            BucketName: !Ref AudioBucket
        - DynamoDBCrudPolicy:
            TableName: !Ref SessionsTable
        - Statement:
            - Effect: Allow
              Action: execute-api:ManageConnections
              Resource: !Sub 'arn:aws:execute-api:${AWS::Region}:${AWS::AccountId}:${WebSocketApi}/*'

  # Lambda: ValidateLectureFunction
  ValidateLectureFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: lambda/validate_lecture/
      Handler: validate_lecture.lambda_handler
      Timeout: 120
      MemorySize: 1024
      Policies:
        - S3ReadPolicy:
            BucketName: !Ref AudioBucket
        - DynamoDBCrudPolicy:
            TableName: !Ref SessionsTable
        - Statement:
            - Effect: Allow
              Action: execute-api:ManageConnections
              Resource: !Sub 'arn:aws:execute-api:${AWS::Region}:${AWS::AccountId}:${WebSocketApi}/*'

  # Grant S3 permission to invoke Lambda
  ValidateLectureFunctionPermission:
    Type: AWS::Lambda::Permission
    Properties:
      FunctionName: !Ref ValidateLectureFunction
      Action: lambda:InvokeFunction
      Principal: s3.amazonaws.com
      SourceArn: !GetAtt AudioBucket.Arn

Outputs:
  WebSocketApiEndpoint:
    Value: !GetAtt WebSocketApi.ApiEndpoint
  AudioBucketName:
    Value: !Ref AudioBucket
  SessionsTableName:
    Value: !Ref SessionsTable
```

2. **Deploy infrastructure**
   ```bash
   sam build
   sam deploy --guided
   ```

3. **EC2 Setup**
   - Ensure vLLM is running from Phase 0
   - Configure security groups (allow Lambda VPC to call EC2)
   - Set up systemd service for vLLM auto-start

**Deliverables**: ✅ ALL COMPLETE
- ✅ Complete AWS infrastructure deployed (WebSocket API, Lambda, S3, DynamoDB, Cognito)
- ✅ vLLM endpoint running and accessible from Lambda (http://172.31.36.1:8000)
- ✅ gTTS service running and accessible (http://172.31.36.1:8001)
- ✅ S3 event trigger configured (lectures/ → ValidateLectureFunction)
- ✅ Infrastructure-as-Code templates (SAM template.yaml)
- ✅ All integration tests passed

**Deployed Resources**:
- WebSocket API: `wss://1h29nttho0.execute-api.us-east-1.amazonaws.com/Prod`
- S3 Bucket: `synapscribe-audio-657177702657`
- DynamoDB Table: `SynapScribe-Sessions`
- Cognito Identity Pool: `us-east-1:43e8b60d-1251-4cb7-8fc0-3deeed0f7244`
- Lambda Functions: WebSocketHandler, ValidateLectureFunction

**Next**: Proceed to Phase 2 (AgentCore + QueryAgent implementation)

---

### Phase 2: AgentCore + QueryAgent ✅ COMPLETE (December 4, 2025)

**Objective**: Build and deploy AgentCore with single QueryAgent

**Status**: All backend services (vLLM, gTTS, AgentCore) operational and configured for automatic startup. See `PHASE2_REPORT.md` for complete details.

**Tasks**:

1. **Install frameworks on EC2**
   ```bash
   pip install bedrock-agentcore strands-agents boto3 requests tenacity pybreaker
   ```

2. **Build AgentCore app** (app.py) - See implementation above

3. **Implement QueryAgent** - See implementation above

4. **Deploy AgentCore to EC2**
   ```bash
   agentcore configure -e app.py
   agentcore launch --region us-east-1
   ```

5. **Integration testing**
   - Test lecture upload → S3 event → Lambda validation
   - Test Q&A with sample queries
   - Verify audio streaming works end-to-end
   - Test 1-minute inactivity timeout
   - Load test with 10 concurrent users

**Deliverables**:
- ✅ Working AgentCore deployment on EC2
- ✅ QueryAgent implemented and tested
- ✅ Unit and integration tests passing
- ✅ Load test results

---

### Phase 3: Frontend (1 week)

**Objective**: Build React frontend with audio upload and voice recording

**Tasks**:

1. **React app setup**
   ```bash
   npm create vite@latest synapscribe-frontend -- --template react-ts
   cd synapscribe-frontend
   npm install aws-amplify
   ```

2. **Configure Cognito Identity Pool (no auth UI)**
   ```typescript
   // src/config/amplify.ts
   import { Amplify } from 'aws-amplify';

   Amplify.configure({
     Auth: {
       identityPoolId: 'us-east-1:xxxxx',
       region: 'us-east-1',
       allowGuestAccess: true  // No login required
     }
   });
   ```

3. **Core components**
   - `LectureUpload.tsx` - File upload with progress
   - `VoiceRecorder.tsx` - MediaRecorder API
   - `ConversationView.tsx` - Q&A display with waveforms
   - `AudioPlayer.tsx` - Streaming audio playback
   - `WebSocketClient.ts` - WebSocket connection manager
   - `useSessionTimeout.ts` - 1-minute inactivity hook

4. **Deploy to S3 + CloudFront**
   ```bash
   npm run build
   aws s3 mb s3://synapscribe-frontend
   aws s3 sync dist/ s3://synapscribe-frontend/
   ```

**Deliverables**:
- ✅ Working React frontend
- ✅ Deployed to CloudFront
- ✅ Audio upload and recording functional
- ✅ WebSocket streaming working

---

### Phase 4: Integration & Testing (3-5 days)

**Objective**: End-to-end testing and optimization

**Tasks**:

1. **End-to-end testing**
   - Upload 30-minute lecture → verify ready for Q&A
   - Ask 10 sample questions → verify relevant answers
   - Test all audio formats (mp3, wav, m4a, webm)
   - Test 1-minute inactivity → verify session ends

2. **Error scenario testing**
   - Large files (>100MB) - should reject
   - Long lectures (>50 min) - should reject
   - Corrupt audio files
   - Network interruptions
   - vLLM server unavailable

3. **Performance testing**
   - Lecture upload latency
   - Q&A latency (time to first audio chunk)
   - Concurrent users (10, 20, 50)
   - GPU utilization during load

**Deliverables**:
- ✅ All tests passing
- ✅ Performance benchmarks documented
- ✅ Known issues list
- ✅ Production-ready MVP

---

### Phase 5: Observability & Documentation (2-3 days)

**Objective**: Add monitoring and create documentation

**Tasks**:

1. **CloudWatch Dashboards**
   - API Gateway metrics
   - Lambda invocations, duration, errors
   - vLLM inference latency
   - GPU utilization
   - DynamoDB read/write capacity
   - S3 storage size

2. **CloudWatch Alarms**
   - High error rate (>5%)
   - High latency (>10s for Q&A)
   - GPU memory exhaustion
   - Lambda timeout rate

3. **Documentation**
   - Architecture diagram
   - API documentation (WebSocket messages)
   - Deployment guide
   - User guide
   - Troubleshooting runbook

**Deliverables**:
- ✅ CloudWatch dashboards configured
- ✅ Alarms set up
- ✅ Complete documentation

---

## Cost Estimates

### Monthly AWS Costs (Simplified MVP)

| Service | Configuration | Cost/Month |
|---------|--------------|------------|
| **EC2 g5.2xlarge** | Spot instance, 24/7 | **$330** |
| **Lambda** | 2 functions, 100K invocations | **$5** |
| **S3** | 100GB storage | **$3** |
| **API Gateway WebSocket** | 1M messages | **$5** |
| **DynamoDB** | Sessions table (on-demand) | **$5** |
| **CloudFront** | Frontend CDN | **$2** |
| **Cognito Identity Pool** | Unauthenticated (free tier) | **$0** |
| **Data Transfer** | Moderate usage | **$10** |
| **CloudWatch** | Logs + metrics | **$5** |

**Total Monthly Cost: ~$365**

**Cost Savings vs Original Plan:**
- Original plan (v2.0): $1,071/month
- Simplified plan (v3.0): $365/month
- **Savings: $706/month (66% reduction)**

**Removed costs:**
- OpenSearch Serverless: -$700/month
- Qwen3-Embedding-8B: -$0 (saves GPU memory)
- IngestionAgent complexity: -$20/month

### Per-User Cost (100 Active Users)

Assuming 100 users/month:
- 500 lecture uploads (30 min avg)
- 5,000 Q&A queries

**Additional variable costs**:
- S3 storage: ~50GB → +$1
- DynamoDB: ~5M read/write units → +$5
- API Gateway: ~5M messages → +$25
- Lambda: ~500K invocations → +$10

**Total: ~$405/month for 100 users = $4.05/user/month**

---

## Success Criteria

### Phase 0 (Model Validation) - COMPLETED December 2-3, 2025

**ASR Performance (vLLM via prompting):**
- ✅ ASR via vLLM prompting: ~2s for 30s audio (VALIDATED: exceeds <3s target)
- ✅ Method: `/v1/chat/completions` with transcription prompt
- ✅ Quality: Coherent, properly punctuated transcriptions
- ✅ No separate ASR endpoint needed (architectural simplification)

**Audio Context & Q&A:**
- ✅ Audio context persistence across turns (VALIDATED)
- ✅ Q&A with audio context: <3s response time (VALIDATED: meets <3s target)
- ✅ 25-minute lectures fit in 16K context window (optimized for 2x performance)

**TTS Performance:**
- 🎯 TTS via gTTS: <2s for short text (TO BE VALIDATED in final deployment)
- ✅ Architecture Decision: Use gTTS due to vLLM API limitation
- ✅ Lightweight, production-ready solution

**Architecture Simplifications:**
- ✅ Eliminated separate ASR endpoint (use vLLM prompting)
- ✅ Removed Whisper dependency
- ✅ Resolved transformers version conflicts
- ✅ Simplified TTS service (gTTS only, no heavy dependencies)

**Infrastructure:**
- ✅ No dependency conflicts (removed problematic transformers preview)
- ✅ GPU memory usage optimized
- ✅ End-to-end audio Q&A workflow validated

**See:** `docs/QWEN_INVESTIGATION_FINDINGS.md` for complete Phase 0 investigation details

### Full MVP

**Functional Requirements**:
- ✅ User uploads 30-min lecture → ready for Q&A in <10 seconds
- ✅ User asks question → gets audio answer in <5 seconds
- ✅ Conversation feels natural (real-time audio streaming)
- ✅ 1-minute inactivity triggers session end
- ✅ Transcripts saved to DynamoDB after session
- ✅ All audio formats supported (mp3, wav, m4a, webm)

**Performance Requirements**:
- ✅ Lecture validation: < 5 seconds
- ✅ ASR latency: < 2 seconds for 30-second query
- ✅ Q&A generation: < 3 seconds
- ✅ TTS latency: < 3 seconds for 200-word answer
- ✅ End-to-end Q&A: < 8 seconds total
- ✅ System handles 10 concurrent users without degradation

**Quality Requirements**:
- ✅ ASR accuracy: < 5% WER on clear audio
- ✅ Q&A relevance: Answers based on lecture content
- ✅ TTS quality: Natural-sounding, intelligible speech
- ✅ Error rate: < 1% system errors
- ✅ Uptime: > 99% during testing

**Usability Requirements**:
- ✅ Clean, minimalistic UI with voice animations
- ✅ Clear error messages for validation failures
- ✅ Intuitive upload and recording flow
- ✅ Mobile-responsive design

---

## Next Steps

### Immediate Actions (Phase 0)

1. ✅ **Review and approve this plan**
2. **Launch EC2 g5.2xlarge Spot instance**
3. **Install vLLM and download Qwen2.5-Omni-3B**
4. **Create validation notebook** - Test audio context loading
5. **Benchmark performance** - ASR, TTS, Q&A latency
6. **Measure GPU memory** - Ensure < 22GB
7. **Document findings** - Go/No-Go decision

### After Phase 0 Validation

- **If audio context works**: Proceed with Phases 1-5
- **If audio context doesn't work**: Implement fallback (ASR upfront + text context)

---

**End of Simplified MVP Plan v3.0**

*This plan prioritizes maximum simplicity, serverless automation, and rapid iteration with 1-minute session timeouts for fast MVP testing.*
