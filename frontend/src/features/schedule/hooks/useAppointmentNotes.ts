/**
 * TanStack Query hooks for appointment notes.
 * Canonical source — NotesPanel imports from here.
 * Requirements: 8.1, 8.2, 8.3, 8.4
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/core/api/client';

// ── Types ──

interface NoteAuthor {
  id: string;
  name: string;
  role: string;
}

export interface AppointmentNotesResponse {
  appointment_id: string;
  body: string;
  updated_at: string;
  updated_by: NoteAuthor | null;
}

// ── Query key factory ──

export const appointmentNoteKeys = {
  all: ['appointment-notes'] as const,
  detail: (appointmentId: string) =>
    [...appointmentNoteKeys.all, appointmentId] as const,
};

// ── Hooks ──

/**
 * Fetch notes for an appointment.
 * Returns default empty body when no notes exist (404 or missing).
 * Req 8.1, 8.4
 */
export function useAppointmentNotes(appointmentId: string) {
  return useQuery({
    queryKey: appointmentNoteKeys.detail(appointmentId),
    queryFn: async (): Promise<AppointmentNotesResponse> => {
      try {
        const { data } = await apiClient.get<AppointmentNotesResponse>(
          `/appointments/${appointmentId}/notes`,
        );
        return data;
      } catch {
        // Return default empty notes on error / 404
        return {
          appointment_id: appointmentId,
          body: '',
          updated_at: new Date().toISOString(),
          updated_by: null,
        };
      }
    },
    enabled: !!appointmentId,
  });
}

/**
 * Mutation to save (upsert) appointment notes.
 * Optimistic update on the notes query cache; invalidate on success; revert on failure.
 * Req 8.2, 8.3
 */
export function useSaveAppointmentNotes() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      appointmentId,
      body,
    }: {
      appointmentId: string;
      body: string;
    }): Promise<AppointmentNotesResponse> => {
      const { data } = await apiClient.patch<AppointmentNotesResponse>(
        `/appointments/${appointmentId}/notes`,
        { body },
      );
      return data;
    },

    onMutate: async ({ appointmentId, body }) => {
      // Cancel any outgoing refetches so they don't overwrite our optimistic update
      await queryClient.cancelQueries({
        queryKey: appointmentNoteKeys.detail(appointmentId),
      });

      // Snapshot the previous value
      const previousNotes = queryClient.getQueryData<AppointmentNotesResponse>(
        appointmentNoteKeys.detail(appointmentId),
      );

      // Optimistically update to the new value
      queryClient.setQueryData<AppointmentNotesResponse>(
        appointmentNoteKeys.detail(appointmentId),
        (old) =>
          old
            ? { ...old, body, updated_at: new Date().toISOString() }
            : {
                appointment_id: appointmentId,
                body,
                updated_at: new Date().toISOString(),
                updated_by: null,
              },
      );

      return { previousNotes };
    },

    onError: (_error, variables, context) => {
      // Revert to the previous value on failure
      if (context?.previousNotes) {
        queryClient.setQueryData(
          appointmentNoteKeys.detail(variables.appointmentId),
          context.previousNotes,
        );
      }
    },

    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: appointmentNoteKeys.detail(variables.appointmentId),
      });
    },
  });
}
