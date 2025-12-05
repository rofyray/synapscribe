export type WebSocketMessageType =
  | 'session.create'
  | 'session.update'
  | 'transcript.complete'
  | 'question.ask'
  | 'question.response'
  | 'error'
  | 'ping'
  | 'pong';

export interface WebSocketMessage {
  type: WebSocketMessageType;
  sessionId: string;
  timestamp: string;
  data: unknown;
}

export interface QuestionMessage extends WebSocketMessage {
  type: 'question.ask';
  data: {
    question: string;
  };
}

export interface ResponseMessage extends WebSocketMessage {
  type: 'question.response';
  data: {
    answer: string;
    confidence?: number;
    isStreaming?: boolean;
  };
}

export interface TranscriptMessage extends WebSocketMessage {
  type: 'transcript.complete';
  data: {
    transcript: string;
    duration: number;
  };
}

export interface ErrorMessage extends WebSocketMessage {
  type: 'error';
  data: {
    code: string;
    message: string;
  };
}
