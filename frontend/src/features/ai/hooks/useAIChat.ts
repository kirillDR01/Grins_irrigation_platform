/**
 * useAIChat hook
 * 
 * Manages AI chat state, session history, and streaming responses
 */

import { useState, useCallback } from 'react';
import { aiApi } from '../api/aiApi';
import type { AIChatRequest, AIChatResponse } from '../types';

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export interface UseAIChatReturn {
  messages: ChatMessage[];
  isLoading: boolean;
  error: string | null;
  sessionId: string | null;
  messageCount: number;
  sendMessage: (message: string) => Promise<void>;
  clearChat: () => void;
}

const MAX_MESSAGES = 50;

export function useAIChat(): UseAIChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);

  const sendMessage = useCallback(async (message: string) => {
    if (!message.trim()) return;

    setIsLoading(true);
    setError(null);

    // Add user message
    const userMessage: ChatMessage = {
      role: 'user',
      content: message,
      timestamp: new Date(),
    };

    setMessages(prev => {
      const updated = [...prev, userMessage];
      // Enforce 50 message limit
      return updated.slice(-MAX_MESSAGES);
    });

    try {
      const request: AIChatRequest = {
        message,
        session_id: sessionId || undefined,
      };

      const response: AIChatResponse = await aiApi.chat(request);

      // Update session ID
      if (response.session_id) {
        setSessionId(response.session_id);
      }

      // Add assistant message
      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: response.message,
        timestamp: new Date(),
      };

      setMessages(prev => {
        const updated = [...prev, assistantMessage];
        // Enforce 50 message limit
        return updated.slice(-MAX_MESSAGES);
      });
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to send message';
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, [sessionId]);

  const clearChat = useCallback(() => {
    setMessages([]);
    setSessionId(null);
    setError(null);
  }, []);

  return {
    messages,
    isLoading,
    error,
    sessionId,
    messageCount: messages.length,
    sendMessage,
    clearChat,
  };
}
