/**
 * useCommunications hook
 * 
 * Manages communications queue state, bulk actions, and filtering
 */

import { useState, useCallback, useEffect } from 'react';
import { getCommunicationsQueue, sendBulkSMS, deleteCommunication } from '../api/aiApi';
import type { CommunicationsQueueItem } from '../types';

export interface UseCommunicationsParams {
  search?: string;
  messageType?: string;
}

export interface UseCommunicationsReturn {
  queue: CommunicationsQueueItem[] | null;
  isLoading: boolean;
  error: string | null;
  isSending: boolean;
  sendAll: () => Promise<void>;
  pauseAll: () => Promise<void>;
  retry: (messageId: string) => Promise<void>;
  refresh: () => Promise<void>;
}

export function useCommunications(params?: UseCommunicationsParams): UseCommunicationsReturn {
  const [queue, setQueue] = useState<CommunicationsQueueItem[] | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSending, setIsSending] = useState(false);

  const fetchQueue = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await getCommunicationsQueue({
        message_type: params?.messageType !== 'all' ? params?.messageType : undefined,
      });
      
      // Filter by search query if provided
      let items = response.items as CommunicationsQueueItem[];
      if (params?.search) {
        const searchLower = params.search.toLowerCase();
        items = items.filter(item => 
          item.recipient_phone.toLowerCase().includes(searchLower) ||
          item.message_content.toLowerCase().includes(searchLower)
        );
      }
      
      setQueue(items);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch communications queue';
      setError(errorMessage);
      setQueue(null);
    } finally {
      setIsLoading(false);
    }
  }, [params?.search, params?.messageType]);

  useEffect(() => {
    fetchQueue();
  }, [fetchQueue]);

  const sendAll = useCallback(async () => {
    if (!queue) return;

    setIsSending(true);
    setError(null);

    try {
      const pendingIds = queue
        .filter(m => m.delivery_status === 'pending')
        .map(m => m.id);

      if (pendingIds.length > 0) {
        await sendBulkSMS({ message_ids: pendingIds });
        await fetchQueue(); // Refresh queue after sending
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to send messages';
      setError(errorMessage);
    } finally {
      setIsSending(false);
    }
  }, [queue, fetchQueue]);

  const pauseAll = useCallback(async () => {
    if (!queue) return;

    setIsLoading(true);
    setError(null);

    try {
      const scheduledIds = queue
        .filter(m => m.delivery_status === 'scheduled')
        .map(m => m.id);

      // Delete scheduled messages to pause them
      await Promise.all(scheduledIds.map(id => deleteCommunication(id)));
      await fetchQueue(); // Refresh queue after pausing
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to pause messages';
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, [queue, fetchQueue]);

  const retry = useCallback(async (messageId: string) => {
    setIsLoading(true);
    setError(null);

    try {
      await sendBulkSMS({ message_ids: [messageId] });
      await fetchQueue(); // Refresh queue after retry
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to retry message';
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, [fetchQueue]);

  const refresh = useCallback(async () => {
    await fetchQueue();
  }, [fetchQueue]);

  return {
    queue,
    isLoading,
    error,
    isSending,
    sendAll,
    pauseAll,
    retry,
    refresh,
  };
}
