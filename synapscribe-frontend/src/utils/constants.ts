export const MAX_FILE_SIZE_MB = parseInt(import.meta.env.VITE_MAX_FILE_SIZE_MB) || 100;
export const SESSION_TIMEOUT_MS = parseInt(import.meta.env.VITE_SESSION_TIMEOUT_MS) || 60000;
export const SUPPORTED_FORMATS = (import.meta.env.VITE_SUPPORTED_FORMATS || 'mp3,wav,m4a,mp4,ogg,flac,webm').split(',');
export const WEB_SOCKET_URL = import.meta.env.VITE_WEBSOCKET_URL || 'ws://localhost:8000/ws';
