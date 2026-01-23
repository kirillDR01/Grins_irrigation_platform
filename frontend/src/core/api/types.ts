// Standard API response types

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  meta?: {
    request_id?: string;
    timestamp?: string;
  };
}

export interface ApiError {
  success: false;
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
  meta?: {
    request_id?: string;
    timestamp?: string;
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

// Common entity types
export interface BaseEntity {
  id: string;
  created_at: string;
  updated_at: string;
}
