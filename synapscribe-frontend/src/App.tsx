import { useState, useEffect } from 'react';
import { useSessionStore } from './store/sessionStore';
import { useChatStore } from './store/chatStore';
import { websocketService } from './services/websocketService';
import { s3Service } from './services/s3Service';
import { useInactivityTimeout } from './hooks/useInactivityTimeout';
import { validateAudioFile } from './utils/audioValidator';
import { formatFileSize } from './utils/formatters';
import { SESSION_TIMEOUT_MS } from './utils/constants';
import toast, { Toaster } from 'react-hot-toast';
import './index.css';

function App() {
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [question, setQuestion] = useState('');
  const [connectionState, setConnectionState] = useState<string>('disconnected');

  const { session, createSession, updateActivity, markInactive } = useSessionStore();
  const { messages, addMessage, setProcessing, isProcessing } = useChatStore();

  const { resetTimeout } = useInactivityTimeout({
    timeoutMs: SESSION_TIMEOUT_MS,
    onTimeout: () => {
      if (session) {
        toast.error('Session expired due to inactivity');
        markInactive();
        websocketService.disconnect();
      }
    },
    enabled: session !== null,
  });

  useEffect(() => {
    const unsubscribe = websocketService.onStateChange(setConnectionState);
    return unsubscribe;
  }, []);

  useEffect(() => {
    if (!session) return;

    const unsubscribeTranscript = websocketService.on('transcript.complete', (msg: any) => {
      toast.success('Transcript ready!');
      console.log('Transcript:', msg.data.transcript);
    });

    const unsubscribeResponse = websocketService.on('question.response', (msg: any) => {
      addMessage({
        type: 'answer',
        content: msg.data.answer,
      });
      setProcessing(false);
    });

    const unsubscribeError = websocketService.on('error', (msg: any) => {
      toast.error(`Error: ${msg.data.message}`);
      setProcessing(false);
    });

    return () => {
      unsubscribeTranscript();
      unsubscribeResponse();
      unsubscribeError();
    };
  }, [session, addMessage, setProcessing]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      const validation = validateAudioFile(selectedFile);
      if (!validation.isValid) {
        toast.error(validation.error || 'Invalid file');
        return;
      }
      setFile(selectedFile);
      if (validation.warnings) {
        validation.warnings.forEach(warning => toast(warning, { icon: '⚠️' }));
      }
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    try {
      setIsUploading(true);
      toast.loading('Uploading audio...', { id: 'upload' });

      const fileKey = await s3Service.uploadAudio(file);
      toast.success('Audio uploaded!', { id: 'upload' });

      createSession(fileKey, {
        fileName: file.name,
        fileSize: file.size,
        mimeType: file.type,
      });

      if (session?.sessionId) {
        await websocketService.connect(session.sessionId);
        toast.success('Connected to server');
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Upload failed';
      toast.error(message, { id: 'upload' });
    } finally {
      setIsUploading(false);
    }
  };

  const handleAskQuestion = () => {
    if (!question.trim() || !session) return;

    addMessage({
      type: 'question',
      content: question,
    });

    websocketService.send({
      type: 'question.ask',
      sessionId: session.sessionId,
      data: { question },
    });

    setProcessing(true);
    setQuestion('');
    updateActivity();
    resetTimeout();
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-8">
      <Toaster position="top-right" />

      <div className="max-w-4xl mx-auto">
        <header className="text-center mb-12">
          <h1 className="text-5xl font-bold text-indigo-900 mb-2">
            SynapScribe
          </h1>
          <p className="text-lg text-gray-600">
            AI-powered lecture transcription and Q&A
          </p>
          <div className="mt-4 inline-flex items-center gap-2 px-4 py-2 bg-white rounded-full shadow">
            <div className={`w-2 h-2 rounded-full ${
              connectionState === 'connected' ? 'bg-green-500' :
              connectionState === 'connecting' ? 'bg-yellow-500' : 'bg-gray-400'
            }`} />
            <span className="text-sm text-gray-700 capitalize">{connectionState}</span>
          </div>
        </header>

        {!session ? (
          <div className="bg-white rounded-2xl shadow-xl p-8">
            <h2 className="text-2xl font-bold text-gray-800 mb-6">
              Upload Your Lecture
            </h2>

            <div className="space-y-4">
              <div className="border-2 border-dashed border-gray-300 rounded-xl p-8 text-center hover:border-indigo-500 transition-colors">
                <input
                  type="file"
                  accept="audio/*,video/*"
                  onChange={handleFileChange}
                  className="hidden"
                  id="file-input"
                />
                <label
                  htmlFor="file-input"
                  className="cursor-pointer block"
                >
                  <div className="text-6xl mb-4">🎵</div>
                  <p className="text-lg text-gray-700 mb-2">
                    Click to select audio file
                  </p>
                  <p className="text-sm text-gray-500">
                    Supports: MP3, WAV, M4A, MP4, OGG, FLAC, WEBM
                  </p>
                </label>
              </div>

              {file && (
                <div className="bg-indigo-50 rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-gray-800">{file.name}</p>
                      <p className="text-sm text-gray-600">{formatFileSize(file.size)}</p>
                    </div>
                    <button
                      onClick={handleUpload}
                      disabled={isUploading}
                      className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      {isUploading ? 'Uploading...' : 'Upload & Start'}
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="bg-white rounded-2xl shadow-xl p-8">
            <div className="mb-6 pb-6 border-b">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-2xl font-bold text-gray-800">Session Active</h2>
                  <p className="text-sm text-gray-600 mt-1">
                    File: {session.metadata?.fileName}
                  </p>
                </div>
                <div className="px-4 py-2 bg-green-100 text-green-800 rounded-lg text-sm font-medium">
                  Connected
                </div>
              </div>
            </div>

            <div className="mb-6 space-y-4 max-h-96 overflow-y-auto">
              {messages.length === 0 ? (
                <div className="text-center py-12 text-gray-400">
                  <p className="text-lg">No messages yet</p>
                  <p className="text-sm">Ask a question about your lecture</p>
                </div>
              ) : (
                messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`flex ${msg.type === 'question' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-md px-4 py-3 rounded-2xl ${
                        msg.type === 'question'
                          ? 'bg-indigo-600 text-white'
                          : 'bg-gray-100 text-gray-800'
                      }`}
                    >
                      <p>{msg.content}</p>
                    </div>
                  </div>
                ))
              )}
            </div>

            <div className="flex gap-2">
              <input
                type="text"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleAskQuestion()}
                placeholder="Ask a question about your lecture..."
                disabled={isProcessing}
                className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:opacity-50"
              />
              <button
                onClick={handleAskQuestion}
                disabled={isProcessing || !question.trim()}
                className="px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
              >
                {isProcessing ? 'Processing...' : 'Ask'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
