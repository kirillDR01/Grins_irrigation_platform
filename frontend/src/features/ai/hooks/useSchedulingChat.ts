/**
 * useSchedulingChat — TanStack Query mutation hook for AI scheduling chat.
 * Manages session state and message history locally.
 */

import { useState, useCallback } from 'react';
import { useMutation } from '@tanstack/react-query';
import { apiClient } from '@/core/api/client';
import type { ChatRequest, ChatResponse, ScheduleChange } from '../types/aiScheduling';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  userName?: string;
  criteriaUsed?: Array<{ number: number; name: string }>;
  clarifyingQuestions?: string[];
  scheduleChanges?: ScheduleChange[];
  scheduleSummary?: string | null;
  changeRequestId?: string | null;
}

export const schedulingChatKeys = {
  all: ['scheduling-chat'] as const,
  session: (id: string) => [...schedulingChatKeys.all, 'session', id] as const,
};

export function useSchedulingChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessionId, setSessionId] = useState<string | undefined>(undefined);

  const mutation = useMutation({
    mutationFn: async (request: ChatRequest) => {
      const response = await apiClient.post<ChatResponse>(
        '/ai-scheduling/chat',
        request
      );
      return response.data;
    },
    onSuccess: (data) => {
      setSessionId(data.session_id);
      const assistantMsg: ChatMessage = {
        id: `${Date.now()}-assistant`,
        role: 'assistant',
        content: data.response,
        criteriaUsed: data.criteria_used,
        clarifyingQuestions: data.clarifying_questions,
        scheduleChanges: data.schedule_changes,
        scheduleSummary: data.schedule_summary,
        changeRequestId: data.change_request_id,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    },
  });

  const sendMessage = useCallback(
    (text: string) => {
      const userMsg: ChatMessage = {
        id: `${Date.now()}-user`,
        role: 'user',
        content: text,
      };
      setMessages((prev) => [...prev, userMsg]);
      mutation.mutate({ message: text, session_id: sessionId });
    },
    [mutation, sessionId]
  );

  return {
    messages,
    sendMessage,
    isLoading: mutation.isPending,
    sessionId,
  };
}
