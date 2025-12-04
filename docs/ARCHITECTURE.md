# SynapScribe Architecture

**Version:** 3.3 (Phase 2 Deployed)
**Date:** December 4, 2025
**Purpose:** Concise technical architecture for voice-to-voice learning assistant

**Latest Update:** Phase 2 backend services deployed successfully on December 4, 2025. All three core services (vLLM, gTTS, AgentCore) are operational on EC2 with automatic startup configured. System ready for Phase 3 (React Frontend) development. See `PHASE2_REPORT.md` for complete details.

**Deployment Status:**
- ✅ Phase 0: Model validation (December 3, 2025)
- ✅ Phase 1: AWS infrastructure (December 3, 2025)
- ✅ Phase 2: Backend services - vLLM, gTTS, AgentCore (December 4, 2025)
- ⏳ Phase 3: Frontend React app
- ⏳ Phase 4: End-to-end testing
- ⏳ Phase 5: Production hardening

---

## Overview

SynapScribe enables real-time voice-to-voice Q&A on uploaded lecture audio using a radically simplified serverless architecture with event-driven processing and a single AI model.

**Core Flows:**
1. **Lecture Upload** → S3 event triggers automatic validation and context loading (5-10 seconds, ≤25 min lectures)
2. **Voice Q&A** → Real-time conversational questions and audio streaming responses (<3 seconds)

---

## Architecture Diagram (Layered View)

