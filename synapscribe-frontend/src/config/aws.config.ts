import { fromCognitoIdentityPool } from '@aws-sdk/credential-providers';
import { S3Client } from '@aws-sdk/client-s3';

const AWS_REGION = import.meta.env.VITE_AWS_REGION || 'us-east-1';
const COGNITO_IDENTITY_POOL_ID = import.meta.env.VITE_COGNITO_IDENTITY_POOL_ID || '';

export const credentialsProvider = fromCognitoIdentityPool({
  clientConfig: { region: AWS_REGION },
  identityPoolId: COGNITO_IDENTITY_POOL_ID,
});

export const s3Client = new S3Client({
  region: AWS_REGION,
  credentials: credentialsProvider,
});

export const awsConfig = {
  region: AWS_REGION,
  s3Bucket: import.meta.env.VITE_S3_BUCKET || 'synapscribe-audio',
  cognitoIdentityPoolId: COGNITO_IDENTITY_POOL_ID,
};
