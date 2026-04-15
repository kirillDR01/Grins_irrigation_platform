import { apiClient } from '@/core/api';
import type { PaginatedResponse } from '@/core/api';
import type {
  Invoice,
  InvoiceDetail,
  InvoiceCreate,
  InvoiceUpdate,
  InvoiceListParams,
  PaymentRecord,
  BulkNotifyRequest,
  BulkNotifyResponse,
  MassNotifyRequest,
  MassNotifyResponse,
  PdfUrlResponse,
} from '../types';

const BASE_PATH = '/invoices';

export const invoiceApi = {
  // List invoices with pagination and filters
  list: async (params?: InvoiceListParams): Promise<PaginatedResponse<Invoice>> => {
    const response = await apiClient.get<PaginatedResponse<Invoice>>(BASE_PATH, {
      params,
    });
    return response.data;
  },

  // Get single invoice by ID with details
  get: async (id: string): Promise<InvoiceDetail> => {
    const response = await apiClient.get<InvoiceDetail>(`${BASE_PATH}/${id}`);
    return response.data;
  },

  // Create new invoice
  create: async (data: InvoiceCreate): Promise<Invoice> => {
    const response = await apiClient.post<Invoice>(BASE_PATH, data);
    return response.data;
  },

  // Update existing invoice (draft only)
  update: async (id: string, data: InvoiceUpdate): Promise<Invoice> => {
    const response = await apiClient.put<Invoice>(`${BASE_PATH}/${id}`, data);
    return response.data;
  },

  // Cancel invoice
  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`${BASE_PATH}/${id}`);
  },

  // Send invoice (draft → sent)
  send: async (id: string): Promise<Invoice> => {
    const response = await apiClient.post<Invoice>(`${BASE_PATH}/${id}/send`);
    return response.data;
  },

  // Record payment
  recordPayment: async (id: string, data: PaymentRecord): Promise<Invoice> => {
    const response = await apiClient.post<Invoice>(`${BASE_PATH}/${id}/payment`, data);
    return response.data;
  },

  // Send reminder
  sendReminder: async (id: string): Promise<Invoice> => {
    const response = await apiClient.post<Invoice>(`${BASE_PATH}/${id}/reminder`);
    return response.data;
  },

  // Send lien warning (admin only)
  sendLienWarning: async (id: string): Promise<Invoice> => {
    const response = await apiClient.post<Invoice>(`${BASE_PATH}/${id}/lien-warning`);
    return response.data;
  },

  // Mark lien filed (admin only)
  markLienFiled: async (id: string, filingDate: string): Promise<Invoice> => {
    const response = await apiClient.post<Invoice>(`${BASE_PATH}/${id}/lien-filed`, {
      filing_date: filingDate,
    });
    return response.data;
  },

  // Get overdue invoices
  getOverdue: async (params?: InvoiceListParams): Promise<PaginatedResponse<Invoice>> => {
    const response = await apiClient.get<PaginatedResponse<Invoice>>(
      `${BASE_PATH}/overdue`,
      { params },
    );
    return response.data;
  },

  // Get lien deadlines
  getLienDeadlines: async (): Promise<{
    approaching_45_day: Invoice[];
    approaching_120_day: Invoice[];
  }> => {
    const response = await apiClient.get<{
      approaching_45_day: Invoice[];
      approaching_120_day: Invoice[];
    }>(`${BASE_PATH}/lien-deadlines`);
    return response.data;
  },

  // Generate invoice from job
  generateFromJob: async (jobId: string): Promise<Invoice> => {
    const response = await apiClient.post<Invoice>(
      `${BASE_PATH}/generate-from-job/${jobId}`,
    );
    return response.data;
  },

  // Bulk notify customers for selected invoices (Req 38)
  bulkNotify: async (data: BulkNotifyRequest): Promise<BulkNotifyResponse> => {
    const response = await apiClient.post<BulkNotifyResponse>(
      `${BASE_PATH}/bulk-notify`,
      data,
    );
    return response.data;
  },

  // Mass notify customers (Req 29.3, 29.4)
  massNotify: async (data: MassNotifyRequest): Promise<MassNotifyResponse> => {
    const response = await apiClient.post<MassNotifyResponse>(
      `${BASE_PATH}/mass-notify`,
      data,
    );
    return response.data;
  },

  // Generate PDF for an invoice (Req 80)
  generatePdf: async (id: string): Promise<PdfUrlResponse> => {
    const response = await apiClient.post<PdfUrlResponse>(
      `${BASE_PATH}/${id}/generate-pdf`,
    );
    return response.data;
  },

  // Get pre-signed PDF download URL (Req 80)
  getPdfUrl: async (id: string): Promise<PdfUrlResponse> => {
    const response = await apiClient.get<PdfUrlResponse>(
      `${BASE_PATH}/${id}/pdf`,
    );
    return response.data;
  },
};
