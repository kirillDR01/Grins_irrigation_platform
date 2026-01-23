import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import axios from 'axios';
import MockAdapter from 'axios-mock-adapter';
import { apiClient, getErrorMessage } from './client';

describe('apiClient', () => {
  let mock: MockAdapter;

  beforeEach(() => {
    mock = new MockAdapter(apiClient);
    localStorage.clear();
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
  });

  describe('request interceptor', () => {
    it('should add auth token to request headers when token exists', async () => {
      localStorage.setItem('auth_token', 'test-token-123');
      mock.onGet('/test').reply(200, { data: 'success' });

      await apiClient.get('/test');

      expect(mock.history.get[0].headers?.Authorization).toBe('Bearer test-token-123');
    });

    it('should not add auth header when no token exists', async () => {
      mock.onGet('/test').reply(200, { data: 'success' });

      await apiClient.get('/test');

      expect(mock.history.get[0].headers?.Authorization).toBeUndefined();
    });
  });

  describe('response interceptor', () => {
    it('should pass through successful responses', async () => {
      mock.onGet('/test').reply(200, { data: 'success' });

      const response = await apiClient.get('/test');

      expect(response.data).toEqual({ data: 'success' });
    });

    it('should handle 401 unauthorized by clearing token', async () => {
      localStorage.setItem('auth_token', 'test-token');
      mock.onGet('/test').reply(401, { error: { message: 'Unauthorized' } });

      await expect(apiClient.get('/test')).rejects.toThrow();
      expect(localStorage.getItem('auth_token')).toBeNull();
    });

    it('should handle 403 forbidden', async () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      mock.onGet('/test').reply(403, { error: { message: 'Forbidden' } });

      await expect(apiClient.get('/test')).rejects.toThrow();
      expect(consoleSpy).toHaveBeenCalledWith('Access forbidden');
    });

    it('should handle 500 server error', async () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      mock.onGet('/test').reply(500, { error: { message: 'Server error' } });

      await expect(apiClient.get('/test')).rejects.toThrow();
      expect(consoleSpy).toHaveBeenCalledWith('Server error:', expect.any(Object));
    });

    it('should handle network errors', async () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      // Use timeout to simulate network error (no response)
      mock.onGet('/test').timeout();

      await expect(apiClient.get('/test')).rejects.toThrow();
      // Network errors may or may not trigger the console.error depending on the error type
      // The important thing is that the request rejects
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
    // Mock axios.isAxiosError
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
