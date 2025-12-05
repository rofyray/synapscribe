# Phase 1 Implementation Plan: AWS Infrastructure Setup on EC2

## Overview

**Objective:** Deploy AWS infrastructure for SynapScribe MVP using SAM (Serverless Application Model) with development entirely on EC2.

**Development Approach:**
- ✅ Develop on EC2 via VS Code Remote
- ✅ Install SAM CLI on EC2
- ✅ Deploy and test directly (no local testing)
- ✅ Leverage existing EC2 setup (vLLM, gTTS already running)

**Phase Status:** Phase 0 COMPLETE ✅ - Ready to begin Phase 1

---

## Execution Checklist (Immediate Tasks)

**User approved - proceeding with:**

- [ ] **Task 1:** Copy this plan to EC2 for easy reference
  - Command: `scp -i "qwen-test-login.pem" /Users/rofy/.claude/plans/harmonic-leaping-bengio.md ubuntu@ec2-52-91-74-103.compute-1.amazonaws.com:/home/ubuntu/synapscribe/PHASE1_PLAN.md`

- [ ] **Task 2:** Run first setup commands
  - Install SAM CLI on EC2 (Step 1.1)
  - Configure AWS credentials (Step 1.2)
  - Copy project files to EC2 (Step 1.3)

- [ ] **Task 3:** Create project structure on EC2
  - Create directory structure (Step 2.1)
  - Create placeholder files
  - Verify structure with tree command

- [ ] **Task 4:** Implement Lambda functions
  - Create WebSocketHandler function (Step 3.1)
  - Create ValidateLectureFunction (Step 3.2)
  - Create requirements.txt files
  - Copy implementations from MVP_PLAN.md

**Execution Mode:** After exiting plan mode, proceed with these tasks sequentially.

---

## Prerequisites Check

**Already Complete:**
- ✅ EC2 g5.2xlarge instance running (i-0a3e07ed09ca5a5ab)
- ✅ vLLM server on port 8000 (Qwen2.5-Omni-3B, 16K context)
- ✅ gTTS service on port 8001
- ✅ Phase 0 validation passed (all metrics exceeded targets)
- ✅ VS Code connected to EC2 with terminal access

**To Be Done:**
- SAM CLI installation on EC2
- AWS credentials configuration on EC2
- Project structure setup on EC2
- Lambda function implementation
- SAM template creation
- Infrastructure deployment

---

## Step 1: Setup Development Environment on EC2

### 1.1 Install AWS SAM CLI on EC2

**Commands to run on EC2:**

```bash
# Connect to EC2
ssh -i "qwen-test-login.pem" ubuntu@ec2-52-91-74-103.compute-1.amazonaws.com

# Install SAM CLI prerequisites
sudo apt-get update
sudo apt-get install -y unzip

# Download and install AWS SAM CLI
wget https://github.com/aws/aws-sam-cli/releases/latest/download/aws-sam-cli-linux-x86_64.zip
unzip aws-sam-cli-linux-x86_64.zip -d sam-installation
sudo ./sam-installation/install

# Verify installation
sam --version  # Should show: SAM CLI, version 1.x.x

# Clean up installation files
rm -rf sam-installation aws-sam-cli-linux-x86_64.zip
```

### 1.2 Configure AWS Credentials on EC2

**Option A: Using existing credentials (if AWS CLI configured locally)**

```bash
# On local machine, copy credentials to EC2
scp -i "qwen-test-login.pem" ~/.aws/credentials ubuntu@ec2-52-91-74-103.compute-1.amazonaws.com:~/.aws/
scp -i "qwen-test-login.pem" ~/.aws/config ubuntu@ec2-52-91-74-103.compute-1.amazonaws.com:~/.aws/
```

**Option B: Configure new credentials on EC2**

```bash
# On EC2
aws configure
# Enter:
# - AWS Access Key ID
# - AWS Secret Access Key
# - Default region: us-east-1
# - Default output format: json

# Verify credentials
aws sts get-caller-identity
```

### 1.3 Copy Project Files to EC2

**On local machine:**

