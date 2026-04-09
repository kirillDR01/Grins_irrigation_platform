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

/** Build the text block appended to the message body. */
export function renderPollOptionsBlock(options: PollOption[]): string {
  if (options.length === 0) return '';
  const lines = options.map((o) => `${o.key}. ${o.label || '(no label)'}`);
  const keys = options.map((o) => o.key).join(', ');
  return `\n\nReply with ${keys}:\n${lines.join('\n')}`;
}
