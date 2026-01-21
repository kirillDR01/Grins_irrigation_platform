# Implement API Client

Create a type-safe API client for a feature using Axios.

## API Client Structure

```typescript
// features/{feature}/api/{feature}Api.ts
import { apiClient } from '@/core/api/client';
import type { 
  {Feature}, 
  {Feature}Create, 
  {Feature}Update,
  {Feature}ListParams 
} from '../types';
import type { PaginatedResponse } from '@/core/api/types';

export const {feature}Api = {
  /**
   * List {feature}s with optional filtering and pagination
   */
  list: async (params?: {Feature}ListParams) => {
    const response = await apiClient.get<PaginatedResponse<{Feature}>>(
      '/{feature}s',
      { params }
    );
    return response.data;
  },

  /**
   * Get a single {feature} by ID
   */
  get: async (id: string) => {
    const response = await apiClient.get<{Feature}>(`/{feature}s/${id}`);
    return response.data;
  },

  /**
   * Create a new {feature}
   */
  create: async (data: {Feature}Create) => {
    const response = await apiClient.post<{Feature}>('/{feature}s', data);
    return response.data;
  },

  /**
   * Update an existing {feature}
   */
  update: async (id: string, data: {Feature}Update) => {
    const response = await apiClient.put<{Feature}>(`/{feature}s/${id}`, data);
    return response.data;
  },

  /**
   * Delete a {feature}
   */
  delete: async (id: string) => {
    await apiClient.delete(`/{feature}s/${id}`);
  },
};
```

## Core API Client Setup

```typescript
// core/api/client.ts
import axios, { AxiosInstance, AxiosError } from 'axios';
import type { ApiError } from './types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const apiClient: AxiosInstance = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
});

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ApiError>) => {
    const message = error.response?.data?.error?.message || 'An error occurred';
    return Promise.reject(new Error(message));
  }
);
```

## Core Types

```typescript
// core/api/types.ts
export interface ApiResponse<T> {
  success: boolean;
  data: T;
  meta?: {
    request_id: string;
    timestamp: string;
  };
}

export interface ApiError {
  success: false;
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface PaginationParams {
  page?: number;
  page_size?: number;
}
```

## Checklist

- [ ] API client uses apiClient from core
- [ ] All methods are async and return typed data
- [ ] List method supports pagination params
- [ ] Error handling via interceptor
- [ ] JSDoc comments for each method
- [ ] Proper TypeScript types for all parameters and returns
