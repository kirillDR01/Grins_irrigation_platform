/**
 * AI Scheduling-specific TypeScript types.
 * Matches backend schemas in src/grins_platform/schemas/ai_scheduling.py
 */

// ---- Criteria ---------------------------------------------------------------

export interface CriterionResult {
  criterion_number: number;
  criterion_name: string;
  score: number;
  weight: number;
  is_hard: boolean;
  is_satisfied: boolean;
  explanation: string;
}

// ---- Chat -------------------------------------------------------------------

export interface ScheduleChange {
  change_type: string;
  job_id: string;
  staff_id: string;
  old_slot: string | null;
  new_slot: string | null;
  explanation: string;
}

export interface ChatRequest {
  message: string;
  session_id?: string;
}

/**
 * Mirrors `CriterionUsage` in `src/grins_platform/schemas/ai_scheduling.py`.
 */
export interface CriterionUsage {
  number: number;
  name: string;
}

export interface ChatResponse {
  response: string;
  /** Persistent multi-turn session id; echo back on the next request. */
  session_id?: string | null;
  schedule_changes?: ScheduleChange[] | null;
  clarifying_questions?: string[] | null;
  change_request_id?: string | null;
  /** Subset of the 30 scheduling criteria that drove this response. */
  criteria_used?: CriterionUsage[] | null;
  /** "Mon: 10 jobs, Tue: 8 jobs" style summary when a solution is in scope. */
  schedule_summary?: string | null;
}

// ---- Pre-job ----------------------------------------------------------------

export interface PreJobChecklist {
  job_type: string;
  customer_name: string;
  customer_address: string;
  required_equipment: string[];
  known_issues: string | null;
  gate_code: string | null;
  special_instructions: string | null;
  estimated_duration: number;
}
