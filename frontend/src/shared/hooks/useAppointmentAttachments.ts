/**
 * Appointment attachment hooks.
 *
 * Provides hooks for listing, uploading, and deleting appointment attachments.
 * Reuses the presign pipeline pattern from AttachmentPanel.
 *
 * Validates: april-16th-fixes-enhancements Requirement 10C
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/core/api';

/** Attachment response from the API */
export interface AppointmentAttachment {
  id: string;
  appointment_id: string;
  appointment_type: string;
  file_key: string;
  file_name: string;
  file_size: number;
  content_type: string;
  uploaded_by: string;
  created_at: string;
  download_url?: string;
}

/** Query key factory for appointment attachments */
export const appointmentAttachmentKeys = {
  all: ['appointment-attachments'] as const,
  byAppointment: (appointmentId: string) =>
    [...appointmentAttachmentKeys.all, appointmentId] as const,
};

const MAX_FILE_SIZE = 25 * 1024 * 1024; // 25 MB

/**
 * List attachments for an appointment.
 */
export function useAppointmentAttachments(appointmentId: string) {
  return useQuery({
    queryKey: appointmentAttachmentKeys.byAppointment(appointmentId),
    queryFn: async (): Promise<AppointmentAttachment[]> => {
      const response = await apiClient.get<AppointmentAttachment[]>(
        `/appointments/${appointmentId}/attachments`
      );
      return response.data;
    },
    enabled: !!appointmentId,
  });
}

/**
 * Upload a file attachment to an appointment.
 */
export function useUploadAppointmentAttachment(appointmentId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (file: File): Promise<AppointmentAttachment> => {
      if (file.size > MAX_FILE_SIZE) {
        throw new Error('File size exceeds 25 MB limit');
      }
      const formData = new FormData();
      formData.append('file', file);
      const response = await apiClient.post<AppointmentAttachment>(
        `/appointments/${appointmentId}/attachments`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: appointmentAttachmentKeys.byAppointment(appointmentId),
      });
    },
  });
}

/**
 * Delete an attachment from an appointment.
 */
export function useDeleteAppointmentAttachment(appointmentId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (attachmentId: string): Promise<void> => {
      await apiClient.delete(
        `/appointments/${appointmentId}/attachments/${attachmentId}`
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: appointmentAttachmentKeys.byAppointment(appointmentId),
      });
    },
  });
}