```bash
# Create synapscribe directory on EC2 (if not exists)
ssh -i "qwen-test-login.pem" ubuntu@ec2-52-91-74-103.compute-1.amazonaws.com "mkdir -p /home/ubuntu/synapscribe"

# Copy docs/ directory (contains MVP_PLAN.md, ARCHITECTURE.md, etc.)
scp -r -i "qwen-test-login.pem" /Users/rofy/Documents/dev/synapscribe/docs \
  ubuntu@ec2-52-91-74-103.compute-1.amazonaws.com:/home/ubuntu/synapscribe/

# Copy notebooks/ directory (for reference)
scp -r -i "qwen-test-login.pem" /Users/rofy/Documents/dev/synapscribe/notebooks \
  ubuntu@ec2-52-91-74-103.compute-1.amazonaws.com:/home/ubuntu/synapscribe/

# Copy phase0-results/ (validation data)
scp -r -i "qwen-test-login.pem" /Users/rofy/Documents/dev/synapscribe/phase0-results \
  ubuntu@ec2-52-91-74-103.compute-1.amazonaws.com:/home/ubuntu/synapscribe/
```

**Alternative: Use VS Code Remote to sync files**
- Connect VS Code to EC2
- Use File > Open Folder → `/home/ubuntu/synapscribe`
- Manually copy/paste files via VS Code interface

---

## Step 2: Create Project Structure on EC2

### 2.1 Create Directory Structure

**On EC2 (via VS Code terminal or SSH):**

```bash
cd /home/ubuntu/synapscribe

# Create Phase 1 infrastructure directories
mkdir -p lambda/websocket_handler
mkdir -p lambda/validate_lecture
mkdir -p services  # For future AgentCore (Phase 2)
mkdir -p tests     # For integration tests

# Create placeholder files
touch lambda/websocket_handler/__init__.py
touch lambda/websocket_handler/websocket_handler.py
touch lambda/validate_lecture/__init__.py
touch lambda/validate_lecture/validate_lecture.py
touch template.yaml
touch samconfig.toml

# Verify structure
tree -L 3 /home/ubuntu/synapscribe
```

**Expected structure:**
```
/home/ubuntu/synapscribe/
├── docs/
│   ├── MVP_PLAN.md
│   ├── PHASE0_REPORT.md
│   ├── ARCHITECTURE.md
│   └── ...
├── notebooks/
│   ├── phase0_validation.ipynb
│   ├── phase0_benchmarks.ipynb
│   └── ...
├── phase0-results/
│   ├── benchmarks/
│   └── ...
├── lambda/
│   ├── websocket_handler/
│   │   ├── __init__.py
│   │   ├── websocket_handler.py
│   │   └── requirements.txt (to be created)
│   └── validate_lecture/
│       ├── __init__.py
│       ├── validate_lecture.py
│       └── requirements.txt (to be created)
├── services/  (empty for now, Phase 2)
├── tests/
└── template.yaml
```

---

## Step 3: Implement Lambda Functions

### 3.1 Create WebSocketHandler Lambda

**File: `lambda/websocket_handler/websocket_handler.py`**

**Implementation from MVP_PLAN.md (lines 800-997):**

Key features:
- Handle WebSocket connection lifecycle ($connect, $disconnect)
- Generate presigned S3 URLs for audio uploads
- Route queries to AgentCore on EC2
- Stream responses back via WebSocket
- Handle session end events

**Dependencies:** `lambda/websocket_handler/requirements.txt`

```txt
boto3==1.34.0
requests==2.31.0
```

### 3.2 Create ValidateLectureFunction Lambda

**File: `lambda/validate_lecture/validate_lecture.py`**

**Implementation from MVP_PLAN.md (lines 1001-1200):**

Key features:
- Triggered by S3 PutObject event (lectures/ prefix)
- Validate audio file (format, size, duration, integrity)
- Load audio into vLLM context (16K tokens)
- Save lecture metadata to DynamoDB
- Notify frontend via WebSocket

**Dependencies:** `lambda/validate_lecture/requirements.txt`

```txt
boto3==1.34.0
requests==2.31.0
librosa==0.10.1
numpy==1.26.2
```

**Note:** Lambda layers may be needed for librosa (large dependencies)

---

## Step 4: Create SAM Template

### 4.1 Create template.yaml

**File: `template.yaml`**

**Full template from MVP_PLAN.md (lines 1514-1661):**

**Key resources:**
1. **Cognito Identity Pool** - Unauthenticated access
2. **IAM Role** - For unauthenticated users (S3 upload, API invoke)
3. **S3 Bucket** - Audio storage (synapscribe-audio)
   - Lifecycle rules: 7-day auto-delete for queries/responses
   - S3 event trigger → ValidateLectureFunction
