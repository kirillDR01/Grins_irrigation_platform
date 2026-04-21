/**
 * AppointmentCommunicationTimeline (Gap 11).
 *
 * Renders a collapsible "Communication" section inside the
 * AppointmentDetail modal. Pure — receives timeline data via props and
 * emits no mutations. The parent owns the fetching hook.
 */

import { format, formatDistanceToNow } from 'date-fns';
import {
  AlertTriangle,
  Ban,
  Check,
  ChevronDown,
  MessageCircle,
  MessageSquare,
  Send,
} from 'lucide-react';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import type {
  AppointmentTimelineResponse,
  TimelineEvent,
  TimelineEventKind,
} from '../types';

interface AppointmentCommunicationTimelineProps {
  data: AppointmentTimelineResponse | undefined;
  isLoading: boolean;
  error: Error | null;
}

const KIND_ICON: Record<
  TimelineEventKind,
  React.ComponentType<{ className?: string }>
> = {
  outbound_sms: MessageSquare,
  inbound_reply: MessageCircle,
  reschedule_opened: AlertTriangle,
  reschedule_resolved: Check,
  opt_out: Ban,
  opt_in: Send,
};

const KIND_COLOR: Record<TimelineEventKind, string> = {
  outbound_sms: 'text-slate-500',
  inbound_reply: 'text-teal-600',
  reschedule_opened: 'text-amber-600',
  reschedule_resolved: 'text-emerald-600',
  opt_out: 'text-red-600',
  opt_in: 'text-emerald-600',
};

export function AppointmentCommunicationTimeline({
  data,
  isLoading,
  error,
}: AppointmentCommunicationTimelineProps) {
  if (isLoading) {
    return (
      <div
        className="p-3 bg-slate-50 rounded-xl"
        data-testid="appointment-communication-timeline"
      >
        <Skeleton className="h-4 w-40" />
        <Skeleton className="mt-2 h-12 w-full" />
      </div>
    );
  }

  if (error) {
    return (
      <Alert
        variant="destructive"
        data-testid="appointment-communication-timeline"
      >
        Failed to load communication timeline.
      </Alert>
    );
  }

  if (!data) {
    return null;
  }

  const events = data.events;
  const summary =
    data.last_event_at !== null
      ? `Last activity ${formatDistanceToNow(new Date(data.last_event_at), {
          addSuffix: true,
        })}`
      : 'No activity';

  return (
    <details
      className="group p-3 bg-slate-50 rounded-xl"
      data-testid="appointment-communication-timeline"
    >
      <summary className="flex items-center gap-2 cursor-pointer list-none [&::-webkit-details-marker]:hidden">
        <MessageCircle className="h-3.5 w-3.5 text-slate-400" />
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex-1">
          Communication
        </p>
        <span className="text-xs text-slate-500">{summary}</span>
        <ChevronDown
          className="h-4 w-4 text-slate-400 transition-transform group-open:rotate-180"
          data-testid="toggle-communication-timeline-btn"
        />
      </summary>
      <div className="mt-2 pl-5 space-y-2">
        {events.length === 0 ? (
          <p className="text-xs text-slate-500">
            No customer communication yet.
          </p>
        ) : (
          events.map((event) => (
            <TimelineRow key={`${event.kind}-${event.id}`} event={event} />
          ))
        )}
      </div>
    </details>
  );
}

interface TimelineRowProps {
  event: TimelineEvent;
}

function TimelineRow({ event }: TimelineRowProps) {
  const Icon = KIND_ICON[event.kind];
  const color = KIND_COLOR[event.kind];
  const occurred = new Date(event.occurred_at);
  const relative = formatDistanceToNow(occurred, { addSuffix: true });
  const absolute = format(occurred, 'PPp');
  const deliveryStatus =
    event.kind === 'outbound_sms'
      ? (event.details['delivery_status'] as string | undefined)
      : undefined;
  const rawBody =
    event.kind === 'inbound_reply'
      ? (event.details['raw_reply_body'] as string | undefined)
      : undefined;

  return (
    <div
      className="flex items-start gap-2 text-xs"
      data-testid={`timeline-event-${event.id}`}
    >
      <Icon className={`h-3.5 w-3.5 mt-0.5 shrink-0 ${color}`} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-medium text-slate-700">{event.summary}</span>
          {deliveryStatus && (
            <Badge
              variant="secondary"
              className="text-[10px] px-1 py-0 h-4 bg-slate-100 text-slate-600"
            >
              {deliveryStatus}
            </Badge>
          )}
          <span className="text-slate-400" title={absolute}>
            {relative}
          </span>
        </div>
        {rawBody && (
          <p className="text-[11px] text-slate-500 mt-0.5 line-clamp-2">
            &quot;{rawBody}&quot;
          </p>
        )}
      </div>
    </div>
  );
}
