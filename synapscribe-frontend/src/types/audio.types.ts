export type AudioFormat = 'mp3' | 'wav' | 'm4a' | 'mp4' | 'ogg' | 'flac' | 'webm';

export interface AudioFile {
  file: File;
  format: AudioFormat;
  size: number;
  duration?: number;
  url?: string;
}

export interface RecordingState {
  isRecording: boolean;
  isPaused: boolean;
  duration: number;
  audioBlob: Blob | null;
}

export interface AudioValidationResult {
  isValid: boolean;
  error?: string;
  warnings?: string[];
}
