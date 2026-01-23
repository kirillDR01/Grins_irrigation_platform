import { describe, it, expect, vi, beforeEach } from 'vitest';
import { customerApi } from './customerApi';
import { apiClient } from '@/core/api';

// Mock the apiClient
vi.mock('@/core/api', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

const mockCustomer = {
  id: '1',
  first_name: 'John',
  last_name: 'Doe',
  phone: '6125551234',
  email: 'john@example.com',
  is_priority: false,
  is_red_flag: false,
  is_slow_payer: false,
  sms_opt_in: true,
  email_opt_in: true,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

const mockPaginatedResponse = {
  items: [mockCustomer],
  total: 1,
  page: 1,
  page_size: 20,
  total_pages: 1,
};

describe('customerApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('list', () => {
    it('should fetch customers list', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockPaginatedResponse });

      const result = await customerApi.list();

      expect(apiClient.get).toHaveBeenCalledWith('/customers', { params: undefined });
      expect(result).toEqual(mockPaginatedResponse);
    });

    it('should fetch customers list with params', async () => {
      const params = { page: 2, page_size: 10 };
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockPaginatedResponse });

      const result = await customerApi.list(params);

      expect(apiClient.get).toHaveBeenCalledWith('/customers', { params });
      expect(result).toEqual(mockPaginatedResponse);
    });

    it('should handle list error', async () => {
      const error = new Error('Network error');
      vi.mocked(apiClient.get).mockRejectedValue(error);

      await expect(customerApi.list()).rejects.toThrow('Network error');
    });
  });

  describe('get', () => {
    it('should fetch single customer by id', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockCustomer });

      const result = await customerApi.get('1');

      expect(apiClient.get).toHaveBeenCalledWith('/customers/1');
      expect(result).toEqual(mockCustomer);
    });

    it('should handle get error', async () => {
      const error = new Error('Customer not found');
      vi.mocked(apiClient.get).mockRejectedValue(error);

      await expect(customerApi.get('999')).rejects.toThrow('Customer not found');
    });
  });

  describe('create', () => {
    it('should create new customer', async () => {
      const createData = {
        first_name: 'John',
        last_name: 'Doe',
        phone: '6125551234',
      };
      vi.mocked(apiClient.post).mockResolvedValue({ data: mockCustomer });

      const result = await customerApi.create(createData);

      expect(apiClient.post).toHaveBeenCalledWith('/customers', createData);
      expect(result).toEqual(mockCustomer);
    });

    it('should create customer with all fields', async () => {
      const createData = {
        first_name: 'John',
        last_name: 'Doe',
        phone: '6125551234',
        email: 'john@example.com',
        sms_opt_in: true,
        email_opt_in: false,
      };
      vi.mocked(apiClient.post).mockResolvedValue({ data: mockCustomer });

      const result = await customerApi.create(createData);

      expect(apiClient.post).toHaveBeenCalledWith('/customers', createData);
      expect(result).toEqual(mockCustomer);
    });

    it('should handle create error', async () => {
      const error = new Error('Validation error');
      vi.mocked(apiClient.post).mockRejectedValue(error);

      await expect(
        customerApi.create({ first_name: '', last_name: '', phone: '' })
      ).rejects.toThrow('Validation error');
    });
  });

  describe('update', () => {
    it('should update existing customer', async () => {
      const updateData = { first_name: 'Jane' };
      const updatedCustomer = { ...mockCustomer, first_name: 'Jane' };
      vi.mocked(apiClient.put).mockResolvedValue({ data: updatedCustomer });

      const result = await customerApi.update('1', updateData);

      expect(apiClient.put).toHaveBeenCalledWith('/customers/1', updateData);
      expect(result).toEqual(updatedCustomer);
    });

    it('should update multiple fields', async () => {
      const updateData = {
        first_name: 'Jane',
        email: 'jane@example.com',
        sms_opt_in: false,
      };
      const updatedCustomer = { ...mockCustomer, ...updateData };
      vi.mocked(apiClient.put).mockResolvedValue({ data: updatedCustomer });

      const result = await customerApi.update('1', updateData);

      expect(apiClient.put).toHaveBeenCalledWith('/customers/1', updateData);
      expect(result).toEqual(updatedCustomer);
    });

    it('should handle update error', async () => {
      const error = new Error('Update failed');
      vi.mocked(apiClient.put).mockRejectedValue(error);

      await expect(customerApi.update('1', { first_name: 'Jane' })).rejects.toThrow(
        'Update failed'
      );
    });
  });

  describe('delete', () => {
    it('should delete customer', async () => {
      vi.mocked(apiClient.delete).mockResolvedValue({ data: undefined });

      await customerApi.delete('1');

      expect(apiClient.delete).toHaveBeenCalledWith('/customers/1');
    });

    it('should handle delete error', async () => {
      const error = new Error('Delete failed');
      vi.mocked(apiClient.delete).mockRejectedValue(error);

      await expect(customerApi.delete('1')).rejects.toThrow('Delete failed');
    });
  });

  describe('search', () => {
    it('should search customers', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockPaginatedResponse });

      const result = await customerApi.search('john');

      expect(apiClient.get).toHaveBeenCalledWith('/customers', {
        params: { search: 'john' },
      });
      expect(result).toEqual(mockPaginatedResponse);
    });

    it('should handle search error', async () => {
      const error = new Error('Search failed');
      vi.mocked(apiClient.get).mockRejectedValue(error);

      await expect(customerApi.search('john')).rejects.toThrow('Search failed');
    });
  });

  describe('updateFlags', () => {
    it('should update customer flags', async () => {
      const flags = { is_priority: true };
      const updatedCustomer = { ...mockCustomer, is_priority: true };
      vi.mocked(apiClient.put).mockResolvedValue({ data: updatedCustomer });

      const result = await customerApi.updateFlags('1', flags);

      expect(apiClient.put).toHaveBeenCalledWith('/customers/1', flags);
      expect(result).toEqual(updatedCustomer);
    });

    it('should update multiple flags', async () => {
      const flags = { is_priority: true, is_red_flag: true, is_slow_payer: false };
      const updatedCustomer = { ...mockCustomer, ...flags };
      vi.mocked(apiClient.put).mockResolvedValue({ data: updatedCustomer });

      const result = await customerApi.updateFlags('1', flags);

      expect(apiClient.put).toHaveBeenCalledWith('/customers/1', flags);
      expect(result).toEqual(updatedCustomer);
    });

    it('should handle flags update error', async () => {
      const error = new Error('Flags update failed');
      vi.mocked(apiClient.put).mockRejectedValue(error);

      await expect(customerApi.updateFlags('1', { is_priority: true })).rejects.toThrow(
        'Flags update failed'
      );
    });
  });
});
