/**
 * TanStack Query hooks for appointment queries.
 */

import { useQuery } from '@tanstack/react-query';
import { appointmentApi } from '../api/appointmentApi';
import type { AppointmentListParams } from '../types';

// Query key factory for appointments
export const appointmentKeys = {
  all: ['appointments'] as const,
  lists: () => [...appointmentKeys.all, 'list'] as const,
  list: (params?: AppointmentListParams) =>
    [...appointmentKeys.lists(), params] as const,
  details: () => [...appointmentKeys.all, 'detail'] as const,
  detail: (id: string) => [...appointmentKeys.details(), id] as const,
  daily: (date: string) => [...appointmentKeys.all, 'daily', date] as const,
  staffDaily: (staffId: string, date: string) =>
    [...appointmentKeys.all, 'staffDaily', staffId, date] as const,
  weekly: (startDate?: string, endDate?: string) =>
    [...appointmentKeys.all, 'weekly', startDate, endDate] as const,
};

/**
 * Hook to fetch paginated list of appointments.
 */
export function useAppointments(params?: AppointmentListParams) {
  return useQuery({
    queryKey: appointmentKeys.list(params),
    queryFn: () => appointmentApi.list(params),
  });
}

/**
 * Hook to fetch a single appointment by ID.
 */
export function useAppointment(id: string | undefined) {
  return useQuery({
    queryKey: appointmentKeys.detail(id ?? ''),
    queryFn: () => appointmentApi.getById(id!),
    enabled: !!id,
  });
}

/**
 * Hook to fetch daily schedule for a specific date.
 */
export function useDailySchedule(date: string | undefined) {
  return useQuery({
    queryKey: appointmentKeys.daily(date ?? ''),
    queryFn: () => appointmentApi.getDailySchedule(date!),
    enabled: !!date,
  });
}

/**
 * Hook to fetch daily schedule for a specific staff member.
 */
export function useStaffDailySchedule(
  staffId: string | undefined,
  date: string | undefined
) {
  return useQuery({
    queryKey: appointmentKeys.staffDaily(staffId ?? '', date ?? ''),
    queryFn: () => appointmentApi.getStaffDailySchedule(staffId!, date!),
    enabled: !!staffId && !!date,
  });
}

/**
 * Hook to fetch weekly schedule overview.
 */
export function useWeeklySchedule(startDate?: string, endDate?: string) {
  return useQuery({
    queryKey: appointmentKeys.weekly(startDate, endDate),
    queryFn: () => appointmentApi.getWeeklySchedule(startDate, endDate),
  });
}

/**
 * Hook to fetch appointments for a specific job.
 */
export function useJobAppointments(jobId: string | undefined) {
  return useQuery({
    queryKey: appointmentKeys.list({ job_id: jobId }),
    queryFn: () => appointmentApi.list({ job_id: jobId }),
    enabled: !!jobId,
  });
}

/**
 * Hook to fetch appointments for a specific staff member.
 */
export function useStaffAppointments(staffId: string | undefined) {
  return useQuery({
    queryKey: appointmentKeys.list({ staff_id: staffId }),
    queryFn: () => appointmentApi.list({ staff_id: staffId }),
    enabled: !!staffId,
  });
}
