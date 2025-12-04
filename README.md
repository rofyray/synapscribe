# SynapScribe

Voice-to-voice AI learning assistant for lecture Q&A with audio context awareness.

## Overview

SynapScribe enables students to upload lecture audio and ask questions vocally, receiving spoken answers that reference the lecture content. Built with:

- **vLLM** (Qwen2.5-Omni-3B) - ASR + Q&A with 16K context
- **gTTS** - Text-to-speech synthesis
- **AgentCore** - Q&A pipeline orchestration
- **AWS** - WebSocket API, Lambda, S3, DynamoDB, Cognito

## Architecture

- **Phase 0**: ✅ Model validation (Qwen2.5-Omni-3B)
- **Phase 1**: ✅ AWS serverless infrastructure
- **Phase 2**: ✅ Backend services (vLLM, gTTS, AgentCore)
- **Phase 3**: ⏳ React frontend (In Progress)

See `docs/ARCHITECTURE.md` for complete architecture details.

## Deployment Status

All backend services operational on EC2:
- vLLM Inference Server (port 8000)
- gTTS TTS Service (port 8001)
- AgentCore Service (port 5000)

See `docs/PHASE2_REPORT.md` for deployment details.

## Project Structure

```
synapscribe/
├── docs/               # Documentation
├── services/           # Application services
│   ├── agentcore/      # Main orchestration service
│   └── direct_inference/  # gTTS TTS service
├── DELETED_FILES.md    # Record of removed files
└── README.md
```

## Documentation

- `ARCHITECTURE.md` - System architecture
- `MVP_PLAN.md` - Development phases and timeline
- `AWS_RESOURCES.md` - AWS infrastructure details
- `PHASE0_REPORT.md` - Model validation results
- `PHASE1_REPORT.md` - Infrastructure deployment
- `PHASE2_REPORT.md` - Backend services deployment
- `DELETED_FILES.md` - Cleanup documentation

## Setup

See individual service README files for setup instructions:
- `services/agentcore/README.md`
- `services/direct_inference/README.md`

## Security Notes

- SSH keys (`*.pem`) are NOT included in this repository
- Environment variables in `.env.phase1` are NOT committed
- AWS credentials must be configured separately

## License

[To be determined]