```
┌─────────────────────────────────────────────────────────────────┐
│  USER LAYER                                                      │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ User Browser (React + TypeScript)                          │ │
│  │ • No login UI (auto guest credentials via Cognito)         │ │
│  │ • File upload for lecture audio (≤25 min limit)            │ │
│  │ • Voice recorder (MediaRecorder API)                       │ │
│  │ • Audio playback with waveform animations                  │ │
│  │ • WebSocket client (persistent connection)                 │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────┬───────────────────────────────────┘
                              │ wss:// (WebSocket + JWT-like token)
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  AWS CLOUD                                                       │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ FRONTEND LAYER (Optional - for serving static React app)   │ │
│  │                                                              │ │
│  │  CloudFront (CDN) → S3 Bucket (synapscribe-frontend)       │ │
│  │  • Static website hosting for React build                   │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ AUTHENTICATION LAYER                                        │ │
│  │                                                              │ │
│  │  Amazon Cognito Identity Pool                               │ │
│  │  • Unauthenticated access enabled                           │ │
│  │  • Auto-generates temporary AWS credentials                 │ │
│  │  • No User Pools needed (no login UI)                       │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ API LAYER                                                   │ │
│  │                                                              │ │
│  │  ┌──────────────────────────────────────────────────────┐  │ │
│  │  │ WebSocket API Gateway                                 │  │ │
│  │  │ • Cognito Identity Pool authorizer                    │  │ │
│  │  │ • Routes: $connect, request_upload, query, end_session│  │ │
│  │  └──────────┬───────────────────────────────────────────┘  │ │
│  │             │                                                │ │
│  │  ┌──────────────────────────────────────────────────────┐  │ │
│  │  │ Lambda (WebSocketHandler)                             │  │ │
│  │  │ • Connection management                               │  │ │
│  │  │ • Generate presigned URLs for S3 uploads              │  │ │
│  │  │ • Route query messages to AgentCore                   │  │ │
│  │  └──────────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ PROCESSING LAYER                                            │ │
│  │                                                              │ │
│  │  ┌──────────────────────────────────────────────────────┐  │ │
│  │  │ Lambda (ValidateLectureFunction)                      │  │ │
│  │  │ • Triggered by S3 PutObject event (lectures/*)        │  │ │
│  │  │ • Validates: duration (≤25min), format, integrity     │  │ │
│  │  │ • Loads audio into Qwen 16K context via HTTP          │  │ │
│  │  │ • Saves metadata to DynamoDB                          │  │ │
│  │  │ • Notifies frontend via WebSocket                     │  │ │
│  │  └──────────────────────────────────────────────────────┘  │ │
│  │                          │ HTTP POST                         │ │
│  │  ┌────────────────────────────────────────────────────────┐│ │
│  │  │ COMPUTE LAYER (EC2 g5.2xlarge - 24GB VRAM)            ││ │
│  │  │                                                         ││ │
│  │  │  ┌────────────────────────────────────────────────┐   ││ │
│  │  │  │ Amazon Bedrock AgentCore                       │   ││ │
│  │  │  │ (Serverless Runtime)                           │   ││ │
│  │  │  │  • QueryAgent (Strands) - ONLY AGENT           │   ││ │
│  │  │  │    Handles ASR (vLLM prompting) → Q&A → TTS    │   ││ │
│  │  │  │    ASR: vLLM /v1/chat/completions (~2s)        │   ││ │
│  │  │  │    Q&A: vLLM with audio context (<3s)          │   ││ │
│  │  │  │    TTS: gTTS service                           │   ││ │
│  │  │  └────────────────────────────────────────────────┘   ││ │
│  │  │                                                         ││ │
│  │  │  ┌────────────────────────────────────────────────┐   ││ │
│  │  │  │ vLLM Inference Server (port 8000)              │   ││ │
│  │  │  │  • Qwen2.5-Omni-3B - SINGLE MODEL              │   ││ │
│  │  │  │    - ASR via prompt engineering (~2s)          │   ││ │
│  │  │  │    - Audio Context (16K context window)        │   ││ │
│  │  │  │    - Chat Completion (Q&A)                     │   ││ │
│  │  │  │  • Config: --max-model-len 16384               │   ││ │
│  │  │  │  • GPU Utilization: 85%                        │   ││ │
│  │  │  └────────────────────────────────────────────────┘   ││ │
│  │  │                                                         ││ │
│  │  │  ┌────────────────────────────────────────────────┐   ││ │
│  │  │  │ TTS Service (port 8001)                        │   ││ │
│  │  │  │  • gTTS (Google Text-to-Speech)                │   ││ │
│  │  │  │    - Text → Audio (MP3)                        │   ││ │
│  │  │  │    - Lightweight, no model downloads           │   ││ │
│  │  │  │    - OpenAI-compatible API                     │   ││ │
│  │  │  │                                                 │   ││ │
│  │  │  │  Note: Qwen2.5-Omni CAN generate audio but     │   ││ │
│  │  │  │  vLLM API doesn't expose it (API limitation)   │   ││ │
│  │  │  └────────────────────────────────────────────────┘   ││ │
│  │  └────────────────────────────────────────────────────────┘│ │
│  └────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ DATA/STORAGE LAYER                                          │ │
│  │                                                              │ │
│  │  ┌──────────────────────────────────────────────────────┐  │ │
│  │  │ S3 Bucket (synapscribe-audio)                        │  │ │
│  │  │ • lectures/  ← User uploads (≤25 min, ≤50MB)        │  │ │
│  │  │ • queries/   ← Voice questions (7-day TTL)           │  │ │
│  │  │ • responses/ ← TTS audio (7-day TTL)                 │  │ │
│  │  │                                                       │  │ │
│  │  │ Event: S3 PutObject (lectures/*) → Lambda trigger    │  │ │
│  │  └──────────────────────────────────────────────────────┘  │ │
│  │                                                              │ │
│  │  ┌──────────────────────────────────────────────────────┐  │ │
│  │  │ DynamoDB (Sessions Table)                            │  │ │
│  │  │ • Conversation transcripts (query-response pairs)    │  │ │
│  │  │ • Lecture metadata (duration, status, tokensUsed)    │  │ │
│  │  │ • Billing: On-demand                                  │  │ │
│  │  │ • TTL: 7 days auto-cleanup                            │  │ │
│  │  └──────────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

**Removed Components (from v2.0):**
- ❌ OpenSearch Serverless (no vector storage needed)
- ❌ Qwen3-Embed-8B (no embeddings model needed)
- ❌ IngestionAgent (replaced with S3 event → ValidateLectureFunction)
- ❌ Cognito User Pools (using Identity Pools for unauthenticated access)

---

## Component Summary

| Component | Technology | Purpose | Cost/Month | Status |
|-----------|-----------|---------|------------|--------|
| Frontend | React + Vite + TypeScript | File upload, voice recording, audio playback | $2 (CloudFront) | ⏳ Phase 3 |
| Authentication | Cognito Identity Pool | Auto guest credentials (no login UI) | $0 (free tier) | ✅ Deployed |
| API Gateway | WebSocket API | Real-time bidirectional communication | $5 | ✅ Deployed |
| Lambda | Python 3.12 (2 functions) | Presigned URLs + lecture validation | $5 | ✅ Deployed |
| EC2 | g5.2xlarge Spot (24GB GPU) | vLLM + gTTS + Qwen2.5-Omni-3B | $330 | ✅ Running |
| AgentCore | FastAPI on EC2:5000 | QueryAgent orchestration | $0 (same EC2) | ⏳ Phase 2 |
| Storage | S3 + DynamoDB | Audio files + conversation transcripts | $8 | ✅ Deployed |
| Observability | CloudWatch | Logs, metrics, traces | $5 | ✅ Deployed |
| **TOTAL** | | | **~$365/month** | |

**Savings vs v2.0:** $706/month (66% reduction) by removing OpenSearch, embeddings model, and IngestionAgent

---

## Key Design Decisions

### 1. No Embeddings (Fits in Context) - 16K Optimized
**Rationale:** 25-minute lectures fit in Qwen2.5-Omni-3B's 16K token context window (Phase 0 validated)
**Benefit:** Eliminates OpenSearch Serverless ($700/month), no embedding model needed, 2x performance vs 32K
**Performance:** 16K context provides ~2x inference speed, ~2x concurrent throughput, ~50% less KV cache memory
**Trade-off:** Max lecture 25 minutes (acceptable for MVP, optimized for quick testing)

### 2. S3 Event-Driven Processing
**Rationale:** Automatic lecture processing without manual WebSocket message
**Benefit:** Simpler architecture, serverless automation, pay-per-use
**Trade-off:** None (objectively better)

### 3. Single Agent (QueryAgent Only)
**Rationale:** IngestionAgent replaced by simple Lambda function
**Benefit:** Fewer moving parts, easier debugging, lower cost
**Trade-off:** Less flexibility (not needed for MVP)

### 4. Cognito Identity Pools (No User Pools)
**Rationale:** No login UI needed, automatic guest credentials
**Benefit:** Simplest authentication, zero user management
**Trade-off:** No user accounts (acceptable for MVP)

### 5. 1-Minute Inactivity Timeout
**Rationale:** Fast MVP testing loop
**Benefit:** Quick session turnover, saves compute
**Trade-off:** May feel abrupt (configurable)

### 6. Post-Session Transcription
**Rationale:** No need for real-time transcription
**Benefit:** Lower latency during conversation
**Trade-off:** Transcripts saved after session ends

### 7. 16K Context Optimization (Phase 0 Decision)
**Rationale:** MVP prioritizes speed over max lecture length; 16K provides 2x performance vs 32K
**Benefit:** ~2x faster inference, ~2x concurrent sequences (8→16), ~50% less KV cache memory (9.4GB→4.7GB)
**Implementation:** `--max-model-len 16384` in vLLM configuration
**Validation:** Phase 0 testing confirmed 25-min lectures fit comfortably in 16K context
**Trade-off:** Max lecture 50min → 25min (acceptable for MVP focus on shorter audio)
**Future:** Can scale to 32K or 128K context as needed for longer lectures

### 8. Simplified Hybrid Architecture: vLLM + gTTS (Phase 0 Finding)
**Rationale:** vLLM can handle ASR via prompt engineering; only TTS needs separate service
**Implementation:**
- vLLM (port 8000): ASR via chat completions + transcription prompt (~2s for 30s audio)
- vLLM (port 8000): Q&A with audio context via conversation history
- gTTS Service (port 8001): TTS only (lightweight, no heavy dependencies)
**Benefit:** Simplified from original plan - eliminated separate ASR endpoint and Whisper
**Architecture Decision:** Qwen2.5-Omni model CAN generate audio (native capability), but vLLM API does NOT expose it (API limitation, not model limitation)
**Validation:** Phase 0 testing confirmed ASR via prompting works perfectly (~2s latency)
**See:** docs/QWEN_INVESTIGATION_FINDINGS.md for complete investigation details
**Future:** If vLLM adds audio output support, can eliminate gTTS and use single service

---

## Data Flows

### Flow 1: Lecture Upload (5-10 seconds)

```
User selects audio → Frontend validates (≤25min, ≤50MB for 16K context)
→ WebSocket: "request_upload" → Lambda generates presigned URL
→ Frontend uploads directly to S3 (lectures/)
→ S3 PutObject event AUTOMATICALLY triggers Lambda ⚡
→ ValidateLectureFunction: Validate + Load into Qwen 16K context
→ Notify frontend via WebSocket: "lecture_ready"
→ Frontend enables Q&A interface
```

### Flow 2: Voice Q&A (<3 seconds to first audio chunk)

```
User records question → Upload to S3 (queries/)
→ WebSocket: "query" → Lambda → AgentCore → QueryAgent
→ QueryAgent pipeline:
   1. Load history from DynamoDB
   2. ASR via vLLM prompting (chat completions + transcription prompt)
      → Send query_transcript to frontend
   3. Generate answer with lecture context (vLLM chat completions)
   4. Send answer_text to frontend
   5. TTS (gTTS service) → Stream audio_chunk (4KB each)
   6. Send audio_complete
   7. Store Q&A in memory