4. **DynamoDB Table** - Sessions table with TTL
5. **WebSocket API Gateway** - Real-time communication
6. **Lambda Functions:**
   - WebSocketHandler (connection management, routing)
   - ValidateLectureFunction (S3 event-triggered validation)

**Environment variables to configure:**
- `VLLM_ENDPOINT`: http://172.31.x.x:8000 (EC2 private IP)
- `S3_BUCKET`: synapscribe-audio
- `DYNAMODB_TABLE`: SynapScribe-Sessions

### 4.2 Create samconfig.toml (deployment config)

**File: `samconfig.toml`**

```toml
version = 0.1

[default]
[default.deploy]
[default.deploy.parameters]
stack_name = "synapscribe-mvp"
s3_bucket = "aws-sam-cli-managed-default-samclisourcebucket-XXXX"
s3_prefix = "synapscribe-mvp"
region = "us-east-1"
capabilities = "CAPABILITY_IAM"
parameter_overrides = "EC2PrivateIP=172.31.x.x"
confirm_changeset = true
```

**Note:** EC2 private IP will be determined in next step

---

## Step 5: Configure EC2 for Lambda Access

### 5.1 Get EC2 Private IP

**On EC2:**

```bash
# Get EC2 private IP (for vLLM endpoint)
curl http://169.254.169.254/latest/meta-data/local-ipv4

# Example output: 172.31.45.123
# Save this - you'll need it for template.yaml
```

### 5.2 Update Security Group

**Allow Lambda to access vLLM on EC2:**

**On local machine or EC2 (with AWS CLI):**

```bash
# Get EC2 security group ID
EC2_SG_ID=$(aws ec2 describe-instances \
  --instance-ids i-0a3e07ed09ca5a5ab \
  --query 'Reservations[0].Instances[0].SecurityGroups[0].GroupId' \
  --output text)

echo "EC2 Security Group: $EC2_SG_ID"

# Add inbound rule for vLLM (port 8000) from Lambda
# Lambda runs in default VPC, allow from VPC CIDR
aws ec2 authorize-security-group-ingress \
  --group-id $EC2_SG_ID \
  --protocol tcp \
  --port 8000 \
  --cidr 172.31.0.0/16  # Default VPC CIDR (adjust if different)

# Add inbound rule for gTTS (port 8001)
aws ec2 authorize-security-group-ingress \
  --group-id $EC2_SG_ID \
  --protocol tcp \
  --port 8001 \
  --cidr 172.31.0.0/16

# Verify security group rules
aws ec2 describe-security-groups --group-ids $EC2_SG_ID
```

### 5.3 Setup vLLM Systemd Service (Auto-start)

**On EC2:**

**Create systemd service file:**

```bash
sudo nano /etc/systemd/system/vllm.service
```

**Content:**

```ini
[Unit]
Description=vLLM Qwen2.5-Omni-3B Server
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu
ExecStart=/home/ubuntu/.local/bin/vllm serve /opt/models/qwen-omni \
  --host 0.0.0.0 \
  --port 8000 \
  --dtype bfloat16 \
  --max-model-len 16384 \
  --trust-remote-code \
  --gpu-memory-utilization 0.85
Restart=on-failure
RestartSec=10
StandardOutput=append:/var/log/vllm.log
StandardError=append:/var/log/vllm.log

[Install]
WantedBy=multi-user.target
```

**Enable and start service:**

```bash
sudo systemctl daemon-reload
sudo systemctl enable vllm.service
sudo systemctl start vllm.service

# Check status
sudo systemctl status vllm.service

# View logs
sudo tail -f /var/log/vllm.log
```

**Create systemd service for gTTS:**

```bash
sudo nano /etc/systemd/system/gtts.service
```

**Content:**

```ini
[Unit]
Description=gTTS Text-to-Speech Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/synapscribe/services/gtts
ExecStart=/usr/bin/python3 /home/ubuntu/synapscribe/services/gtts/app.py
Restart=on-failure
RestartSec=10
StandardOutput=append:/var/log/gtts.log
StandardError=append:/var/log/gtts.log

[Install]
WantedBy=multi-user.target
```

**Enable and start:**

```bash
sudo systemctl daemon-reload
sudo systemctl enable gtts.service
sudo systemctl start gtts.service
sudo systemctl status gtts.service
```

