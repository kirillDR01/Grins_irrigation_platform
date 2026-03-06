import type { PaginationParams } from '@/core/api';

// Processing status enum values
export type ProcessingStatus = 'imported' | 'lead_created' | 'skipped' | 'error';

// Client type from Google Sheet
export type SheetClientType = 'new' | 'existing';

// Work request entity (Google Sheet submission)
export interface WorkRequest {
  id: string;
  sheet_row_number: number;
  timestamp: string | null;
  spring_startup: string | null;
  fall_blowout: string | null;
  summer_tuneup: string | null;
  repair_existing: string | null;
  new_system_install: string | null;
  addition_to_system: string | null;
  additional_services_info: string | null;
  date_work_needed_by: string | null;
  name: string | null;
  phone: string | null;
  email: string | null;
  city: string | null;
  address: string | null;
  additional_info: string | null;
  client_type: string | null;
  property_type: string | null;
  referral_source: string | null;
  landscape_hardscape: string | null;
  processing_status: ProcessingStatus;
  processing_error: string | null;
  lead_id: string | null;
  imported_at: string;
  created_at: string;
  updated_at: string;
}

// Sync status from poller
export interface SyncStatus {
  last_sync: string | null;
  is_running: boolean;
  last_error: string | null;
}

// Work request list query params
export interface WorkRequestListParams extends PaginationParams {
  processing_status?: ProcessingStatus;
  client_type?: SheetClientType;
  search?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

// Paginated work request response
export interface PaginatedWorkRequestResponse {
  items: WorkRequest[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// Status display helpers
export const PROCESSING_STATUS_LABELS: Record<ProcessingStatus, string> = {
  imported: 'Imported',
  lead_created: 'Lead Created',
  skipped: 'Skipped',
  error: 'Error',
};

export const CLIENT_TYPE_LABELS: Record<SheetClientType, string> = {
  new: 'New',
  existing: 'Existing',
};
