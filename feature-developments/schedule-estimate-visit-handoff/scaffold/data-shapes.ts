// data-shapes.ts
// Types shared across the Schedule Estimate Visit modal and its sub-components.
// Mirror the API contract documented in SPEC.md §4.

/** A picked slot. `start`/`end` are minutes from midnight in the business's local TZ. */
export type Pick = {
  date: string;   // 'YYYY-MM-DD'
  start: number;  // minutes from midnight (inclusive)
  end: number;    // minutes from midnight (exclusive)
};

/** Read-only customer info shown at the top of the modal. */
export type CustomerSummary = {
  id: string;
  name: string;
  phone?: string;
  email?: string;
  address?: string;
  job_summary: string;        // e.g. "Sprinkler install"
  source: 'lead' | 'manual';  // for the "from Leads tab" tag
};

/** An existing estimate visit on the calendar. */
export type EstimateBlock = {
  id: string;
  date: string;        // 'YYYY-MM-DD'
  start: number;
  end: number;
  customer_name: string;
  job_summary: string;
  assigned_to: string; // user id
};

/** Form-field shape (the inputs in the left column). */
export type ScheduleForm = {
  date: string;            // 'YYYY-MM-DD'
  startMin: number;        // minutes from midnight
  durationMin: 30 | 60 | 90 | 120;
  assignedTo: string;      // user id
  internalNotes?: string;
  sendConfirmationText: boolean;
};

/** Server payload for POST /api/sales/:entryId/schedule-visit */
export type ScheduleVisitRequest = {
  date: string;
  start: number;
  end: number;
  assigned_to: string;
  internal_notes?: string;
  send_confirmation_text?: boolean;
};

/** Server response for POST /api/sales/:entryId/schedule-visit */
export type ScheduleVisitResponse = {
  appointment_id: string;
  entry: SalesEntry;
};

/** Slim shape of the parent SalesEntry — see existing app types for the canonical version. */
export type SalesEntry = {
  id: string;
  status:
    | 'lead_captured'
    | 'estimate_scheduled'
    | 'estimate_sent'
    | 'won'
    | 'lost';
  customer: CustomerSummary;
  appointment?: {
    id: string;
    date: string;
    start: number;
    end: number;
    assigned_to: string;
  };
};

/** Top-level props for `<ScheduleVisitModal />`. */
export type ScheduleVisitModalProps = {
  entry: SalesEntry;
  /** Fired on successful submit. Parent should swap `entry` in the store. */
  onScheduled: (updated: SalesEntry) => void;
  /** Close handler. Should warn if the form is dirty. */
  onClose: () => void;
  /** Optional — defaults to current user. */
  defaultAssigneeId?: string;
  /** Optional — for tests. Defaults to `new Date()`. */
  now?: Date;
};
