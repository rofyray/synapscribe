import { create } from 'zustand';
import type { Session } from '../types/session.types';
import { v4 as uuidv4 } from 'uuid';

interface SessionStore {
  session: Session | null;
  isActive: boolean;
  lastActivity: number;

  createSession: (audioFileKey: string, metadata: Session['metadata']) => void;
  updateSession: (updates: Partial<Session>) => void;
  endSession: () => void;
  updateActivity: () => void;
  markInactive: () => void;
}

export const useSessionStore = create<SessionStore>((set) => ({
  session: null,
  isActive: false,
  lastActivity: Date.now(),

  createSession: (audioFileKey, metadata) => {
    const session: Session = {
      sessionId: uuidv4(),
      userId: 'anonymous',
      audioFileKey,
      createdAt: new Date().toISOString(),
      lastActivityAt: new Date().toISOString(),
      status: 'active',
      metadata,
    };

    set({ session, isActive: true, lastActivity: Date.now() });
  },

  updateSession: (updates) => {
    set((state) => ({
      session: state.session ? { ...state.session, ...updates } : null,
    }));
  },

  endSession: () => {
    set({ session: null, isActive: false });
  },

  updateActivity: () => {
    set((state) => ({
      lastActivity: Date.now(),
      session: state.session
        ? { ...state.session, lastActivityAt: new Date().toISOString() }
        : null,
    }));
  },

  markInactive: () => {
    set((state) => ({
      isActive: false,
      session: state.session
        ? { ...state.session, status: 'inactive' }
        : null,
    }));
  },
}));
