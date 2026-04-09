/**
 * Render the poll options block that gets appended to the campaign message body.
 */

import { format } from 'date-fns';
import type { PollOption } from '../types/campaign';

export function defaultPollLabel(startDate: string | null): string {
  if (!startDate) return '';
  try {
    return `Week of ${format(new Date(startDate + 'T00:00:00'), 'MMM d')}`;
  } catch {
    return '';
  }
}

/**
 * Build the text block appended to the message body.
 *
 * The trailing `\n\n` ensures the STOP footer lands on its own paragraph
 * below the options list instead of gluing onto the last option line.
 * The backend `_render_poll_block` in `background_jobs.py` must stay in sync.
 */
export function renderPollOptionsBlock(options: PollOption[]): string {
  if (options.length === 0) return '';
  const lines = options.map((o) => `${o.key}. ${o.label || '(no label)'}`);
  const keys = options.map((o) => o.key).join(', ');
  return `\n\nReply with ${keys}:\n${lines.join('\n')}\n\n`;
}

/**
 * Per-row validation for poll options.
 *
 * Mirrors the backend Pydantic `PollOption` schema
 * (`src/grins_platform/schemas/campaign_response.py`): label 1-120 chars,
 * start/end dates required, end >= start.
 */
export interface PollOptionRowErrors {
  label: string | null;
  start: string | null;
  end: string | null;
  range: string | null;
}

export interface PollOptionsValidation {
  rowErrors: PollOptionRowErrors[];
  valid: boolean;
}

export function validatePollOptions(options: PollOption[]): PollOptionsValidation {
  const rowErrors = options.map((o): PollOptionRowErrors => {
    const label =
      !o.label || o.label.trim().length === 0 ? 'Label required' : null;
    const start = !o.start_date ? 'Start date required' : null;
    const end = !o.end_date ? 'End date required' : null;
    const range =
      o.start_date && o.end_date && o.end_date < o.start_date
        ? 'End date must be on or after start date'
        : null;
    return { label, start, end, range };
  });
  const valid =
    options.length >= 2 &&
    rowErrors.every((e) => !e.label && !e.start && !e.end && !e.range);
  return { rowErrors, valid };
}
