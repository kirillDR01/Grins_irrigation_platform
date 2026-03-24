import axios from 'axios';
import type { AxiosError, AxiosInstance, AxiosRequestConfig } from 'axios';
import { toast } from 'sonner';
import { config } from '@/core/config';
import type { ApiError } from './types';

// Create axios instance with default config
export const apiClient: AxiosInstance = axios.create({
  baseURL: `${config.apiBaseUrl}/api/${config.apiVersion}`,
  timeout: 30000,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Track whether a token refresh is in progress to avoid concurrent refreshes
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value?: unknown) => void;
  reject: (reason?: unknown) => void;
  config: AxiosRequestConfig;
}> = [];

function processQueue(error: unknown) {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(apiClient(prom.config));
    }
  });
  failedQueue = [];
}

// Response interceptor - handle 401 (silent refresh) and 429 (rate limit toast)
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<ApiError>) => {
    const originalRequest = error.config;

    if (error.response) {
      const status = error.response.status;

      // 401 — attempt silent refresh, then retry once
      if (status === 401 && originalRequest && !originalRequest.url?.includes('/auth/refresh') && !originalRequest.url?.includes('/auth/login')) {
        if (isRefreshing) {
          // Queue this request until refresh completes
          return new Promise((resolve, reject) => {
            failedQueue.push({ resolve, reject, config: originalRequest });
          });
        }

        isRefreshing = true;

        try {
          await apiClient.post('/auth/refresh', null, { withCredentials: true });
          isRefreshing = false;
          processQueue(null);
          // Retry the original request
          return apiClient(originalRequest);
        } catch (refreshError) {
          isRefreshing = false;
          processQueue(refreshError);
          // Redirect to login with reason
          window.location.href = '/login?reason=session_expired';
          return Promise.reject(refreshError);
        }
      }

      // 429 — rate limit: show toast with retry time
      if (status === 429) {
        const retryAfter = error.response.headers?.['retry-after'];
        const seconds = retryAfter ? parseInt(retryAfter, 10) || 30 : 30;
        toast.warning('Too many requests', {
          description: `Please wait ${seconds} seconds and try again.`,
          duration: seconds * 1000,
        });
        return Promise.reject(error);
      }

      if (status === 403) {
        console.error('Access forbidden');
      }

      if (status >= 500) {
        console.error('Server error:', error.response.data);
      }
    } else if (error.request) {
      console.error('Network error - no response received');
    }

    return Promise.reject(error);
  }
);

// Helper function to extract error message
export const getErrorMessage = (error: unknown): string => {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<ApiError>;
    if (axiosError.response?.data?.error?.message) {
      return axiosError.response.data.error.message;
    }
    if (axiosError.message) {
      return axiosError.message;
    }
  }
  if (error instanceof Error) {
    return error.message;
  }
  return 'An unexpected error occurred';
};