→ Frontend plays audio in real-time
```

### Flow 3: Session End (1-minute inactivity)

```
1 minute no activity → Frontend: "end_session"
→ Lambda → AgentCore → QueryAgent.end_session()
→ Batch save conversation to DynamoDB (TTL: 7 days)
→ Clear memory
```

---

## AWS Services Configuration

### WebSocket API Gateway (✅ Deployed)
```yaml
API ID: 1h29nttho0
Endpoint: wss://1h29nttho0.execute-api.us-east-1.amazonaws.com/Prod
Stage: Prod
Routes:
  - $connect: WebSocketHandler Lambda
  - $disconnect: WebSocketHandler Lambda
  - query: WebSocketHandler Lambda
Region: us-east-1
```

### Cognito Identity Pool (✅ Deployed)
```yaml
Identity Pool ID: us-east-1:43e8b60d-1251-4cb7-8fc0-3deeed0f7244
Identity Pool Name: SynapScribe-IdentityPool
AllowUnauthenticatedIdentities: true
IAM Role (Unauth): Cognito_SynapScribeIdentityPoolUnauth_Role
Permissions:
  - S3: PutObject to queries/* prefix
  - DynamoDB: PutItem/GetItem to SynapScribe-Sessions table
  - API Gateway: Execute WebSocket API
```

### S3 Bucket (✅ Deployed)
```yaml
Bucket: synapscribe-audio-657177702657
Region: us-east-1
Prefixes:
  - lectures/     # Original lecture audio (persistent)
  - queries/      # Voice questions (7-day lifecycle)
  - responses/    # TTS responses (7-day lifecycle)

Lifecycle Policy:
  - queries/*: Delete after 7 days
  - responses/*: Delete after 7 days

Event Notification:
  - Event: s3:ObjectCreated:*
  - Prefix: lectures/
  - Triggers: ValidateLectureFunction Lambda

CORS: Enabled (for presigned URL uploads)
Encryption: AES-256 (SSE-S3)
```

### DynamoDB Table (✅ Deployed)
```yaml
Table: SynapScribe-Sessions
Partition Key: sessionId (String)
Sort Key: lectureId (String)
Billing: PAY_PER_REQUEST (on-demand)
TTL: expiresAt attribute (7 days)
Encryption: AWS owned CMK
Region: us-east-1

Item Types:
  1. Sessions: {sessionId, lectureId, conversation[], totalTurns, createdAt, expiresAt}
  2. Lectures: {lectureId, s3Key, duration, tokensUsed, status}
```

### Lambda Functions (✅ Deployed)

**WebSocketHandler:**
- Function Name: synapscribe-mvp-WebSocketHandler-[hash]
- Trigger: API Gateway WebSocket ($connect, $disconnect, query)
- Runtime: Python 3.12
- Memory: 512MB
- Timeout: 900 seconds (15 minutes)
- Environment Variables:
  - S3_BUCKET: synapscribe-audio-657177702657
  - DYNAMODB_TABLE: SynapScribe-Sessions
  - AGENTCORE_ENDPOINT: http://172.31.36.1:5000
- Purpose: Presigned URLs + route queries to AgentCore + WebSocket connection management

**ValidateLectureFunction:**
- Function Name: synapscribe-mvp-ValidateLectureFunction-[hash]
- Trigger: S3 PutObject event (lectures/* prefix)
- Runtime: Python 3.12
- Memory: 512MB
- Timeout: 300 seconds (5 minutes)
- Environment Variables:
  - S3_BUCKET: synapscribe-audio-657177702657
  - DYNAMODB_TABLE: SynapScribe-Sessions
- Purpose: Validate audio + update DynamoDB metadata + notify frontend via WebSocket

### EC2 Instance (✅ Running - Phase 0)
```yaml
Instance ID: i-0a3e07ed09ca5a5ab
Instance Type: g5.2xlarge (Spot)
GPU: NVIDIA A10G (24GB VRAM)
Public IP: 18.232.121.236
Private IP: 172.31.36.1
Region: us-east-1
OS: Ubuntu 24.04 LTS

Services Running:
  1. vLLM (port 8000): Qwen2.5-Omni-3B
     - ASR via prompt engineering
     - Q&A with audio context
     - Status: ✅ Running (systemd service)

  2. gTTS Service (port 8001): Text-to-Speech
     - Lightweight, CPU-only
     - OpenAI-compatible API
     - Status: ✅ Running (systemd service)

  3. AgentCore (port 5000): FastAPI service
     - QueryAgent orchestration
     - Status: ⏳ To be deployed in Phase 2

vLLM Configuration (16K Context Optimized):
  - max-model-len: 16384 (16K tokens)
  - gpu-memory-utilization: 0.85 (85%)
  - max-num-seqs: 8
  - KV cache: ~4.7GB
  - GPU memory: ~19GB (82.6% utilization)

Performance (Phase 0 Validated):
  - ASR: 1.8s mean (30s audio)
  - Q&A: 4.6s mean
  - TTS: 1.8s mean
  - End-to-End: 8.2s mean
```

### Network Configuration (✅ Configured - Phase 1)

**VPC Setup:**
- **VPC:** Default VPC (vpc-05013e6141a083135) in us-east-1
- **Security Group:** sg-0e912c3d535919465

**Inbound Rules:**
```yaml
- Port 22 (SSH): Current IP only (for management)
- Port 8000 (vLLM): VPC CIDR 172.31.0.0/16 (Lambda access)
- Port 8001 (gTTS): VPC CIDR 172.31.0.0/16 (AgentCore access)
- Port 5000 (AgentCore): VPC CIDR 172.31.0.0/16 (Lambda access, Phase 2)
```

**Outbound Rules:**
```yaml
- All traffic: 0.0.0.0/0 (for model downloads, AWS API calls)
```

**Communication Pattern (Phase 1 Deployed):**
```
Lambda (Same VPC) → EC2 Private IP (172.31.36.1):5000
AgentCore → vLLM (localhost:8000)
AgentCore → gTTS (localhost:8001)
```

**Security Improvements in Phase 1:**
- ✅ Restricted to VPC CIDR only (not public)
- ✅ Lambda uses private IP for AgentCore communication
- ✅ No public internet access to services
- ✅ Security group properly configured

---

## API Reference

### WebSocket Messages

**From Frontend:**
```javascript
// 1. Request upload URL
{
  "type": "request_upload",
  "fileName": "lecture.mp3",
  "fileSize": 50000000,
  "duration": 2850,
  "category": "lecture" | "query"
}

// 2. Query about lecture
{
  "type": "query",
  "sessionId": "session-xyz",
  "lectureId": "lecture-abc",
  "s3Key": "queries/session-xyz/query-1.webm"
}

// 3. End session
{
  "type": "end_session",
  "sessionId": "session-xyz",
  "lectureId": "lecture-abc"
}
```

**To Frontend:**
```javascript
// 1. Upload URL response
{
  "type": "upload_url",
  "uploadUrl": "https://s3...?signature=...",
  "s3Key": "lectures/uuid.mp3",
  "lectureId": "uuid",
  "expiresIn": 900
}

// 2. Lecture ready
{
  "type": "lecture_ready",
  "lectureId": "uuid",
  "message": "Ready for questions!",
  "duration": 2850
}

// 3. Query transcript
{
  "type": "query_transcript",
  "text": "What is technical debt?"
}

// 4. Answer text
{
  "type": "answer_text",
  "text": "Technical debt refers to..."
}

// 5. Audio chunk (streaming)
{
  "type": "audio_chunk",
  "data": "base64_encoded_audio",
  "sampleRate": 24000,
  "index": 0
}

// 6. Audio complete
{
  "type": "audio_complete"
}

// 7. Error
{
  "type": "error",
  "message": "Lecture too long (max 50 min)"
}
```

---

## Deployment

### Phase 1: Infrastructure (✅ COMPLETE - December 3, 2025)

**Status:** All AWS infrastructure deployed successfully via AWS SAM.

**Deployed Resources:**
- ✅ WebSocket API Gateway: `wss://1h29nttho0.execute-api.us-east-1.amazonaws.com/Prod`
- ✅ Lambda Functions: WebSocketHandler, ValidateLectureFunction
- ✅ S3 Bucket: `synapscribe-audio-657177702657`
- ✅ DynamoDB Table: `SynapScribe-Sessions`
- ✅ Cognito Identity Pool: `us-east-1:43e8b60d-1251-4cb7-8fc0-3deeed0f7244`

**Deployment Command Used:**
```bash
cd infrastructure/
sam build
sam deploy --guided --stack-name synapscribe-mvp
```

**See:** `PHASE1_REPORT.md` for complete deployment details

### Phase 2: Backend Services (✅ COMPLETE - December 4, 2025)

**Status:** All backend services operational on EC2 with systemd auto-start configured.

**Deployed Services:**
- ✅ vLLM Inference Server (port 8000) - Model: /opt/models/qwen-omni, 16K context
- ✅ gTTS TTS Service (port 8001) - OpenAI-compatible API
- ✅ AgentCore Service (port 5000) - FastAPI with QueryAgent, VLLMClient, GTTSClient

**Service Endpoints (Private IP: 172.31.36.1):**
- vLLM: http://172.31.36.1:8000 (Health: /health, API: /v1/chat/completions, /v1/models)
- gTTS: http://172.31.36.1:8001 (Health: /health, API: /v1/audio/speech)
- AgentCore: http://172.31.36.1:5000 (Health: /health, API: /invoke, /end_session)

**See:** `PHASE2_REPORT.md` for complete deployment details and service configurations

### 2. EC2 Setup
```bash
# SSH into EC2
ssh -i key.pem ubuntu@<ec2-ip>

# Install vLLM + dependencies
sudo apt-get update && sudo apt-get install -y python3.11 ffmpeg nvidia-driver-535
pip install vllm>=0.8.5 transformers>=4.51.3 torch boto3 librosa

# Download Qwen2.5-Omni-3B
huggingface-cli download Qwen/Qwen2.5-Omni-3B --local-dir /opt/models/qwen-omni

# Start vLLM (16K context optimized for MVP)
# ASR handled via prompt engineering, no separate endpoint needed
vllm serve /opt/models/qwen-omni --host 0.0.0.0 --port 8000 \
  --dtype bfloat16 --max-model-len 16384 --trust-remote-code \
  --gpu-memory-utilization 0.85 --max-num-seqs 8 --max-num-batched-tokens 2048

# Start gTTS Service (TTS only, lightweight)
cd services/direct_inference
pip install fastapi uvicorn gtts pydantic
uvicorn app:app --host 0.0.0.0 --port 8001

# Deploy AgentCore
pip install bedrock-agentcore strands-agents
agentcore configure -e app.py
agentcore launch --region us-east-1
```

### 3. Frontend
```bash
cd frontend/
npm install
npm run build
aws s3 sync dist/ s3://synapscribe-frontend/
```

---

## Monitoring

### CloudWatch Metrics
- **API Gateway:** Request count, latency, errors
- **Lambda:** Invocations, duration, errors
- **EC2:** CPU, GPU utilization (custom metrics)
- **vLLM:** Inference latency (custom metrics)
- **DynamoDB:** Read/write capacity, throttles
- **S3:** Storage size, request count

### CloudWatch Alarms
- High error rate (>5%)
- High Q&A latency (>10s)
- GPU memory exhaustion (>95%)
- Lambda timeout rate (>1%)

---

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| "Lecture too long" | Duration >25 min (16K limit) | Trim audio or split into multiple (or use 32K config) |
| "Audio context not loaded" | Validation failed | Check DynamoDB lecture status, Lambda logs |
| WebSocket disconnects | Network instability | Implement reconnection with backoff |
| Slow inference (>10s) | GPU overload | Check `nvidia-smi`, reduce concurrency |
| S3 event not firing | Missing notification config | Verify S3 bucket notification settings |

---

## Future Enhancements

**Phase 2 (Post-MVP):**
- User authentication (Cognito User Pools)
- Lecture library (browse/search)
- Conversation history view
- Multiple TTS voices
- Mobile app (iOS/Android)

**Phase 3 (Scale):**
- Support lectures >25 min (scale to 32K/128K context or add embeddings + RAG)
- Horizontal scaling (load-balanced EC2 Auto Scaling)
- Caching (ElastiCache Redis)
- Analytics (user behavior, usage metrics)
- A/B testing (16K vs 32K context performance)

---

**End of Architecture Document**

*This architecture prioritizes simplicity, serverless automation, and cost-efficiency for rapid MVP validation.*
