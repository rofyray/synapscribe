# AWS Resources - SynapScribe MVP

**Last Updated:** 2025-12-03
**Purpose:** Track all AWS resources created throughout MVP implementation phases

---

## Resource Summary

| Resource Type | Resource ID | Description | Date Created | Status | Phase | Notes |
|---------------|-------------|-------------|--------------|--------|-------|-------|
| VPC | vpc-05013e6141a083135 | Default VPC (pre-existing) | N/A | Active | Phase 0 | Used for EC2 instance |
| Security Group | sg-0e912c3d535919465 | EC2 security group | Pre-existing | Active | Phase 0 | Ports 22, 8000, 8001, 8080 open |
| EC2 Instance | i-0a3e07ed09ca5a5ab | g5.2xlarge for vLLM + AgentCore | Pre-existing | Active | Phase 0 | 24GB VRAM, Ubuntu 24.04, Public: 18.232.121.236, Private: 172.31.36.1 |
| EBS Volume | vol-0f9b0434baf5daa9e | Root volume for EC2 instance | Pre-existing | Active | Phase 0 | Resized from 20GB to 100GB (gp3, 3000 IOPS) |
| WebSocket API | 1h29nttho0 | API Gateway WebSocket API | 2025-12-03 | Active | Phase 1 | wss://1h29nttho0.execute-api.us-east-1.amazonaws.com/Prod |
| Lambda Function | WebSocketHandler | WebSocket connection handler | 2025-12-03 | Active | Phase 1 | Handles connect/disconnect/query events |
| Lambda Function | ValidateLectureFunction | Lecture audio validation | 2025-12-03 | Active | Phase 1 | Triggered by S3 lecture uploads |
| S3 Bucket | synapscribe-audio-657177702657 | Audio storage | 2025-12-03 | Active | Phase 1 | 7-day lifecycle for queries/responses |
| DynamoDB Table | SynapScribe-Sessions | Session storage | 2025-12-03 | Active | Phase 1 | PAY_PER_REQUEST, 7-day TTL |
| Cognito Identity Pool | us-east-1:43e8b60d-1251-4cb7-8fc0-3deeed0f7244 | Unauthenticated access | 2025-12-03 | Active | Phase 1 | Temporary AWS credentials |

---

## Phase 0: Model Validation

### Compute Resources
- **EC2 Instance**: i-0a3e07ed09ca5a5ab
  - Type: g5.2xlarge (8 vCPUs, 32GB RAM, 24GB VRAM)
  - OS: Ubuntu
  - Public IP: 18.232.121.236
  - Purpose: vLLM inference server + AgentCore runtime
  - Cost: ~$1.20/hour on-demand, ~$0.40/hour spot

### Network Resources
- **VPC**: vpc-05013e6141a083135 (Default VPC)
- **Security Group**: sg-0e912c3d535919465
  - Inbound Rules:
    - Port 22 (SSH): Current IP
    - Port 8000 (vLLM): VPC CIDR 172.31.0.0/16 (Lambda access)
    - Port 8001 (gTTS): VPC CIDR 172.31.0.0/16 (AgentCore access)
    - Port 5000 (AgentCore): VPC CIDR 172.31.0.0/16 (Lambda access, Phase 2)
  - Outbound Rules: All traffic

---

## Phase 1: Infrastructure (✅ COMPLETE - 2025-12-03)

**Deployment Method:** AWS SAM (Serverless Application Model)
**Stack Name:** synapscribe-mvp
**Region:** us-east-1
**Deployment Date:** December 3, 2025

### API Layer
- **WebSocket API Gateway**: 1h29nttho0
  - Endpoint: `wss://1h29nttho0.execute-api.us-east-1.amazonaws.com/Prod`
  - Stage: Prod
  - Routes: $connect, $disconnect, query
- **Lambda Functions**:
  - **WebSocketHandler**: Handles WebSocket connections and query routing
    - Runtime: Python 3.12
    - Timeout: 15 minutes (900 seconds)
    - Memory: 512MB
    - Environment: AGENTCORE_ENDPOINT=http://172.31.36.1:5000
  - **ValidateLectureFunction**: S3-triggered lecture validation
    - Runtime: Python 3.12
    - Timeout: 5 minutes (300 seconds)
    - Memory: 512MB
    - Trigger: S3 ObjectCreated events on lectures/ prefix

