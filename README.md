# SynapScribe Monorepo

AI-powered lecture transcription and note-taking system.

## Structure

- **synapscribe-backend/** - Backend services (Python/AWS Lambda)
- **synapscribe-frontend/** - Frontend app (React/TypeScript/Vite)

## Quick Start

**Backend:**
\`\`\`bash
cd synapscribe-backend
# See backend README
\`\`\`

**Frontend:**
\`\`\`bash
cd synapscribe-frontend
npm install
npm run dev
\`\`\`

## Infrastructure

- Backend: AWS Lambda, API Gateway, DynamoDB, S3
- AI: vLLM on EC2 g5.2xlarge
- Frontend: S3 + CloudFront
