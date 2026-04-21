// ============================================================
// Sales pipeline — type source of truth for this handoff
// Merge into: frontend/src/features/sales/types/pipeline.ts
// ============================================================

// ─────────────────────────────────────────────────────────────
// Existing types (unchanged — kept here for completeness)
// ─────────────────────────────────────────────────────────────

export type SalesEntryStatus =
  | 'schedule_estimate'
  | 'estimate_scheduled'
  | 'send_estimate'
  | 'pending_approval'
  | 'send_contract'     // ← displayed as "Convert to Job" in the new UI
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

// ─────────────────────────────────────────────────────────────
// NEW — Stage-stepper contract
// The stepper collapses 5 operational stages into 3 phases.
// `estimate_scheduled` is a sub-state of the Schedule phase
// and does NOT get its own stepper node.
// ─────────────────────────────────────────────────────────────

export type StageKey =
  | 'schedule_estimate'  // step 1
  | 'send_estimate'      // step 2
  | 'pending_approval'   // step 3
  | 'send_contract'      // step 4 — labelled "Convert to Job"
  | 'closed_won';        // step 5

export type StagePhase = 'plan' | 'sign' | 'close';

export interface StageDef {
  key: StageKey;
  index: 0 | 1 | 2 | 3 | 4;
  shortLabel: string;   // stepper label, e.g. "Schedule Estimate"
  phase: StagePhase;
}

export const STAGES: readonly StageDef[] = [
  { key: 'schedule_estimate', index: 0, shortLabel: 'Schedule Estimate',  phase: 'plan'  },
  { key: 'send_estimate',     index: 1, shortLabel: 'Send Estimate',      phase: 'sign'  },
  { key: 'pending_approval',  index: 2, shortLabel: 'Pending Approval',   phase: 'sign'  },
  { key: 'send_contract',     index: 3, shortLabel: 'Convert to Job',     phase: 'close' },
  { key: 'closed_won',        index: 4, shortLabel: 'Closed Won',         phase: 'close' },
] as const;

export const STAGE_INDEX: Record<StageKey, number> = {
  schedule_estimate: 0,
  send_estimate:     1,
  pending_approval:  2,
  send_contract:     3,
  closed_won:        4,
};

/** Map raw DB status → stepper stage key. `estimate_scheduled` collapses to step 1. */
export function statusToStageKey(s: SalesEntryStatus): StageKey | null {
  if (s === 'closed_lost') return null;               // stepper hidden; show lost banner
  if (s === 'estimate_scheduled') return 'schedule_estimate';
  return s as StageKey;
}

// ─────────────────────────────────────────────────────────────
// NEW — Age-in-stage thresholds (Pipeline List chip + summary)
// Tuned per stage. pending_approval has a longer leash because
// customer wait is normal. Unit = calendar days since entering
// the current stage (derived from updated_at + notes timeline).
// ─────────────────────────────────────────────────────────────

export type AgeBucket = 'fresh' | 'stale' | 'stuck';

export interface AgeThresholds {
  /** ≤ this many days → fresh */
  freshMax: number;
  /** ≤ this many days → stale; above → stuck */
  staleMax: number;
}

export const AGE_THRESHOLDS: Record<StageKey, AgeThresholds> = {
  schedule_estimate: { freshMax: 3, staleMax: 7  },
  send_estimate:     { freshMax: 3, staleMax: 7  },
  pending_approval:  { freshMax: 4, staleMax: 10 },  // longer leash
  send_contract:     { freshMax: 3, staleMax: 7  },
  closed_won:        { freshMax: 999, staleMax: 999 }, // never ages
};

export interface StageAge {
  days: number;
  bucket: AgeBucket;
  /** True when bucket === 'stuck'. Drives the "Needs Follow-Up" summary count. */
  needsFollowup: boolean;
}

// ─────────────────────────────────────────────────────────────
// NEW — Activity feed event model (one-line strip per entry)
// Derived client-side from the existing fields; no new endpoint.
// ─────────────────────────────────────────────────────────────

export type ActivityEventKind =
  | 'moved_from_leads'       // created_at
  | 'visit_scheduled'        // estimate_scheduled entered
  | 'visit_completed'        // estimate_scheduled → send_estimate
  | 'estimate_sent'          // send_estimate → pending_approval
  | 'estimate_viewed'        // signwell webhook (if available)
  | 'nudge_sent'             // auto-follow-up fired
  | 'nudge_next'             // synthetic: next scheduled nudge
  | 'approved'               // pending_approval → send_contract
  | 'declined'               // pending_approval → closed_lost
  | 'agreement_uploaded'     // signwell_document_id set while send_contract
  | 'converted'              // send_contract → closed_won
  | 'job_created'            // synthetic companion to converted
  | 'customer_created';      // synthetic companion to converted