---

## Step 6: Deploy Infrastructure with SAM

### 6.1 Build SAM Application

**On EC2 (in /home/ubuntu/synapscribe):**

```bash
cd /home/ubuntu/synapscribe

# Build Lambda functions
sam build

# Expected output:
# Building codeuri: lambda/websocket_handler
# Building codeuri: lambda/validate_lecture
# Build Succeeded
```

### 6.2 Deploy with Guided Mode

**First deployment (interactive):**

```bash
sam deploy --guided
```

**You'll be prompted for:**

```
Stack Name [synapscribe-mvp]: synapscribe-mvp
AWS Region [us-east-1]: us-east-1
Parameter EC2PrivateIP []: 172.31.45.123  # Use your EC2 private IP
Confirm changes before deploy [Y/n]: Y
Allow SAM CLI IAM role creation [Y/n]: Y
Disable rollback [y/N]: N
WebSocketHandler may not have authorization defined, Is this okay? [y/N]: y
Save arguments to configuration file [Y/n]: Y
SAM configuration file [samconfig.toml]: samconfig.toml
SAM configuration environment [default]: default
```

**SAM will:**
1. Create CloudFormation stack
2. Deploy all resources (Cognito, S3, DynamoDB, API Gateway, Lambda)
3. Output endpoint URLs

### 6.3 Capture Outputs

**After deployment, save these outputs:**

```bash
# Get CloudFormation outputs
aws cloudformation describe-stacks \
  --stack-name synapscribe-mvp \
  --query 'Stacks[0].Outputs' \
  --output table

# Example outputs:
# WebSocketApiEndpoint: wss://abc123.execute-api.us-east-1.amazonaws.com/Prod
# AudioBucketName: synapscribe-audio
# SessionsTableName: SynapScribe-Sessions
# IdentityPoolId: us-east-1:xxxxx-xxxx-xxxx
```

**Save to environment file:**

```bash
cat > .env.phase1 <<EOF
WEBSOCKET_ENDPOINT=wss://abc123.execute-api.us-east-1.amazonaws.com/Prod
S3_BUCKET=synapscribe-audio
DYNAMODB_TABLE=SynapScribe-Sessions
IDENTITY_POOL_ID=us-east-1:xxxxx-xxxx-xxxx
VLLM_ENDPOINT=http://172.31.45.123:8000
GTTS_ENDPOINT=http://172.31.45.123:8001
EOF
```

---

## Step 7: Post-Deployment Configuration

### 7.1 Update Lambda Environment Variables

**If EC2 IP changes or needs updating:**

```bash
# Update WebSocketHandler environment
aws lambda update-function-configuration \
  --function-name synapscribe-mvp-WebSocketHandler-XXXX \
  --environment "Variables={
    S3_BUCKET=synapscribe-audio,
    DYNAMODB_TABLE=SynapScribe-Sessions,
    VLLM_ENDPOINT=http://172.31.45.123:8000,
    AGENTCORE_ENDPOINT=http://172.31.45.123:5000
  }"

# Update ValidateLectureFunction environment
aws lambda update-function-configuration \
  --function-name synapscribe-mvp-ValidateLectureFunction-XXXX \
  --environment "Variables={
    S3_BUCKET=synapscribe-audio,
    DYNAMODB_TABLE=SynapScribe-Sessions,
    VLLM_ENDPOINT=http://172.31.45.123:8000
  }"
```

### 7.2 Configure WebSocket API Routes

**Create WebSocket routes:**

```bash
# Get WebSocket API ID
API_ID=$(aws apigatewayv2 get-apis \
  --query "Items[?Name=='SynapScribeWebSocket'].ApiId" \
  --output text)

# Get Lambda ARN
LAMBDA_ARN=$(aws lambda get-function \
  --function-name synapscribe-mvp-WebSocketHandler-XXXX \
  --query 'Configuration.FunctionArn' \
  --output text)

# Create routes: $connect, $disconnect, request_upload, query, end_session
# (This may be automated in SAM template - verify first)
```

---

## Step 8: Testing Infrastructure

### 8.1 Test S3 Upload

**On EC2 or local:**

```bash
# Test S3 bucket access
aws s3 ls s3://synapscribe-audio/

# Upload test file
echo "test audio data" > test.mp3
aws s3 cp test.mp3 s3://synapscribe-audio/lectures/test-123.mp3

# Check S3 event triggered Lambda
aws logs tail /aws/lambda/synapscribe-mvp-ValidateLectureFunction-XXXX --follow
```

