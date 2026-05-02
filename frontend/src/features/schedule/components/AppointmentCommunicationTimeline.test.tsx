/**
 * Tests for AppointmentCommunicationTimeline (Gap 11).
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AppointmentCommunicationTimeline } from './AppointmentCommunicationTimeline';
import type {
  AppointmentTimelineResponse,
  TimelineEventKind,
} from '../types';

function buildTimeline(
  overrides?: Partial<AppointmentTimelineResponse>,
): AppointmentTimelineResponse {
  return {
    appointment_id: 'appt-1',
    events: [],
    pending_reschedule_request: null,
    needs_review_reason: null,
    opt_out: null,
    last_event_at: null,
    ...overrides,
  };
}

describe('AppointmentCommunicationTimeline', () => {
  it('renders loading skeleton', () => {
    render(
      <AppointmentCommunicationTimeline
        data={undefined}
        isLoading={true}
        error={null}
      />,
    );
    expect(
      screen.getByTestId('appointment-communication-timeline'),
    ).toBeInTheDocument();
  });

  it('renders error alert when error is present', () => {
    render(
      <AppointmentCommunicationTimeline
        data={undefined}
        isLoading={false}
        error={new Error('boom')}
      />,
    );
    expect(screen.getByText(/failed to load/i)).toBeInTheDocument();
  });

  it('renders empty state with "No customer communication yet."', () => {
    render(
      <AppointmentCommunicationTimeline
        data={buildTimeline()}
        isLoading={false}
        error={null}
      />,
    );
    const section = screen.getByTestId('appointment-communication-timeline');
    expect(section).toBeInTheDocument();
    expect(section.tagName.toLowerCase()).toBe('details');
    expect(section.hasAttribute('open')).toBe(false);
    expect(
      screen.getByText(/no customer communication yet/i),
    ).toBeInTheDocument();
  });

  it('renders events in the provided (parent-sorted) order', () => {
    const timeline = buildTimeline({
      last_event_at: '2026-04-21T10:30:00Z',
      events: [
        {
          id: 'evt-1',
          kind: 'inbound_reply',
          occurred_at: '2026-04-21T10:30:00Z',
          summary: 'Customer replied: confirm',
          details: { raw_reply_body: 'Y' },
          source_id: 'src-1',
        },
        {
          id: 'evt-2',
          kind: 'outbound_sms',
          occurred_at: '2026-04-21T09:00:00Z',
          summary: 'Sent appointment confirmation',
          details: { delivery_status: 'delivered' },
          source_id: 'src-2',
        },
      ],
    });

    render(
      <AppointmentCommunicationTimeline
        data={timeline}
        isLoading={false}
        error={null}
      />,
    );

    const rows = screen.getAllByTestId(/^timeline-event-/);
    expect(rows).toHaveLength(2);
    expect(rows[0].getAttribute('data-testid')).toBe('timeline-event-evt-1');
    expect(rows[1].getAttribute('data-testid')).toBe('timeline-event-evt-2');
  });

  it('renders delivery status badge for outbound SMS and raw reply for inbound', () => {
    const timeline = buildTimeline({
      last_event_at: '2026-04-21T10:30:00Z',
      events: [
        {
          id: 'evt-1',
          kind: 'inbound_reply',
          occurred_at: '2026-04-21T10:30:00Z',
          summary: 'Customer replied: confirm',
          details: { raw_reply_body: 'Yes thanks' },
          source_id: null,
        },
        {
          id: 'evt-2',
          kind: 'outbound_sms',
          occurred_at: '2026-04-21T09:00:00Z',
          summary: 'Sent appointment confirmation',
          details: { delivery_status: 'delivered' },
          source_id: null,
        },
      ],
    });

    render(
      <AppointmentCommunicationTimeline
        data={timeline}
        isLoading={false}
        error={null}
      />,
    );

    expect(screen.getByText(/"Yes thanks"/)).toBeInTheDocument();
    expect(screen.getByText(/delivered/)).toBeInTheDocument();
  });

  it('renders payment_received event without throwing', () => {
    const timeline = buildTimeline({
      last_event_at: '2026-05-01T12:00:00Z',
      events: [
        {
          id: 'evt-pay-1',
          kind: 'payment_received',
          occurred_at: '2026-05-01T12:00:00Z',
          summary: 'Payment received: $100.00 (cash)',
          details: { payment_method: 'cash', amount: '100.00' },
          source_id: 'inv-1',
        },
      ],
    });

    render(
      <AppointmentCommunicationTimeline
        data={timeline}
        isLoading={false}
        error={null}
      />,
    );

    expect(
      screen.getByTestId('timeline-event-evt-pay-1'),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/payment received: \$100\.00/i),
    ).toBeInTheDocument();
  });

  it('renders unknown timeline kind without throwing and warns', () => {
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const timeline = buildTimeline({
      last_event_at: '2026-05-01T12:00:00Z',
      events: [
        {
          id: 'evt-unknown',
          kind: 'totally_made_up' as TimelineEventKind,
          occurred_at: '2026-05-01T12:00:00Z',
          summary: 'Unknown event kind',
          details: {},
          source_id: null,
        },
      ],
    });

    render(
      <AppointmentCommunicationTimeline
        data={timeline}
        isLoading={false}
        error={null}
      />,
    );

    expect(
      screen.getByTestId('timeline-event-evt-unknown'),
    ).toBeInTheDocument();
    expect(warnSpy).toHaveBeenCalledWith(
      'timeline.kind.unknown',
      expect.objectContaining({ kind: 'totally_made_up', id: 'evt-unknown' }),
    );
    warnSpy.mockRestore();
  });
});
