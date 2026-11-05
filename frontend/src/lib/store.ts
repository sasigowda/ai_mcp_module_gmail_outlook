"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { User, Conversation, MCPServer, StreamEvent } from "@/types";

interface AuthState {
  user: User | null;
  accessToken: string | null;
  setUser: (user: User | null) => void;
  setTokens: (access: string, refresh: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      setUser: (user) => set({ user }),
      setTokens: (access, refresh) => {
        localStorage.setItem("refresh_token", refresh);
        set({ accessToken: access });
      },
      logout: () => {
        localStorage.removeItem("refresh_token");
        localStorage.removeItem("access_token");
        set({ user: null, accessToken: null });
      },
    }),
    { name: "auth-store", partialize: (state) => ({ user: state.user, accessToken: state.accessToken }) }
  )
);

interface ChatState {
  conversations: Conversation[];
  activeConversationId: string | null;
  messages: Record<string, ChatMessageLocal[]>;
  isStreaming: boolean;
  streamBuffer: string;
  setConversations: (convs: Conversation[]) => void;
  setActiveConversation: (id: string | null) => void;
  addMessage: (convId: string, msg: ChatMessageLocal) => void;
  appendStream: (convId: string, text: string) => void;
  finalizeStream: (convId: string, messageId: string) => void;
  migrateMessages: (fromId: string, toId: string) => void;
  setStreaming: (v: boolean) => void;
  addConversation: (conv: Conversation) => void;
}

export interface ChatMessageLocal {
  id: string;
  role: "user" | "assistant";
  content: string;
  tool_calls?: StreamEvent[];
  isStreaming?: boolean;
}

export const useChatStore = create<ChatState>()((set, get) => ({
  conversations: [],
  activeConversationId: null,
  messages: {},
  isStreaming: false,
  streamBuffer: "",
  setConversations: (conversations) => set({ conversations }),
  setActiveConversation: (id) => set({ activeConversationId: id }),
  addMessage: (convId, msg) =>
    set((state) => ({
      messages: {
        ...state.messages,
        [convId]: [...(state.messages[convId] || []), msg],
      },
    })),
  appendStream: (convId, text) =>
    set((state) => {
      const msgs = [...(state.messages[convId] || [])];
      const last = msgs[msgs.length - 1];
      if (last?.isStreaming) {
        msgs[msgs.length - 1] = { ...last, content: last.content + text };
      } else {
        msgs.push({ id: "streaming", role: "assistant", content: text, isStreaming: true });
      }
      return { messages: { ...state.messages, [convId]: msgs } };
    }),
  finalizeStream: (convId, messageId) =>
    set((state) => {
      const msgs = (state.messages[convId] || []).map((m) =>
        m.isStreaming ? { ...m, id: messageId, isStreaming: false } : m
      );
      return { messages: { ...state.messages, [convId]: msgs }, isStreaming: false };
    }),
  migrateMessages: (fromId, toId) =>
    set((state) => {
      const moved = state.messages[fromId] || [];
      const existing = state.messages[toId] || [];
      const merged = [...moved, ...existing];
      const next = { ...state.messages, [toId]: merged };
      delete next[fromId];
      return { messages: next };
    }),
  setStreaming: (v) => set({ isStreaming: v }),
  addConversation: (conv) =>
    set((state) => ({ conversations: [conv, ...state.conversations] })),
}));

interface MCPState {
  servers: MCPServer[];
  setServers: (servers: MCPServer[]) => void;
  updateServer: (id: string, updates: Partial<MCPServer>) => void;
  removeServer: (id: string) => void;
  addServer: (server: MCPServer) => void;
}

export const useMCPStore = create<MCPState>()((set) => ({
  servers: [],
  setServers: (servers) => set({ servers }),
  updateServer: (id, updates) =>
    set((state) => ({
      servers: state.servers.map((s) => (s.id === id ? { ...s, ...updates } : s)),
    })),
  removeServer: (id) =>
    set((state) => ({ servers: state.servers.filter((s) => s.id !== id) })),
  addServer: (server) =>
    set((state) => ({ servers: [...state.servers, server] })),
}));