### 8.2 Test DynamoDB Access

```bash
# List items in Sessions table
aws dynamodb scan --table-name SynapScribe-Sessions

# Insert test session
aws dynamodb put-item \
  --table-name SynapScribe-Sessions \
  --item '{
    "sessionId": {"S": "test-session-123"},
    "lectureId": {"S": "test-lecture-123"},
    "status": {"S": "active"},
    "createdAt": {"S": "2025-12-03T10:00:00Z"}
  }'
```

### 8.3 Test WebSocket Connection

**Use wscat (install if needed):**

```bash
# Install wscat
npm install -g wscat

# Connect to WebSocket API
wscat -c wss://abc123.execute-api.us-east-1.amazonaws.com/Prod

# Send test message
> {"type": "request_upload", "fileName": "test.mp3", "fileSize": 1024, "category": "lecture"}

# Should receive presigned URL response
```

### 8.4 Test vLLM Endpoint from Lambda

**Create test Lambda:**

```bash
# Test vLLM connectivity from Lambda environment
# (Can use AWS Lambda console to create test function)
```

---

## Step 9: Integration Testing

### 9.1 End-to-End Upload Flow

**Test sequence:**

1. **Request upload URL** → WebSocket
2. **Upload to S3** → Presigned URL
3. **S3 event triggers ValidateLectureFunction**
4. **Lecture validation** → Audio integrity, duration check
5. **Load into vLLM context** → 16K tokens
6. **Save metadata to DynamoDB**
7. **Notify frontend** → lecture_ready message

**Manual test:**

```bash
# 1. Connect WebSocket
wscat -c wss://abc123.execute-api.us-east-1.amazonaws.com/Prod

# 2. Request upload URL
> {"type": "request_upload", "fileName": "lecture.mp3", "fileSize": 5000000, "category": "lecture"}

# 3. Use presigned URL to upload (copy URL from response)
curl -X PUT -T /path/to/lecture.mp3 "PRESIGNED_URL_HERE"

# 4. Watch for lecture_ready message on WebSocket
< {"type": "lecture_ready", "lectureId": "xxx", "duration": 300, "tokensUsed": 12000}
```

### 9.2 Query Flow Test

**Test sequence:**

1. **Upload query audio** → WebSocket request_upload
2. **Send query** → WebSocket with sessionId, lectureId, s3Key
3. **Lambda routes to AgentCore** (Phase 2 - not yet implemented)
4. **Stream response back** → WebSocket chunks

**Note:** Query flow requires AgentCore (Phase 2) - can test routing only in Phase 1

---

## Step 10: Monitoring & Troubleshooting

### 10.1 CloudWatch Logs

**Monitor Lambda logs:**

```bash
# WebSocketHandler logs
aws logs tail /aws/lambda/synapscribe-mvp-WebSocketHandler-XXXX --follow

# ValidateLectureFunction logs
aws logs tail /aws/lambda/synapscribe-mvp-ValidateLectureFunction-XXXX --follow

# Search for errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/synapscribe-mvp-WebSocketHandler-XXXX \
  --filter-pattern "ERROR"
```

### 10.2 Common Issues & Solutions

**Issue 1: Lambda can't reach vLLM on EC2**
- Solution: Check EC2 security group allows inbound from VPC CIDR
- Solution: Verify EC2 private IP is correct in environment variables
- Solution: Test connectivity: `curl http://172.31.x.x:8000/health`

**Issue 2: S3 event not triggering Lambda**
- Solution: Check S3 bucket notification configuration
- Solution: Verify Lambda permission (ValidateLectureFunctionPermission)
- Solution: Check Lambda execution role has S3 read permissions

**Issue 3: WebSocket connection fails**
- Solution: Check API Gateway deployment stage
- Solution: Verify Lambda integration configured for routes
- Solution: Check Lambda execution role has API Gateway permissions

**Issue 4: DynamoDB access denied**
- Solution: Check Lambda execution role has DynamoDB CRUD policy
- Solution: Verify table name matches environment variable

### 10.3 Performance Monitoring

