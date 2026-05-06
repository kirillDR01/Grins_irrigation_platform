// Sales pipeline types — CRM Changes Update 2 Req 14.1, 14.2
// Extended with stage walkthrough types — Req 1.1, 1.2, 1.3, 1.4

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
  // NEW-D: NULL = nudges active. Non-null = paused until this UTC ISO ts.
  nudges_paused_until: string | null;
  // NEW-D: NULL = visible in pipeline list. Non-null = dismissed at this ts.
  dismissed_at: string | null;
  created_at: string;
  updated_at: string;
  customer_name: string | null;
  customer_phone: string | null;
  customer_email: string | null;
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
    // Means: estimate sent; awaiting customer approval via portal click.
    // NOT a contract signature — that happens at send_contract → closed_won.
    label: 'Pending Approval',
    className: 'bg-amber-100 text-amber-700',
    action: 'Send Contract',
  },
  send_contract: {
    label: 'Convert to Job',
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

// Sales calendar event types — Req 15.1, 15.2, 15.3
/**
 * Y/R/C confirmation lifecycle status (migration 20260509_120000).
 *
 * - `pending`: confirmation SMS dispatched, awaiting customer reply
 * - `confirmed`: customer replied Y
 * - `reschedule_requested`: customer replied R, RescheduleRequest opened
 * - `cancelled`: customer replied C
 */
export type SalesCalendarEventConfirmationStatus =
  | 'pending'
  | 'confirmed'
  | 'reschedule_requested'
  | 'cancelled';

export interface SalesCalendarEvent {
  id: string;
  sales_entry_id: string;
  customer_id: string;
  title: string;
  scheduled_date: string;
  start_time: string | null;
  end_time: string | null;
  notes: string | null;
  assigned_to_user_id: string | null;
  confirmation_status: SalesCalendarEventConfirmationStatus;
  confirmation_status_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface SalesCalendarEventCreate {
  sales_entry_id: string;
  customer_id: string;
  title: string;
  scheduled_date: string;
  start_time?: string | null;
  end_time?: string | null;
  notes?: string | null;
  assigned_to_user_id?: string | null;
}

export interface SalesCalendarEventUpdate {
  title?: string;
  scheduled_date?: string;
  start_time?: string | null;
  end_time?: string | null;
  notes?: string | null;
  assigned_to_user_id?: string | null;
}

// ─────────────────────────────────────────────────────────────────────────────
// Stage walkthrough types — Req 1.1, 1.2, 1.3, 1.4
// ─────────────────────────────────────────────────────────────────────────────

/** The 5 canonical pipeline stages (excludes estimate_scheduled alias). */
export type StageKey =
  | 'schedule_estimate'
  | 'send_estimate'
  | 'pending_approval'
  | 'send_contract'
  | 'closed_won';

export type StagePhase = 'plan' | 'sign' | 'close';

export interface StageDef {
  key: StageKey;
  shortLabel: string;
  phase: StagePhase;
}

export const STAGES: StageDef[] = [
  { key: 'schedule_estimate', shortLabel: 'Schedule',  phase: 'plan'  },
  { key: 'send_estimate',     shortLabel: 'Estimate',  phase: 'sign'  },
  { key: 'pending_approval',  shortLabel: 'Approval',  phase: 'sign'  },
  { key: 'send_contract',     shortLabel: 'Contract',  phase: 'close' },
  { key: 'closed_won',        shortLabel: 'Closed',    phase: 'close' },
];

/** Lookup: StageKey → 0-based index in STAGES */
export const STAGE_INDEX: Record<StageKey, number> = Object.fromEntries(
  STAGES.map((s, i) => [s.key, i]),
) as Record<StageKey, number>;

/**
 * Map a SalesEntryStatus to its canonical StageKey.
 * `estimate_scheduled` is an alias for `schedule_estimate`.
 * `closed_lost` has no stage → null.
 */
export function statusToStageKey(status: SalesEntryStatus): StageKey | null {
  if (status === 'closed_lost') return null;
  if (status === 'estimate_scheduled') return 'schedule_estimate';
  return status as StageKey;
}

// ─────────────────────────────────────────────────────────────────────────────
// Age / health signal types — Req 1.2
// ─────────────────────────────────────────────────────────────────────────────

export type AgeBucket = 'fresh' | 'stale' | 'stuck';

export interface AgeThresholds {
  /** Days until entry becomes stale (exclusive upper bound for fresh). */
  freshMax: number;
  /** Days until entry becomes stuck (exclusive upper bound for stale). */
  staleMax: number;
}

/** Per-stage age thresholds (days). */
export const AGE_THRESHOLDS: Record<StageKey, AgeThresholds> = {
  schedule_estimate: { freshMax: 3,   staleMax: 7   },
  send_estimate:     { freshMax: 3,   staleMax: 7   },
  pending_approval:  { freshMax: 4,   staleMax: 10  },
  send_contract:     { freshMax: 3,   staleMax: 7   },
  closed_won:        { freshMax: 999, staleMax: 999 },
};

export interface StageAge {
  days: number;
  bucket: AgeBucket;
  needsFollowup: boolean;
}

// ─────────────────────────────────────────────────────────────────────────────
// Activity strip types — Req 1.3
// ─────────────────────────────────────────────────────────────────────────────

export type ActivityEventKind =
  | 'moved_from_leads'
  | 'visit_scheduled'
  | 'visit_completed'
  | 'estimate_sent'
  | 'estimate_viewed'
  | 'nudge_sent'
  | 'nudge_next'
  | 'approved'
  | 'declined'
  | 'agreement_uploaded'
  | 'converted'
  | 'job_created'
  | 'customer_created';

export interface ActivityEvent {
  kind: ActivityEventKind;
  label: string;
  tone: 'done' | 'wait' | 'neutral';
  at?: string; // ISO timestamp
}

// ─────────────────────────────────────────────────────────────────────────────
// NowCard types — Req 1.3
// ─────────────────────────────────────────────────────────────────────────────

export type LucideIconName =
  | 'Calendar'
  | 'Mail'
  | 'MessageSquare'
  | 'Upload'
  | 'CheckCircle2'
  | 'XCircle'
  | 'RotateCw'
  | 'PauseCircle'
  | 'ArrowRight'
  | 'User'
  | 'Edit3'
  | 'Lock';

export type NowActionId =
  | 'schedule_visit'
  | 'text_confirmation'
  | 'send_estimate_email'
  | 'add_customer_email'
  | 'skip_advance'
  | 'mark_approved_manual'
  | 'resend_estimate'
  | 'pause_nudges'
  | 'mark_declined'
  | 'convert_to_job'
  | 'view_job'
  | 'view_customer'
  | 'jump_to_schedule';

export type NowPill = {
  tone: 'you' | 'cust' | 'done';
  label: string;
};

export type NowAction =
  | {
      kind: 'primary' | 'outline' | 'ghost' | 'danger';
      label: string;
      testId: string;
      onClickId: NowActionId;
      icon?: LucideIconName;
      disabled?: boolean;
    }
  | {
      kind: 'locked';
      label: string;
      testId: string;
      reason: string;
    };

export interface NowCardContent {
  pill: NowPill;
  title: string;
  copyHtml: string;
  actions: NowAction[];
  dropzone?: { kind: 'estimate' | 'agreement'; filled: boolean };
  showNudgeSchedule?: boolean;
  showWeekOfPicker?: boolean;
  lockBanner?: { textHtml: string };
}

export interface NowCardInputs {
  stage: StageKey;
  hasEstimateDoc: boolean;
  hasSignedAgreement: boolean;
  hasCustomerEmail: boolean;
  weekOf?: string | null;
}

// ─────────────────────────────────────────────────────────────────────────────
// Auto-nudge types — Req 1.3
// ─────────────────────────────────────────────────────────────────────────────

export type NudgeStepState = 'done' | 'next' | 'future' | 'loop';

export interface NudgeStep {
  dayOffset: number; // -1 = weekly loop sentinel
  state: NudgeStepState;
  when: string;
  message: string;
}

/** Day offsets for the auto-nudge cadence (excluding the weekly loop). */
export const NUDGE_CADENCE_DAYS: readonly number[] = [0, 2, 5, 8] as const;

// ─────────────────────────────────────────────────────────────────────────────
// ScheduleVisitModal types
// ─────────────────────────────────────────────────────────────────────────────

/** A picked slot. start/end are minutes-from-midnight (business-local TZ). */
export type Pick = {
  date: string;   // 'YYYY-MM-DD'
  start: number;  // minutes (inclusive)
  end: number;    // minutes (exclusive)
};

/** Calendar render block — minute-based projection of a SalesCalendarEvent. */
export type EstimateBlock = {
  id: string;
  date: string;
  startMin: number;
  endMin: number;
  customerName: string;     // resolved at hook layer
  jobSummary: string;       // resolved at hook layer
  assignedToUserId: string | null;
};

/** Companion form-field state held alongside `pick` in useScheduleVisit. */
export type ScheduleVisitFormState = {
  durationMin: 30 | 60 | 90 | 120;
  assignedToUserId: string | null;
  internalNotes: string;
};
