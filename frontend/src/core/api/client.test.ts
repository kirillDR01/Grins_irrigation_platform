import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import axios from 'axios';
import MockAdapter from 'axios-mock-adapter';
import { apiClient, getErrorMessage } from './client';

// Mock sonner toast
vi.mock('sonner', () => ({
  toast: {
    warning: vi.fn(),
    error: vi.fn(),
    success: vi.fn(),
  },
}));

describe('apiClient', () => {
  let mock: MockAdapter;

  beforeEach(() => {
    mock = new MockAdapter(apiClient);
  });

  afterEach(() => {
    mock.restore();
    vi.restoreAllMocks();
  });

  describe('configuration', () => {
    it('should have correct base URL', () => {
      expect(apiClient.defaults.baseURL).toContain('/api/');
    });

    it('should have correct timeout', () => {
      expect(apiClient.defaults.timeout).toBe(30000);
    });

    it('should have correct content type header', () => {
      expect(apiClient.defaults.headers['Content-Type']).toBe('application/json');
    });

    it('should have withCredentials enabled', () => {
      expect(apiClient.defaults.withCredentials).toBe(true);
    });
  });

  describe('response interceptor', () => {
    it('should pass through successful responses', async () => {
      mock.onGet('/test').reply(200, { data: 'success' });

      const response = await apiClient.get('/test');

      expect(response.data).toEqual({ data: 'success' });
    });

    it('should handle 403 forbidden', async () => {
      vi.spyOn(console, 'error').mockImplementation(() => {});
      mock.onGet('/test').reply(403, { error: { message: 'Forbidden' } });

      await expect(apiClient.get('/test')).rejects.toThrow();
    });

    it('should handle 500 server error', async () => {
      vi.spyOn(console, 'error').mockImplementation(() => {});
      mock.onGet('/test').reply(500, { error: { message: 'Server error' } });

      await expect(apiClient.get('/test')).rejects.toThrow();
    });

    it('should handle network errors', async () => {
      vi.spyOn(console, 'error').mockImplementation(() => {});
      mock.onGet('/test').timeout();

      await expect(apiClient.get('/test')).rejects.toThrow();
    });

    it('should show toast on 429 rate limit', async () => {
      const { toast } = await import('sonner');
      mock.onGet('/test').reply(429, { error: { message: 'Rate limited' } }, { 'retry-after': '15' });

      await expect(apiClient.get('/test')).rejects.toThrow();

      expect(toast.warning).toHaveBeenCalledWith('Too many requests', expect.objectContaining({
        description: 'Please wait 15 seconds and try again.',
      }));
    });

    it('should attempt silent refresh on 401 for non-auth endpoints', async () => {
      // First call returns 401, refresh succeeds, retry succeeds
      mock.onGet('/test').replyOnce(401, { error: { message: 'Unauthorized' } });
      mock.onPost('/auth/refresh').reply(200, { access_token: 'new', token_type: 'bearer', expires_in: 900 });
      mock.onGet('/test').reply(200, { data: 'success' });

      const response = await apiClient.get('/test');
      expect(response.data).toEqual({ data: 'success' });
    });
  });
});

describe('getErrorMessage', () => {
  it('should extract message from axios error with API error response', () => {
    const error = {
      isAxiosError: true,
      response: {
        data: {
          error: {
            message: 'Custom API error message',
          },
        },
      },
    };
    vi.spyOn(axios, 'isAxiosError').mockReturnValue(true);

    const message = getErrorMessage(error);

    expect(message).toBe('Custom API error message');
  });

  it('should extract message from axios error without API error structure', () => {
    const error = {
      isAxiosError: true,
      message: 'Request failed with status code 404',
      response: {
        data: {},
      },
    };
    vi.spyOn(axios, 'isAxiosError').mockReturnValue(true);

    const message = getErrorMessage(error);

    expect(message).toBe('Request failed with status code 404');
  });

  it('should extract message from standard Error', () => {
    vi.spyOn(axios, 'isAxiosError').mockReturnValue(false);
    const error = new Error('Standard error message');

    const message = getErrorMessage(error);

    expect(message).toBe('Standard error message');
  });

  it('should return default message for unknown error types', () => {
    vi.spyOn(axios, 'isAxiosError').mockReturnValue(false);
    const error = { unknown: 'error' };

    const message = getErrorMessage(error);

    expect(message).toBe('An unexpected error occurred');
  });

  it('should return default message for null error', () => {
    vi.spyOn(axios, 'isAxiosError').mockReturnValue(false);

    const message = getErrorMessage(null);

    expect(message).toBe('An unexpected error occurred');
  });

  it('should return default message for undefined error', () => {
    vi.spyOn(axios, 'isAxiosError').mockReturnValue(false);

    const message = getErrorMessage(undefined);

    expect(message).toBe('An unexpected error occurred');
  });

  it('should handle axios error with only message property', () => {
    const error = {
      isAxiosError: true,
      message: 'Network Error',
    };
    vi.spyOn(axios, 'isAxiosError').mockReturnValue(true);

    const message = getErrorMessage(error);

    expect(message).toBe('Network Error');
  });
});
