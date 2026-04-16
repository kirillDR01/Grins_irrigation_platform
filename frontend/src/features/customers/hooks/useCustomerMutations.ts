import { useMutation, useQueryClient } from '@tanstack/react-query';
import { customerApi } from '../api/customerApi';
import type { CustomerCreate, CustomerUpdate, ChargeRequest, MergeRequest, ServicePreferenceCreate } from '../types';
import { customerKeys, customerInvoiceKeys } from './useCustomers';

// Create customer mutation
export function useCreateCustomer() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CustomerCreate) => customerApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: customerKeys.lists() });
    },
  });
}

// Update customer mutation
export function useUpdateCustomer() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: CustomerUpdate }) =>
      customerApi.update(id, data),
    onSuccess: (updatedCustomer) => {
      queryClient.setQueryData(customerKeys.detail(updatedCustomer.id), updatedCustomer);
      queryClient.invalidateQueries({ queryKey: customerKeys.lists() });
    },
  });
}

// Delete customer mutation
export function useDeleteCustomer() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => customerApi.delete(id),
    onSuccess: (_data, id) => {
      queryClient.removeQueries({ queryKey: customerKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: customerKeys.lists() });
    },
  });
}

// Update customer flags mutation
export function useUpdateCustomerFlags() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      id,
      flags,
    }: {
      id: string;
      flags: {
        is_priority?: boolean;
        is_red_flag?: boolean;
        is_slow_payer?: boolean;
      };
    }) => customerApi.updateFlags(id, flags),
    onSuccess: (updatedCustomer) => {
      queryClient.setQueryData(customerKeys.detail(updatedCustomer.id), updatedCustomer);
      queryClient.invalidateQueries({ queryKey: customerKeys.lists() });
    },
  });
}

// Upload customer photos mutation (Req 9)
export function useUploadCustomerPhotos(customerId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ files, caption }: { files: File[]; caption?: string }) =>
      customerApi.uploadPhotos(customerId, files, caption),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: customerKeys.photos(customerId) });
    },
  });
}

// Update photo caption mutation (Req 9)
export function useUpdatePhotoCaption(customerId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ photoId, caption }: { photoId: string; caption: string }) =>
      customerApi.updatePhotoCaption(customerId, photoId, caption),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: customerKeys.photos(customerId) });
    },
  });
}

// Delete customer photo mutation (Req 9)
export function useDeleteCustomerPhoto(customerId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (photoId: string) => customerApi.deletePhoto(customerId, photoId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: customerKeys.photos(customerId) });
    },
  });
}

// Charge customer payment method mutation (Req 56)
export function useChargeCustomer(customerId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: ChargeRequest) => customerApi.chargeCustomer(customerId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: customerInvoiceKeys.byCustomer(customerId),
      });
    },
  });
}

// Merge duplicate customers mutation (CRM Changes Update 2 Req 6)
export function useMergeCustomers(primaryId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: MergeRequest) => customerApi.mergeCustomers(primaryId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: customerKeys.all });
    },
  });
}

// Add service preference mutation (CRM2 Req 7)
export function useAddServicePreference(customerId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: ServicePreferenceCreate) =>
      customerApi.addServicePreference(customerId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: customerKeys.servicePreferences(customerId) });
    },
  });
}

// Update service preference mutation (CRM2 Req 7)
export function useUpdateServicePreference(customerId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ preferenceId, data }: { preferenceId: string; data: ServicePreferenceCreate }) =>
      customerApi.updateServicePreference(customerId, preferenceId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: customerKeys.servicePreferences(customerId) });
    },
  });
}

// Delete service preference mutation (CRM2 Req 7)
export function useDeleteServicePreference(customerId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (preferenceId: string) =>
      customerApi.deleteServicePreference(customerId, preferenceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: customerKeys.servicePreferences(customerId) });
    },
  });
}