```bash
# Lambda metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=synapscribe-mvp-WebSocketHandler-XXXX \
  --start-time 2025-12-03T00:00:00Z \
  --end-time 2025-12-03T23:59:59Z \
  --period 3600 \
  --statistics Average,Maximum

# API Gateway metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApiGateway \
  --metric-name Count \
  --dimensions Name=ApiName,Value=SynapScribeWebSocket \
  --start-time 2025-12-03T00:00:00Z \
  --end-time 2025-12-03T23:59:59Z \
  --period 3600 \
  --statistics Sum
```

---

## Deliverables Checklist

**Phase 1 completion criteria:**

- [ ] SAM CLI installed and configured on EC2
- [ ] AWS credentials configured on EC2
- [ ] Project structure created on EC2
- [ ] Lambda functions implemented:
  - [ ] WebSocketHandler (websocket_handler.py)
  - [ ] ValidateLectureFunction (validate_lecture.py)
- [ ] SAM template created (template.yaml)
- [ ] Infrastructure deployed successfully
- [ ] EC2 security group configured for Lambda access
- [ ] vLLM systemd service running (auto-start enabled)
- [ ] gTTS systemd service running (auto-start enabled)
- [ ] S3 bucket created with lifecycle rules
- [ ] DynamoDB table created with TTL
- [ ] WebSocket API Gateway deployed
- [ ] Cognito Identity Pool configured
- [ ] S3 event trigger configured
- [ ] End-to-end upload flow tested
- [ ] CloudWatch logging verified
- [ ] Environment variables documented (.env.phase1)

---

## Next Steps: Phase 2

**After Phase 1 completion:**

1. **Implement AgentCore** on EC2 (Bedrock AgentCore framework)
2. **Implement QueryAgent** (audio Q&A logic)
3. **Integrate AgentCore with Lambda** (WebSocketHandler → AgentCore)
4. **Test end-to-end Q&A flow** (upload → query → answer)
5. **Load testing** (10+ concurrent users)

**Phase 2 duration:** 1 week (per MVP_PLAN.md)

---

## Critical Files Reference

**Implementation references from MVP_PLAN.md:**
- SAM template: lines 1514-1661
- WebSocketHandler: lines 800-997
- ValidateLectureFunction: lines 1001-1200
- Phase 1 tasks: lines 1506-1678

**Files to create on EC2:**
- `/home/ubuntu/synapscribe/template.yaml`
- `/home/ubuntu/synapscribe/samconfig.toml`
- `/home/ubuntu/synapscribe/lambda/websocket_handler/websocket_handler.py`
- `/home/ubuntu/synapscribe/lambda/websocket_handler/requirements.txt`
- `/home/ubuntu/synapscribe/lambda/validate_lecture/validate_lecture.py`
- `/home/ubuntu/synapscribe/lambda/validate_lecture/requirements.txt`
- `/etc/systemd/system/vllm.service`
- `/etc/systemd/system/gtts.service`
- `/home/ubuntu/synapscribe/.env.phase1` (deployment outputs)

**Files to read before implementation:**
- `docs/MVP_PLAN.md` (complete Phase 1 details)
- `docs/PHASE0_REPORT.md` (validated architecture)
- `docs/ARCHITECTURE.md` (system design)

---

## Estimated Timeline

**Phase 1 total: 1 week (5-7 days)**

- Day 1: Setup (Steps 1-2) - SAM CLI, AWS config, project structure
- Day 2: Lambda functions (Step 3) - Implement WebSocketHandler, ValidateLectureFunction
- Day 3: SAM template (Step 4) - Create template.yaml with all resources
- Day 4: EC2 config (Step 5) - Security groups, systemd services
- Day 5: Deploy (Steps 6-7) - SAM deploy, post-deployment config
- Day 6: Testing (Steps 8-9) - Integration testing, troubleshooting
- Day 7: Documentation (Step 10) - Monitoring setup, deliverables check

---

## Success Metrics

**Phase 1 is complete when:**

1. ✅ Infrastructure deployed (CloudFormation stack shows CREATE_COMPLETE)
2. ✅ S3 upload triggers Lambda successfully
3. ✅ Lecture metadata saved to DynamoDB
4. ✅ WebSocket connection established and messages sent
5. ✅ vLLM accessible from Lambda (network connectivity verified)
6. ✅ All Lambda functions have <5% error rate
7. ✅ CloudWatch logs showing successful executions
8. ✅ SystemD services auto-start after EC2 reboot

**Ready for Phase 2:** AgentCore implementation and Q&A integration
