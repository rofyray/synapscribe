import { create } from 'zustand';

export interface ChatMessage {
  id: string;
  type: 'question' | 'answer';
  content: string;
  timestamp: number;
  isStreaming?: boolean;
}

interface ChatStore {
  messages: ChatMessage[];
  isProcessing: boolean;

  addMessage: (message: Omit<ChatMessage, 'id' | 'timestamp'>) => void;
  updateMessage: (id: string, updates: Partial<ChatMessage>) => void;
  clearMessages: () => void;
  setProcessing: (isProcessing: boolean) => void;
}

export const useChatStore = create<ChatStore>((set) => ({
  messages: [],
  isProcessing: false,

  addMessage: (message) => {
    const newMessage: ChatMessage = {
      ...message,
      id: crypto.randomUUID(),
      timestamp: Date.now(),
    };

    set((state) => ({
      messages: [...state.messages, newMessage],
    }));
  },

  updateMessage: (id, updates) => {
    set((state) => ({
      messages: state.messages.map((msg) =>
        msg.id === id ? { ...msg, ...updates } : msg
      ),
    }));
  },

  clearMessages: () => {
    set({ messages: [] });
  },

  setProcessing: (isProcessing) => {
    set({ isProcessing });
  },
}));
