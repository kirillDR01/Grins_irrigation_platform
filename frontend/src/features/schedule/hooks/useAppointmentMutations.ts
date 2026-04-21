/**
 * TanStack Query mutation hooks for appointments.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { appointmentApi } from '../api/appointmentApi';
import { appointmentKeys } from './useAppointments';
import type {
  AppointmentCreate,
  AppointmentUpdate,
  CollectPaymentRequest,
  CreateEstimateFromAppointmentRequest,
} from '../types';

/**
 * Hook to create a new appointment.
 */
export function useCreateAppointment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: AppointmentCreate) => appointmentApi.create(data),
    onSuccess: () => {
      // Invalidate all appointment lists and schedules
      queryClient.invalidateQueries({ queryKey: appointmentKeys.all });
      // Invalidate jobs ready to schedule (job is now assigned)
      queryClient.invalidateQueries({ queryKey: ['jobs-ready-to-schedule'] });
      // Invalidate dashboard today schedule
      queryClient.invalidateQueries({ queryKey: ['dashboard', 'today-schedule'] });
    },
  });
}

/**
 * Hook to update an existing appointment.
 */
export function useUpdateAppointment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: AppointmentUpdate }) =>
      appointmentApi.update(id, data),
    onSuccess: (_, variables) => {
      // Invalidate the specific appointment and all lists
      queryClient.invalidateQueries({
        queryKey: appointmentKeys.detail(variables.id),
      });
      queryClient.invalidateQueries({ queryKey: appointmentKeys.lists() });
      // Also invalidate daily and weekly schedules
      queryClient.invalidateQueries({
        queryKey: [...appointmentKeys.all, 'daily'],
      });
      queryClient.invalidateQueries({
        queryKey: [...appointmentKeys.all, 'weekly'],
      });
      queryClient.invalidateQueries({
        queryKey: [...appointmentKeys.all, 'staffDaily'],
      });
    },
  });
}

/**
 * Hook to cancel an appointment. Accepts ``{ id, notifyCustomer }`` so the
 * admin can opt out of the cancellation SMS via the confirmation dialog.
 */
export function useCancelAppointment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      id,
      notifyCustomer = true,
    }: {
      id: string;
      notifyCustomer?: boolean;
    }) => appointmentApi.cancel(id, notifyCustomer),
    onSuccess: (_, { id }) => {
      // Invalidate the specific appointment and all lists
      queryClient.invalidateQueries({ queryKey: appointmentKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: appointmentKeys.lists() });
      // Also invalidate daily and weekly schedules
      queryClient.invalidateQueries({
        queryKey: [...appointmentKeys.all, 'daily'],
      });
      queryClient.invalidateQueries({
        queryKey: [...appointmentKeys.all, 'weekly'],
      });
      queryClient.invalidateQueries({
        queryKey: [...appointmentKeys.all, 'staffDaily'],
      });
      queryClient.invalidateQueries({
        queryKey: appointmentKeys.timeline(id),
      });
    },
  });
}

/**
 * Hook to confirm an appointment.
 */
export function useConfirmAppointment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => appointmentApi.confirm(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: appointmentKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: appointmentKeys.lists() });
      queryClient.invalidateQueries({
        queryKey: [...appointmentKeys.all, 'daily'],
      });
      queryClient.invalidateQueries({
        queryKey: [...appointmentKeys.all, 'weekly'],
      });
      queryClient.invalidateQueries({
        queryKey: appointmentKeys.timeline(id),
      });
    },
  });
}

/**
 * Hook to mark appointment as arrived (in progress).
 */
export function useMarkAppointmentArrived() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => appointmentApi.markArrived(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: appointmentKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: appointmentKeys.lists() });
      queryClient.invalidateQueries({
        queryKey: [...appointmentKeys.all, 'daily'],
      });
    },
  });
}

/**
 * Hook to mark appointment as completed.
 */
export function useMarkAppointmentCompleted() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => appointmentApi.markCompleted(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: appointmentKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: appointmentKeys.lists() });
      queryClient.invalidateQueries({
        queryKey: [...appointmentKeys.all, 'daily'],
      });
    },
  });
}

/**
 * Hook to mark appointment as no show.
 */
export function useMarkAppointmentNoShow() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => appointmentApi.markNoShow(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: appointmentKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: appointmentKeys.lists() });
      queryClient.invalidateQueries({
        queryKey: [...appointmentKeys.all, 'daily'],
      });
    },
  });
}

/**
 * Hook to mark appointment as en_route (Req 35).
 */
export function useMarkAppointmentEnRoute() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => appointmentApi.markEnRoute(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: appointmentKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: appointmentKeys.lists() });
      queryClient.invalidateQueries({
        queryKey: [...appointmentKeys.all, 'daily'],
      });
    },
  });
}

/**
 * Hook to collect payment on-site (Req 30).
 */
export function useCollectPayment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: CollectPaymentRequest }) =>
      appointmentApi.collectPayment(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: appointmentKeys.all });
    },
  });
}

/**
 * Hook to create invoice from appointment (Req 31).
 */
export function useCreateInvoiceFromAppointment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => appointmentApi.createInvoice(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: appointmentKeys.all });
    },
  });
}

/**
 * Hook to create estimate from appointment (Req 32).
 */
export function useCreateEstimateFromAppointment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      id,
      data,
    }: {
      id: string;
      data: CreateEstimateFromAppointmentRequest;
    }) => appointmentApi.createEstimate(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: appointmentKeys.all });
    },
  });
}

/**
 * Hook to upload photos for an appointment (Req 33).
 */
export function useUploadAppointmentPhotos() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, files }: { id: string; files: File[] }) =>
      appointmentApi.uploadPhotos(id, files),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: appointmentKeys.all });
    },
  });
}

/**
 * Hook to request Google review (Req 34).
 */
export function useRequestReview() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => appointmentApi.requestReview(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: appointmentKeys.all });
    },
  });
}

/**
 * Hook to send confirmation SMS for a draft appointment (Req 8.4).
 */
export function useSendConfirmation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => appointmentApi.sendConfirmation(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: appointmentKeys.all });
    },
  });
}

/**
 * Hook to bulk send confirmation SMS for draft appointments (Req 8.6).
 */
export function useBulkSendConfirmations() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: { appointment_ids?: string[]; date_from?: string; date_to?: string }) =>
      appointmentApi.bulkSendConfirmations(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: appointmentKeys.all });
    },
  });
}

/**
 * Hook to reschedule an appointment from a customer R-request (bughunt H-6).
 *
 * POSTs to ``/appointments/{id}/reschedule-from-request`` which moves the
 * appointment to the new slot, resets status to SCHEDULED, and fires a
 * fresh Y/R/C confirmation SMS so the customer must re-confirm.
 */
export function useRescheduleFromRequest() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      id,
      new_scheduled_at,
    }: {
      id: string;
      new_scheduled_at: string;
    }) => appointmentApi.rescheduleFromRequest(id, { new_scheduled_at }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: appointmentKeys.detail(variables.id),
      });
      queryClient.invalidateQueries({ queryKey: appointmentKeys.lists() });
      queryClient.invalidateQueries({
        queryKey: [...appointmentKeys.all, 'daily'],
      });
      queryClient.invalidateQueries({
        queryKey: [...appointmentKeys.all, 'weekly'],
      });
      queryClient.invalidateQueries({
        queryKey: [...appointmentKeys.all, 'staffDaily'],
      });
    },
  });
}
