/**
 * Notes hooks for the unified notes timeline.
 *
 * Provides `useNotes` (query) and `useCreateNote` (mutation) hooks
 * that work with the notes API endpoints for any subject type.
 *
 * Validates: april-16th-fixes-enhancements Requirement 4
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/core/api';

/** Note response from the API */
export interface NoteEntry {
  id: string;
  subject_type: 'lead' | 'sales_entry' | 'customer' | 'appointment';
  subject_id: string;
  author_id: string;
  author_name: string;
  body: string;
  origin_lead_id: string | null;
  is_system: boolean;
  created_at: string;
  updated_at: string;
  stage_tag: string;
}

/** Query key factory for notes */
export const noteKeys = {
  all: ['notes'] as const,
  bySubject: (subjectType: string, subjectId: string) =>
    [...noteKeys.all, subjectType, subjectId] as const,
};

/** Map subject_type to the API path prefix */
const SUBJECT_PATH_MAP: Record<string, string> = {
  lead: 'leads',
  sales_entry: 'sales',
  customer: 'customers',
  appointment: 'appointments',
};

/**
 * Fetch the notes timeline for a given subject.
 * Returns notes newest-first with author, timestamp, body, and stage tag.
 */
export function useNotes(subjectType: string, subjectId: string) {
  const pathPrefix = SUBJECT_PATH_MAP[subjectType] ?? subjectType;

  return useQuery({
    queryKey: noteKeys.bySubject(subjectType, subjectId),
    queryFn: async (): Promise<NoteEntry[]> => {
      const response = await apiClient.get<NoteEntry[]>(
        `/${pathPrefix}/${subjectId}/notes`
      );
      return response.data;
    },
    enabled: !!subjectId,
  });
}

/**
 * Create a new note on a subject.
 * Invalidates the notes query for that subject on success.
 */
export function useCreateNote(subjectType: string, subjectId: string) {
  const queryClient = useQueryClient();
  const pathPrefix = SUBJECT_PATH_MAP[subjectType] ?? subjectType;

  return useMutation({
    mutationFn: async (body: string): Promise<NoteEntry> => {
      const response = await apiClient.post<NoteEntry>(
        `/${pathPrefix}/${subjectId}/notes`,
        { body }
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: noteKeys.bySubject(subjectType, subjectId),
      });
    },
  });
}
