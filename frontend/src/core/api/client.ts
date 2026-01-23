import axios from 'axios';
import type { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from 'axios';
import { config } from '@/core/config';
import type { ApiError } from './types';

// Create axios instance with default config
export const apiClient: AxiosInstance = axios.create({
  baseURL: `${config.apiBaseUrl}/api/${config.apiVersion}`,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor - add auth token if available
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('auth_token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor - handle errors
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ApiError>) => {
    // Handle specific error codes
    if (error.response) {
      const status = error.response.status;
      
      if (status === 401) {
        // Unauthorized - clear token and redirect to login
        localStorage.removeItem('auth_token');
        // Could dispatch an event or redirect here
      }
      
      if (status === 403) {
        // Forbidden - user doesn't have permission
        console.error('Access forbidden');
      }
      
      if (status >= 500) {
        // Server error
        console.error('Server error:', error.response.data);
      }
    } else if (error.request) {
      // Network error
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