### Storage
- **S3 Bucket**: synapscribe-audio-657177702657
  - Prefixes: lectures/, queries/, responses/
  - Lifecycle Policy: 7-day auto-delete for queries/ and responses/
  - CORS Enabled: For presigned URL uploads
  - Event Notifications: lectures/ → ValidateLectureFunction
- **DynamoDB Table**: SynapScribe-Sessions
  - Partition Key: sessionId (String)
  - Sort Key: lectureId (String)
  - Billing Mode: PAY_PER_REQUEST
  - TTL: expiresAt attribute (7 days)
  - Attributes: sessionId, lectureId, conversation[], totalTurns, createdAt, expiresAt

### Authentication
- **Cognito Identity Pool**: us-east-1:43e8b60d-1251-4cb7-8fc0-3deeed0f7244
  - Unauthenticated access: Enabled
  - Identity Pool Name: SynapScribe-IdentityPool
  - Allowed Operations: S3 uploads (queries/), DynamoDB read/write (sessions)

### IAM Roles
- **Lambda Execution Role**: Created by SAM template
  - Permissions: S3 read/write, DynamoDB read/write, CloudWatch Logs, API Gateway execute
- **Cognito Unauthenticated Role**: Created by SAM template
  - Permissions: S3 PutObject (queries/), DynamoDB PutItem/GetItem (sessions)

---

## Phase 2: Backend Services (✅ COMPLETE - December 4, 2025)

### EC2 Instance (from Phase 0)
- **Instance ID**: i-0a3e07ed09ca5a5ab
- **Instance Type**: g4dn.xlarge
- **Region**: us-east-1
- **Private IP**: 172.31.36.1
- **Public IP**: 52.91.74.103 (changes on stop/start)
- **Security Group**: sg-0e912c3d535919465

### Services Running on EC2

#### 1. vLLM Inference Server
- **Port**: 8000
- **Endpoint**: http://172.31.36.1:8000
- **Health Check**: http://172.31.36.1:8000/health
- **Model**: Qwen2.5-Omni-3B (/opt/models/qwen-omni)
- **Context Length**: 16,384 tokens
- **Service File**: /etc/systemd/system/vllm.service
- **Log File**: /var/log/vllm.log
- **Status**: ✅ Active (auto-start enabled)

#### 2. gTTS TTS Service
- **Port**: 8001
- **Endpoint**: http://172.31.36.1:8001
- **Health Check**: http://172.31.36.1:8001/health
- **API**: OpenAI-compatible `/v1/audio/speech`
- **Service File**: /etc/systemd/system/gtts.service
- **Log File**: /var/log/gtts.log
- **Working Directory**: /home/ubuntu/services/direct_inference
- **Status**: ✅ Active (auto-start enabled)

#### 3. AgentCore Service
- **Port**: 5000
- **Endpoint**: http://172.31.36.1:5000
- **Health Check**: http://172.31.36.1:5000/health
- **Service File**: /etc/systemd/system/agentcore.service
- **Log File**: /var/log/agentcore.log
- **Working Directory**: /home/ubuntu/synapscribe/services/agentcore
- **Status**: ✅ Active (auto-start enabled)

### Integration
- Lambda WebSocketHandler connects to AgentCore via private IP (172.31.36.1:5000)
- AgentCore orchestrates ASR (vLLM) → Q&A (vLLM) → TTS (gTTS) pipeline
- All services configured for automatic restart on failure
- See `PHASE2_REPORT.md` for complete deployment details

---

## Phase 3: Frontend (Planned)

### Hosting
- **S3 Bucket**: TBD (synapscribe-frontend)
- **CloudFront Distribution**: TBD

---

## Cost Tracking

| Phase | Monthly Cost Estimate | Notes |
|-------|----------------------|-------|
| Phase 0 | $330 (EC2 Spot) | Single EC2 g5.2xlarge instance |
| Phase 1+ | ~$365 total | Full MVP stack (EC2 + Lambda + S3 + DynamoDB + API Gateway) |

---

## Notes

- All resource IDs marked as "TBD" will be updated as resources are created
- Security group configuration is MVP-style (permissive) - production should use VPC peering or PrivateLink
- EC2 instance uses default VPC for simplicity
- Spot instances used for cost savings (70% cheaper than on-demand)

