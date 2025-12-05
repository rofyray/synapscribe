export interface Session {
  sessionId: string;
  userId: string;
  audioFileKey: string;
  transcript?: string;
  createdAt: string;
  lastActivityAt: string;
  status: 'active' | 'inactive' | 'expired';
  metadata?: {
    fileName: string;
    fileSize: number;
    duration?: number;
    mimeType: string;
  };
}

export interface SessionState {
  currentSession: Session | null;
  isActive: boolean;
  lastActivity: number;
}
