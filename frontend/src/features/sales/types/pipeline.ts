// Sales pipeline types — CRM Changes Update 2 Req 14.1, 14.2

export type SalesEntryStatus =
  | 'schedule_estimate'
  | 'estimate_scheduled'
  | 'send_estimate'
  | 'pending_approval'
  | 'send_contract'
  | 'closed_won'
  | 'closed_lost';

export interface SalesEntry {
  id: string;
  customer_id: string;
  property_id: string | null;
  lead_id: string | null;
  job_type: string | null;
  status: SalesEntryStatus;
  last_contact_date: string | null;
  notes: string | null;
  override_flag: boolean;
  closed_reason: string | null;
  signwell_document_id: string | null;
  created_at: string;
  updated_at: string;
  customer_name: string | null;
  customer_phone: string | null;
  property_address: string | null;
}

export interface SalesPipelineListResponse {
  items: SalesEntry[];
  total: number;
  summary: Record<string, number>;
}

export interface SalesEntryStatusUpdate {
  status: SalesEntryStatus;
  closed_reason?: string;
}

// Status display config
export const SALES_STATUS_CONFIG: Record<
  SalesEntryStatus,
  { label: string; className: string; action: string | null }
> = {
  schedule_estimate: {
    label: 'Schedule Estimate',
    className: 'bg-orange-100 text-orange-700',
    action: 'Schedule Estimate',
  },
  estimate_scheduled: {
    label: 'Estimate Scheduled',
    className: 'bg-blue-100 text-blue-700',
    action: 'Send Estimate',
  },
  send_estimate: {
    label: 'Send Estimate',
    className: 'bg-violet-100 text-violet-700',
    action: 'Mark Sent',
  },
  pending_approval: {
    label: 'Pending Approval',
    className: 'bg-amber-100 text-amber-700',
    action: 'Send Contract',
  },
  send_contract: {
    label: 'Send Contract',
    className: 'bg-teal-100 text-teal-700',
    action: 'Convert to Job',
  },
  closed_won: {
    label: 'Closed Won',
    className: 'bg-emerald-100 text-emerald-700',
    action: null,
  },
  closed_lost: {
    label: 'Closed Lost',
    className: 'bg-slate-100 text-slate-500',
    action: null,
  },
};

// Terminal statuses have no further actions
export const TERMINAL_STATUSES: SalesEntryStatus[] = ['closed_won', 'closed_lost'];

// All valid statuses for manual override dropdown
export const ALL_STATUSES: SalesEntryStatus[] = [
  'schedule_estimate',
  'estimate_scheduled',
  'send_estimate',
  'pending_approval',
  'send_contract',
  'closed_won',
  'closed_lost',
];
