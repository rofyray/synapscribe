# SynapScribe 

AI-powered lecture transcription and note-taking system combining real-time audio processing with intelligent summarization.

## 🏗️ Repository Structure

synapscribe/
├── synapscribe-backend/     Backend services (Python/AWS Lambda)
├── synapscribe-frontend/    Frontend application (React/TypeScript)
├── .git/                    Git repository
├── .gitignore              Monorepo gitignore
└── README.md               This file

## 🚀 Quick Start

### Backend Development

```bash
cd synapscribe-backend
# See backend README for detailed setup

Frontend Development

cd synapscribe-frontend
npm install
npm run dev

📦 Components

Backend (synapscribe-backend/)

- Technology: Python 3.11, AWS SAM
- Services: Lambda functions, API Gateway, DynamoDB
- AI Processing: vLLM on EC2 g5.2xlarge with Qwen2.5-Omni-7B
- Infrastructure: AWS CloudFormation via SAM

Frontend (synapscribe-frontend/)

- Technology: React 18, TypeScript, Vite
- Features: Real-time transcription, AI summarization, audio recording
- Hosting: S3 + CloudFront
- Authentication: AWS Cognito Identity Pool

🌐 Infrastructure

- Backend API: API Gateway + Lambda
- AI Model: vLLM server on EC2 (g5.2xlarge)
- Storage: S3 (audio files), DynamoDB (transcripts)
- Frontend CDN: CloudFront distribution
- Region: us-east-1

📚 Documentation

- Backend documentation: synapscribe-backend/README.md
- Frontend documentation: synapscribe-frontend/README.md
- Deployment guide: synapscribe-backend/docs/DEPLOYMENT_SUMMARY.md

🔧 Development Workflow

1. Clone repository:
git clone git@github.com:rofyray/synapscribe.git
cd synapscribe
2. Backend setup:
cd synapscribe-backend
# Follow backend README
3. Frontend setup:
cd synapscribe-frontend
npm install
npm run dev

🚀 Deployment

- Backend: Deploy via AWS SAM
- Frontend: Build and deploy to S3, invalidate CloudFront cache
- AI Service: Managed via systemd on EC2

📄 License

Proprietary - All rights reserved