import { useMutation, useQueryClient } from '@tanstack/react-query';
import { jobApi } from '../api/jobApi';
import type { JobCreate, JobUpdate, JobStatusUpdate } from '../types';
import { jobKeys } from './useJobs';

// Create job mutation
export function useCreateJob() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: JobCreate) => jobApi.create(data),
    onSuccess: () => {
      // Invalidate job lists to refetch
      queryClient.invalidateQueries({ queryKey: jobKeys.lists() });
      queryClient.invalidateQueries({ queryKey: jobKeys.readyToSchedule() });
      queryClient.invalidateQueries({ queryKey: jobKeys.requiresEstimate() });
    },
  });
}

// Update job mutation
export function useUpdateJob() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: JobUpdate }) =>
      jobApi.update(id, data),
    onSuccess: (updatedJob) => {
      // Update the specific job in cache
      queryClient.setQueryData(jobKeys.detail(updatedJob.id), updatedJob);
      // Invalidate lists to refetch
      queryClient.invalidateQueries({ queryKey: jobKeys.lists() });
      queryClient.invalidateQueries({ queryKey: jobKeys.readyToSchedule() });
      queryClient.invalidateQueries({ queryKey: jobKeys.requiresEstimate() });
    },
  });
}

// Update job status mutation
export function useUpdateJobStatus() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: JobStatusUpdate }) =>
      jobApi.updateStatus(id, data),
    onSuccess: (updatedJob) => {
      // Update the specific job in cache
      queryClient.setQueryData(jobKeys.detail(updatedJob.id), updatedJob);
      // Invalidate lists to refetch (status change affects multiple lists)
      queryClient.invalidateQueries({ queryKey: jobKeys.lists() });
      queryClient.invalidateQueries({ queryKey: jobKeys.readyToSchedule() });
      queryClient.invalidateQueries({ queryKey: jobKeys.requiresEstimate() });
      // Invalidate status-specific queries
      queryClient.invalidateQueries({
        queryKey: jobKeys.byStatus(updatedJob.status),
      });
    },
  });
}

// Delete job mutation
export function useDeleteJob() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => jobApi.delete(id),
    onSuccess: (_data, id) => {
      // Remove from cache
      queryClient.removeQueries({ queryKey: jobKeys.detail(id) });
      // Invalidate lists to refetch
      queryClient.invalidateQueries({ queryKey: jobKeys.lists() });
      queryClient.invalidateQueries({ queryKey: jobKeys.readyToSchedule() });
      queryClient.invalidateQueries({ queryKey: jobKeys.requiresEstimate() });
    },
  });
}

// Approve job mutation (convenience wrapper)
export function useApproveJob() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => jobApi.approve(id),
    onSuccess: (updatedJob) => {
      queryClient.setQueryData(jobKeys.detail(updatedJob.id), updatedJob);
      queryClient.invalidateQueries({ queryKey: jobKeys.lists() });
      queryClient.invalidateQueries({ queryKey: jobKeys.readyToSchedule() });
    },
  });
}

// Cancel job mutation (convenience wrapper)
export function useCancelJob() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, notes }: { id: string; notes?: string }) =>
      jobApi.cancel(id, notes),
    onSuccess: (updatedJob) => {
      queryClient.setQueryData(jobKeys.detail(updatedJob.id), updatedJob);
      queryClient.invalidateQueries({ queryKey: jobKeys.lists() });
      queryClient.invalidateQueries({ queryKey: jobKeys.readyToSchedule() });
      queryClient.invalidateQueries({ queryKey: jobKeys.requiresEstimate() });
    },
  });
}

// Complete job mutation (convenience wrapper)
export function useCompleteJob() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, notes }: { id: string; notes?: string }) =>
      jobApi.complete(id, notes),
    onSuccess: (updatedJob) => {
      queryClient.setQueryData(jobKeys.detail(updatedJob.id), updatedJob);
      queryClient.invalidateQueries({ queryKey: jobKeys.lists() });
    },
  });
}

// Close job mutation (convenience wrapper)
export function useCloseJob() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, notes }: { id: string; notes?: string }) =>
      jobApi.close(id, notes),
    onSuccess: (updatedJob) => {
      queryClient.setQueryData(jobKeys.detail(updatedJob.id), updatedJob);
      queryClient.invalidateQueries({ queryKey: jobKeys.lists() });
    },
  });
}
