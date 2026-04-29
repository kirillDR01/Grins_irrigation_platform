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

export interface ChatResponse {
  response: string;
  session_id: string;
  schedule_changes: ScheduleChange[];
  clarifying_questions: string[];
  change_request_id: string | null;
  criteria_used: Array<{ number: number; name: string }>;
  schedule_summary: string | null;
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
