import { PutObjectCommand } from '@aws-sdk/client-s3';
import { s3Client, awsConfig } from '../config/aws.config';
import { v4 as uuidv4 } from 'uuid';

export class S3Service {
  async uploadAudio(file: File): Promise<string> {
    const fileKey = `lectures/${uuidv4()}/${file.name}`;

    try {
      const command = new PutObjectCommand({
        Bucket: awsConfig.s3Bucket,
        Key: fileKey,
        Body: file,
        ContentType: file.type,
        Metadata: {
          originalName: file.name,
          uploadedAt: new Date().toISOString(),
        },
      });

      await s3Client.send(command);
      return fileKey;
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      console.error('S3 upload error:', error);
      throw new Error(`Failed to upload audio: ${errorMessage}`);
    }
  }

  getFileUrl(fileKey: string): string {
    return `https://${awsConfig.s3Bucket}.s3.${awsConfig.region}.amazonaws.com/${fileKey}`;
  }
}

export const s3Service = new S3Service();
