// ============================================================
// ActivityStrip.tsx — one-line activity feed for current stage
// Drop at: frontend/src/features/sales/components/ActivityStrip.tsx
// ============================================================

import { formatDistanceToNow, format } from 'date-fns';
import type { ActivityEvent, ActivityEventKind } from '../types/pipeline';

const GLYPH: Record<ActivityEventKind, string> = {
  moved_from_leads:    '🆕',
  visit_scheduled:     '📅',
  visit_completed:     '📅',
  estimate_sent:       '✉',
  estimate_viewed:     '👁',
  nudge_sent:          '⏰',
  nudge_next:          '⏰',
  approved:            '✅',
  declined:            '✕',
  agreement_uploaded:  '📄',
  converted:           '🛠',
  job_created:         '📄',
  customer_created:    '👤',
};

interface ActivityStripProps {
  events: ActivityEvent[];
}

export function ActivityStrip({ events }: ActivityStripProps) {
  if (!events.length) return null;
  return (
    <div
      className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm px-1"
      data-testid="activity-strip"
    >
      {events.map((e, i) => (
        <span key={`${e.kind}-${i}`} className="flex items-center gap-x-2">
          <EventChip event={e} />
          {i < events.length - 1 && <span className="text-slate-300" aria-hidden>·</span>}
        </span>
      ))}
    </div>
  );
}

function EventChip({ event }: { event: ActivityEvent }) {
  const toneClass = {
    done:    'text-slate-600',
    wait:    'text-amber-700 font-medium',
    neutral: 'text-slate-500',
  }[event.tone];
  return (
    <span
      className={toneClass}
      data-testid={`activity-event-${event.kind}`}
    >
      <span className="mr-1" aria-hidden>{GLYPH[event.kind]}</span>
      {event.label}
    </span>
  );
}

// ────────── Helpers a host can use to build the events list ──────────

export function fmtRelative(iso: string): string {
  return formatDistanceToNow(new Date(iso), { addSuffix: true });
}

export function fmtDateTime(iso: string): string {
  return format(new Date(iso), 'MMM d, h:mm a');
}
