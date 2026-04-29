/**
 * Hook test for useSchedulingChat — verifies session_id round-trip (Bug 4 FE).
 *
 * The first POST returns a session_id; the hook must echo it back on the
 * second POST. Without this, the backend has no way to thread multi-turn
 * conversations and the chat session table fragments per request.
 */

import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';

import { apiClient } from '@/core/api/client';

import { useSchedulingChat } from './useSchedulingChat';

vi.mock('@/core/api/client', () => ({
  apiClient: {
    post: vi.fn(),
  },
}));

const mockedPost = vi.mocked(apiClient.post);

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

afterEach(() => {
  mockedPost.mockReset();
});

describe('useSchedulingChat', () => {
  it('echoes the session_id from the first response on the second mutate', async () => {
    mockedPost.mockResolvedValueOnce({
      data: {
        response: 'first',
        session_id: 'abc-123',
        schedule_changes: null,
        clarifying_questions: null,
        change_request_id: null,
        criteria_used: null,
        schedule_summary: null,
      },
    } as never);
    mockedPost.mockResolvedValueOnce({
      data: {
        response: 'second',
        session_id: 'abc-123',
        schedule_changes: null,
        clarifying_questions: null,
        change_request_id: null,
        criteria_used: null,
        schedule_summary: null,
      },
    } as never);

    const { result } = renderHook(() => useSchedulingChat(), { wrapper });

    act(() => {
      result.current.sendMessage('hi');
    });
    await waitFor(() => {
      expect(result.current.sessionId).toBe('abc-123');
    });

    act(() => {
      result.current.sendMessage('and again');
    });
    await waitFor(() => {
      expect(mockedPost).toHaveBeenCalledTimes(2);
    });

    expect(mockedPost.mock.calls[0][1]).toEqual({
      message: 'hi',
      session_id: undefined,
    });
    expect(mockedPost.mock.calls[1][1]).toEqual({
      message: 'and again',
      session_id: 'abc-123',
    });
  });

  it('appends both user and assistant messages to local history', async () => {
    mockedPost.mockResolvedValueOnce({
      data: {
        response: 'hello back',
        session_id: 'sess-1',
        schedule_changes: null,
        clarifying_questions: null,
        change_request_id: null,
        criteria_used: null,
        schedule_summary: null,
      },
    } as never);

    const { result } = renderHook(() => useSchedulingChat(), { wrapper });

    act(() => {
      result.current.sendMessage('hello');
    });

    await waitFor(() => {
      expect(result.current.messages).toHaveLength(2);
    });
    expect(result.current.messages[0]).toMatchObject({
      role: 'user',
      content: 'hello',
    });
    expect(result.current.messages[1]).toMatchObject({
      role: 'assistant',
      content: 'hello back',
    });
  });

  it('keeps the previous sessionId when the next response omits one', async () => {
    mockedPost.mockResolvedValueOnce({
      data: {
        response: 'first',
        session_id: 'first-session',
        schedule_changes: null,
        clarifying_questions: null,
        change_request_id: null,
        criteria_used: null,
        schedule_summary: null,
      },
    } as never);
    mockedPost.mockResolvedValueOnce({
      data: {
        response: 'second',
        session_id: null,
        schedule_changes: null,
        clarifying_questions: null,
        change_request_id: null,
        criteria_used: null,
        schedule_summary: null,
      },
    } as never);

    const { result } = renderHook(() => useSchedulingChat(), { wrapper });

    act(() => {
      result.current.sendMessage('one');
    });
    await waitFor(() => {
      expect(result.current.sessionId).toBe('first-session');
    });

    act(() => {
      result.current.sendMessage('two');
    });
    await waitFor(() => {
      expect(mockedPost).toHaveBeenCalledTimes(2);
    });

    expect(result.current.sessionId).toBe('first-session');
  });
});
