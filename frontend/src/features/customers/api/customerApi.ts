import { apiClient } from '@/core/api';
import type { PaginatedResponse } from '@/core/api';
import type {
  ConsentHistoryResponse,
  ConsentStatus,
  Customer,
  CustomerCreate,
  CustomerUpdate,
  CustomerListParams,
  CustomerPhoto,
  CustomerInvoice,
  PaymentMethod,
  ChargeRequest,
  DuplicateGroup,
  MergeRequest,
  MergePreview,
  PaginatedMergeCandidates,
  SentMessage,
  ServicePreference,
  ServicePreferenceCreate,
  Property,
} from '../types';

const BASE_PATH = '/customers';

export const customerApi = {
  // List customers with pagination and filters
  list: async (params?: CustomerListParams): Promise<PaginatedResponse<Customer>> => {
    const response = await apiClient.get<PaginatedResponse<Customer>>(BASE_PATH, {
      params,
    });
    return response.data;
  },

  // Get single customer by ID
  get: async (id: string): Promise<Customer> => {
    const response = await apiClient.get<Customer>(`${BASE_PATH}/${id}`);
    return response.data;
  },

  // Create new customer
  create: async (data: CustomerCreate): Promise<Customer> => {
    const response = await apiClient.post<Customer>(BASE_PATH, data);
    return response.data;
  },

  // Update existing customer
  update: async (id: string, data: CustomerUpdate): Promise<Customer> => {
    const response = await apiClient.put<Customer>(`${BASE_PATH}/${id}`, data);
    return response.data;
  },

  // Delete customer
  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`${BASE_PATH}/${id}`);
  },

  // Search customers
  search: async (query: string): Promise<PaginatedResponse<Customer>> => {
    const response = await apiClient.get<PaginatedResponse<Customer>>(BASE_PATH, {
      params: { search: query },
    });
    return response.data;
  },

  // Update customer flags
  updateFlags: async (
    id: string,
    flags: {
      is_priority?: boolean;
      is_red_flag?: boolean;
      is_slow_payer?: boolean;
    }
  ): Promise<Customer> => {
    const response = await apiClient.put<Customer>(`${BASE_PATH}/${id}`, flags);
    return response.data;
  },

  // --- Photos (Req 9) ---
  listPhotos: async (id: string): Promise<CustomerPhoto[]> => {
    const response = await apiClient.get<CustomerPhoto[]>(`${BASE_PATH}/${id}/photos`);
    return response.data;
  },

  uploadPhotos: async (id: string, files: File[], caption?: string): Promise<CustomerPhoto[]> => {
    const formData = new FormData();
    files.forEach((file) => formData.append('files', file));
    if (caption) formData.append('caption', caption);
    const response = await apiClient.post<CustomerPhoto[]>(`${BASE_PATH}/${id}/photos`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  updatePhotoCaption: async (customerId: string, photoId: string, caption: string): Promise<CustomerPhoto> => {
    const response = await apiClient.patch<CustomerPhoto>(
      `${BASE_PATH}/${customerId}/photos/${photoId}`,
      { caption }
    );
    return response.data;
  },

  deletePhoto: async (customerId: string, photoId: string): Promise<void> => {
    await apiClient.delete(`${BASE_PATH}/${customerId}/photos/${photoId}`);
  },

  // --- Invoices (Req 10) ---
  listInvoices: async (
    id: string,
    params?: { page?: number; page_size?: number }
  ): Promise<PaginatedResponse<CustomerInvoice>> => {
    const response = await apiClient.get<PaginatedResponse<CustomerInvoice>>(
      `${BASE_PATH}/${id}/invoices`,
      { params }
    );
    return response.data;
  },

  // --- Payment Methods (Req 56) ---
  listPaymentMethods: async (id: string): Promise<PaymentMethod[]> => {
    const response = await apiClient.get<PaymentMethod[]>(`${BASE_PATH}/${id}/payment-methods`);
    return response.data;
  },

  chargeCustomer: async (id: string, data: ChargeRequest): Promise<{ payment_intent_id: string }> => {
    const response = await apiClient.post<{ payment_intent_id: string }>(
      `${BASE_PATH}/${id}/charge`,
      data
    );
    return response.data;
  },

  // --- Duplicates (CRM Changes Update 2 Req 5, 6) ---
  getDuplicates: async (id: string): Promise<DuplicateGroup | null> => {
    const response = await apiClient.get<DuplicateGroup | null>(`${BASE_PATH}/${id}/duplicates`);
    return response.data;
  },

  getDuplicateReviewQueue: async (skip = 0, limit = 20): Promise<PaginatedMergeCandidates> => {
    const response = await apiClient.get<PaginatedMergeCandidates>(`${BASE_PATH}/duplicates`, {
      params: { skip, limit },
    });
    return response.data;
  },

  mergeCustomers: async (primaryId: string, data: MergeRequest): Promise<void> => {
    await apiClient.post(`${BASE_PATH}/${primaryId}/merge`, data);
  },

  previewMerge: async (primaryId: string, data: MergeRequest): Promise<MergePreview> => {
    const response = await apiClient.post<MergePreview>(`${BASE_PATH}/${primaryId}/merge/preview`, data);
    return response.data;
  },

  // --- Sent Messages (Req 82) ---
  listSentMessages: async (id: string): Promise<SentMessage[]> => {
    const response = await apiClient.get<SentMessage[]>(`${BASE_PATH}/${id}/sent-messages`);
    return response.data;
  },

  // --- SMS Consent (Gap 06) ---
  getConsentStatus: async (id: string): Promise<ConsentStatus> => {
    const response = await apiClient.get<ConsentStatus>(`${BASE_PATH}/${id}/consent-status`);
    return response.data;
  },

  getConsentHistory: async (
    id: string,
    params?: { limit?: number }
  ): Promise<ConsentHistoryResponse> => {
    const response = await apiClient.get<ConsentHistoryResponse>(
      `${BASE_PATH}/${id}/consent-history`,
      { params }
    );
    return response.data;
  },

  // --- Tier 1 Duplicate Check (Req 6.13) ---
  checkDuplicate: async (params: { phone?: string; email?: string; exclude_id?: string }): Promise<Customer[]> => {
    const response = await apiClient.get<Customer[]>(`${BASE_PATH}/check-duplicate`, { params });
    return response.data;
  },

  // --- Service Preferences (CRM2 Req 7) ---
  listServicePreferences: async (id: string): Promise<ServicePreference[]> => {
    const response = await apiClient.get<ServicePreference[]>(`${BASE_PATH}/${id}/service-preferences`);
    return response.data;
  },

  addServicePreference: async (id: string, data: ServicePreferenceCreate): Promise<ServicePreference[]> => {
    const response = await apiClient.post<ServicePreference[]>(`${BASE_PATH}/${id}/service-preferences`, data);
    return response.data;
  },

  updateServicePreference: async (
    customerId: string,
    preferenceId: string,
    data: ServicePreferenceCreate
  ): Promise<ServicePreference[]> => {
    const response = await apiClient.put<ServicePreference[]>(
      `${BASE_PATH}/${customerId}/service-preferences/${preferenceId}`,
      data
    );
    return response.data;
  },

  deleteServicePreference: async (customerId: string, preferenceId: string): Promise<ServicePreference[]> => {
    const response = await apiClient.delete<ServicePreference[]>(
      `${BASE_PATH}/${customerId}/service-preferences/${preferenceId}`
    );
    return response.data;
  },

  // --- Properties (Phase 6 inline edit) ---
  listProperties: async (customerId: string): Promise<Property[]> => {
    const response = await apiClient.get<Property[]>(`${BASE_PATH}/${customerId}/properties`);
    return response.data;
  },

  addProperty: async (customerId: string, data: Partial<Property>): Promise<Property> => {
    const response = await apiClient.post<Property>(`${BASE_PATH}/${customerId}/properties`, data);
    return response.data;
  },

  updateProperty: async (propertyId: string, data: Partial<Property>): Promise<Property> => {
    const response = await apiClient.put<Property>(`/properties/${propertyId}`, data);
    return response.data;
  },

  deleteProperty: async (propertyId: string): Promise<void> => {
    await apiClient.delete(`/properties/${propertyId}`);
  },

  setPropertyPrimary: async (propertyId: string): Promise<Property> => {
    const response = await apiClient.put<Property>(`/properties/${propertyId}/primary`);
    return response.data;
  },

  // --- Export (Req 15) ---
  exportCustomers: async (): Promise<Blob> => {
    const response = await apiClient.post('/customers/export', null, {
      params: { format: 'xlsx' },
      responseType: 'blob',
    });
    return response.data as Blob;
  },
};
