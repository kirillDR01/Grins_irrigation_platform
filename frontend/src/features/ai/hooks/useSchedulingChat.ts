/**
 * TanStack Query hooks for AI scheduling chat.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/core/api/client';

// ── Types ──────────────────────────────────────────────────────────────

export interface ScheduleChange {
  change_type: string;
  job_id: string;
  staff_id: string;
  old_slot: string | null;
  new_slot: string | null;
  explanation: string;
}

export interface SchedulingChatRequest {
  message: string;
  session_id?: string;
}

export interface SchedulingChatResponse {
  response: string;
  session_id: string;
  schedule_changes: ScheduleChange[] | null;
  clarifying_questions: string[] | null;
  change_request_id: string | null;
  criteria_used: number[];
}

export interface ChatSessionMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  criteria_used?: number[];
  schedule_changes?: ScheduleChange[] | null;
  clarifying_questions?: string[] | null;
}

export interface ChatSession {
  id: string;
  user_id: string;
  user_role: string;
  messages: ChatSessionMessage[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// ── Query key factory ──────────────────────────────────────────────────

export const schedulingChatKeys = {
  all: ['scheduling-chat'] as const,
  sessions: () => [...schedulingChatKeys.all, 'sessions'] as const,
  session: (sessionId: string) =>
    [...schedulingChatKeys.sessions(), sessionId] as const,
};

// ── Hooks ──────────────────────────────────────────────────────────────

/** POST /api/v1/ai-scheduling/chat — send a scheduling chat message. */
export function useSchedulingChat() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (request: SchedulingChatRequest) => {
      const response = await apiClient.post<SchedulingChatResponse>(
        '/ai-scheduling/chat',
        request
      );
      return response.data;
    },
    onSuccess: (data) => {
      if (data.session_id) {
        qc.invalidateQueries({
          queryKey: schedulingChatKeys.session(data.session_id),
        });
      }
    },
  });
}

/** GET /api/v1/ai-scheduling/chat/history/{sessionId} — fetch chat session history. */
export function useChatHistory(sessionId: string | null) {
  return useQuery({
    queryKey: schedulingChatKeys.session(sessionId ?? ''),
    queryFn: async () => {
      const response = await apiClient.get<ChatSession>(
        `/ai-scheduling/chat/history/${sessionId}`
      );
      return response.data;
    },
    enabled: !!sessionId,
    staleTime: 30_000,
  });
}