export interface ActivityEvent {
  kind: ActivityEventKind;
  /** ISO timestamp */
  at: string;
  /** Display tone: done=✓ past, wait=⏳ open, neutral=informational */
  tone: 'done' | 'wait' | 'neutral';
  /** Short human label, already localised. */
  label: string;
}

// ─────────────────────────────────────────────────────────────
// NEW — Now-card content contract
// A pure function of stage + a small bag of booleans decides
// pill / title / copy / primary action / dropzone / lock banner.
// Keep the mapping declarative; no component-internal branching.
// ─────────────────────────────────────────────────────────────

export type NowPill =
  | { tone: 'you';  label: 'Your move' }
  | { tone: 'cust'; label: 'Waiting on customer' }
  | { tone: 'done'; label: 'Complete' };

export interface NowCardInputs {
  stage: StageKey;
  /** Has an uploaded estimate PDF (controls send_estimate variant + lock). */
  hasEstimateDoc: boolean;
  /** Has a counter-signed agreement PDF (controls send_contract variant + lock). */
  hasSignedAgreement: boolean;
  /** Customer has an email on file (controls email-sign button lock). */
  hasCustomerEmail: boolean;
  /** Current "Week Of" target chosen in the send_contract picker. */
  weekOf?: string | null;
}

export interface NowCardContent {
  pill: NowPill;
  /** Headline. Plain string (no HTML). */
  title: string;
  /** Body copy. Supports narrow inline markup: <em>, <b>. */
  copyHtml: string;
  /** Which dropzone to render, if any. */
  dropzone?: { kind: 'estimate' | 'agreement'; filled: boolean };
  /** Show the auto-nudge schedule block. Only true for pending_approval. */
  showNudgeSchedule?: boolean;
  /** Show the Week-Of chip picker. Only true for send_contract. */
  showWeekOfPicker?: boolean;
  /** Actions — ordered. The primary is rendered as shadcn default; rest as outline/ghost. */
  actions: NowAction[];
  /** Optional red banner shown below actions (e.g. "No estimate PDF yet."). */
  lockBanner?: { textHtml: string };
}

export type NowAction =
  | { kind: 'primary';  label: string; testId: string; onClickId: NowActionId; disabled?: boolean; icon?: LucideIconName }
  | { kind: 'outline';  label: string; testId: string; onClickId: NowActionId; disabled?: boolean; icon?: LucideIconName }
  | { kind: 'ghost';    label: string; testId: string; onClickId: NowActionId; disabled?: boolean; icon?: LucideIconName }
  | { kind: 'danger';   label: string; testId: string; onClickId: NowActionId; disabled?: boolean; icon?: LucideIconName }
  | { kind: 'locked';   label: string; testId: string; reason: string };  // disabled + tooltip

/**
 * Identifiers for click handlers. The host (`SalesDetail`) binds these to real
 * mutations; `NowCard` never calls mutations directly. This keeps the component
 * pure & testable.
 */
export type NowActionId =
  | 'schedule_visit'
  | 'text_confirmation'
  | 'upload_estimate'
  | 'send_estimate_email'
  | 'add_customer_email'
  | 'skip_advance'
  | 'mark_approved_manual'
  | 'resend_estimate'
  | 'pause_nudges'
  | 'mark_declined'
  | 'upload_agreement'
  | 'convert_to_job'
  | 'view_job'
  | 'view_customer'
  | 'jump_to_schedule';

export type LucideIconName =
  | 'Calendar' | 'Mail' | 'MessageSquare' | 'Upload' | 'CheckCircle2'
  | 'XCircle' | 'RotateCw' | 'PauseCircle' | 'ArrowRight' | 'User' | 'Edit3' | 'Lock';

// ─────────────────────────────────────────────────────────────
// NEW — Auto-nudge schedule (pending_approval only)
// Computed client-side from the `estimate_sent` timestamp.
// ─────────────────────────────────────────────────────────────

export interface NudgeStep {
  /** Days since estimate_sent. -1 for the Monday loop sentinel. */
  dayOffset: number;
  /** 'done' | 'next' | 'future' | 'loop' */
  state: 'done' | 'next' | 'future' | 'loop';
  /** Date/time label, e.g. "Apr 11", "Tomorrow 9 AM", "Every Monday 9 AM". */
  when: string;
  /** Message shown to the customer. */
  message: string;
}

/** The standard 4-step cadence + weekly loop. */
export const NUDGE_CADENCE_DAYS: readonly number[] = [0, 2, 5, 8] as const;
