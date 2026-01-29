/**
 * Tests for Invoice API client.
 * Requirements: All invoice API requirements
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { invoiceApi } from './invoiceApi';
import { apiClient } from '@/core/api';

// Mock the API client
vi.mock('@/core/api', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

const mockInvoice = {
  id: '123',
  invoice_number: 'INV-2025-0001',
  job_id: 'job-123',
  customer_id: 'cust-123',
  amount: '150.00',
  late_fee_amount: '0.00',
  total_amount: '150.00',
  status: 'draft',
  invoice_date: '2025-01-29',
  due_date: '2025-02-28',
  line_items: [],
};

const mockInvoiceDetail = {
  ...mockInvoice,
  job: { id: 'job-123', job_type: 'spring_startup' },
  customer: { id: 'cust-123', first_name: 'John', last_name: 'Doe' },
};

describe('invoiceApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('list', () => {
    it('fetches invoices without params', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: { items: [mockInvoice], total: 1, page: 1, page_size: 20 },
      });

      const result = await invoiceApi.list();

      expect(apiClient.get).toHaveBeenCalledWith('/invoices', { params: undefined });
      expect(result.items).toHaveLength(1);
    });

    it('fetches invoices with params', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: { items: [mockInvoice], total: 1, page: 1, page_size: 20 },
      });

      const params = { status: 'draft', page: 1, page_size: 10 };
      await invoiceApi.list(params);

      expect(apiClient.get).toHaveBeenCalledWith('/invoices', { params });
    });
  });

  describe('get', () => {
    it('fetches single invoice by ID', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockInvoiceDetail });

      const result = await invoiceApi.get('123');

      expect(apiClient.get).toHaveBeenCalledWith('/invoices/123');
      expect(result.id).toBe('123');
    });
  });

  describe('create', () => {
    it('creates new invoice', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({ data: mockInvoice });

      const data = {
        job_id: 'job-123',
        amount: '150.00',
        due_date: '2025-02-28',
      };
      const result = await invoiceApi.create(data);

      expect(apiClient.post).toHaveBeenCalledWith('/invoices', data);
      expect(result.id).toBe('123');
    });
  });

  describe('update', () => {
    it('updates existing invoice', async () => {
      vi.mocked(apiClient.put).mockResolvedValue({ data: mockInvoice });

      const data = { amount: '200.00' };
      const result = await invoiceApi.update('123', data);

      expect(apiClient.put).toHaveBeenCalledWith('/invoices/123', data);
      expect(result.id).toBe('123');
    });
  });

  describe('delete', () => {
    it('cancels invoice', async () => {
      vi.mocked(apiClient.delete).mockResolvedValue({});

      await invoiceApi.delete('123');

      expect(apiClient.delete).toHaveBeenCalledWith('/invoices/123');
    });
  });

  describe('send', () => {
    it('sends invoice', async () => {
      const sentInvoice = { ...mockInvoice, status: 'sent' };
      vi.mocked(apiClient.post).mockResolvedValue({ data: sentInvoice });

      const result = await invoiceApi.send('123');

      expect(apiClient.post).toHaveBeenCalledWith('/invoices/123/send');
      expect(result.status).toBe('sent');
    });
  });

  describe('recordPayment', () => {
    it('records payment', async () => {
      const paidInvoice = { ...mockInvoice, status: 'paid' };
      vi.mocked(apiClient.post).mockResolvedValue({ data: paidInvoice });

      const data = { amount: '150.00', payment_method: 'venmo' };
      const result = await invoiceApi.recordPayment('123', data);

      expect(apiClient.post).toHaveBeenCalledWith('/invoices/123/payment', data);
      expect(result.status).toBe('paid');
    });
  });

  describe('sendReminder', () => {
    it('sends reminder', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({ data: mockInvoice });

      await invoiceApi.sendReminder('123');

      expect(apiClient.post).toHaveBeenCalledWith('/invoices/123/reminder');
    });
  });

  describe('sendLienWarning', () => {
    it('sends lien warning', async () => {
      const warningInvoice = { ...mockInvoice, status: 'lien_warning' };
      vi.mocked(apiClient.post).mockResolvedValue({ data: warningInvoice });

      const result = await invoiceApi.sendLienWarning('123');

      expect(apiClient.post).toHaveBeenCalledWith('/invoices/123/lien-warning');
      expect(result.status).toBe('lien_warning');
    });
  });

  describe('markLienFiled', () => {
    it('marks lien as filed', async () => {
      const filedInvoice = { ...mockInvoice, status: 'lien_filed' };
      vi.mocked(apiClient.post).mockResolvedValue({ data: filedInvoice });

      const result = await invoiceApi.markLienFiled('123', '2025-01-29');

      expect(apiClient.post).toHaveBeenCalledWith('/invoices/123/lien-filed', {
        filing_date: '2025-01-29',
      });
      expect(result.status).toBe('lien_filed');
    });
  });

  describe('getOverdue', () => {
    it('fetches overdue invoices', async () => {
      const overdueInvoice = { ...mockInvoice, status: 'overdue' };
      vi.mocked(apiClient.get).mockResolvedValue({
        data: { items: [overdueInvoice], total: 1, page: 1, page_size: 20 },
      });

      const result = await invoiceApi.getOverdue();

      expect(apiClient.get).toHaveBeenCalledWith('/invoices/overdue', { params: undefined });
      expect(result.items[0].status).toBe('overdue');
    });
  });

  describe('getLienDeadlines', () => {
    it('fetches lien deadlines', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: {
          approaching_45_day: [mockInvoice],
          approaching_120_day: [],
        },
      });

      const result = await invoiceApi.getLienDeadlines();

      expect(apiClient.get).toHaveBeenCalledWith('/invoices/lien-deadlines');
      expect(result.approaching_45_day).toHaveLength(1);
      expect(result.approaching_120_day).toHaveLength(0);
    });
  });

  describe('generateFromJob', () => {
    it('generates invoice from job', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({ data: mockInvoice });

      const result = await invoiceApi.generateFromJob('job-123');

      expect(apiClient.post).toHaveBeenCalledWith('/invoices/generate-from-job/job-123');
      expect(result.id).toBe('123');
    });
  });
});
