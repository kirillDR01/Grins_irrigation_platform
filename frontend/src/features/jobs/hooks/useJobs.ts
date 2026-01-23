import { useQuery } from '@tanstack/react-query';
import { jobApi } from '../api/jobApi';
import type { JobListParams, JobStatus } from '../types';

// Query key factory
export const jobKeys = {
  all: ['jobs'] as const,
  lists: () => [...jobKeys.all, 'list'] as const,
  list: (params?: JobListParams) => [...jobKeys.lists(), params] as const,
  details: () => [...jobKeys.all, 'detail'] as const,
  detail: (id: string) => [...jobKeys.details(), id] as const,
  byStatus: (status: JobStatus) => [...jobKeys.all, 'status', status] as const,
  byCustomer: (customerId: string) =>
    [...jobKeys.all, 'customer', customerId] as const,
  readyToSchedule: () => [...jobKeys.all, 'ready-to-schedule'] as const,
  requiresEstimate: () => [...jobKeys.all, 'requires-estimate'] as const,
  search: (query: string) => [...jobKeys.all, 'search', query] as const,
};

// List jobs with pagination and filters
export function useJobs(params?: JobListParams) {
  return useQuery({
    queryKey: jobKeys.list(params),
    queryFn: () => jobApi.list(params),
  });
}

// Get single job by ID
export function useJob(id: string) {
  return useQuery({
    queryKey: jobKeys.detail(id),
    queryFn: () => jobApi.get(id),
    enabled: !!id,
  });
}

// Get jobs by status
export function useJobsByStatus(
  status: JobStatus,
  params?: Omit<JobListParams, 'status'>
) {
  return useQuery({
    queryKey: jobKeys.byStatus(status),
    queryFn: () => jobApi.getByStatus(status, params),
  });
}

// Get jobs by customer
export function useJobsByCustomer(
  customerId: string,
  params?: Omit<JobListParams, 'customer_id'>
) {
  return useQuery({
    queryKey: jobKeys.byCustomer(customerId),
    queryFn: () => jobApi.getByCustomer(customerId, params),
    enabled: !!customerId,
  });
}

// Get jobs ready to schedule
export function useJobsReadyToSchedule() {
  return useQuery({
    queryKey: jobKeys.readyToSchedule(),
    queryFn: () => jobApi.getReadyToSchedule(),
  });
}

// Get jobs requiring estimate
export function useJobsRequiresEstimate() {
  return useQuery({
    queryKey: jobKeys.requiresEstimate(),
    queryFn: () => jobApi.getRequiresEstimate(),
  });
}

// Search jobs with debounced query
export function useJobSearch(query: string) {
  return useQuery({
    queryKey: jobKeys.search(query),
    queryFn: () => jobApi.search(query),
    enabled: query.length >= 2,
  });
}
