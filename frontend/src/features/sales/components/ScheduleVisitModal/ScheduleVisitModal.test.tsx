import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { ScheduleVisitModal } from './ScheduleVisitModal';
import type { SalesEntry, SalesCalendarEvent } from '../../types/pipeline';

vi.mock('@/features/staff/hooks/useStaff', () => ({
  useStaff: () => ({
    data: {
      items: [
        { id: 'me', name: 'Kirill' },
        { id: 'mike', name: 'Mike R.' },
      ],
    },
    isLoading: false,
  }),
  staffKeys: { all: ['staff'], lists: () => ['staff', 'list'] },
}));

vi.mock('@/features/customers', () => ({
  useCustomer: () => ({ data: null, isLoading: false, error: null }),
}));

vi.mock('../../hooks/useSalesPipeline', async () => {
  const actual = await vi.importActual<
    typeof import('../../hooks/useSalesPipeline')
  >('../../hooks/useSalesPipeline');
  return {
    ...actual,
    useSalesCalendarEvents: () => ({ data: [], isLoading: false }),
    useCreateCalendarEvent: () => ({
      mutateAsync: vi.fn(),
      isPending: false,
    }),
    useUpdateCalendarEvent: () => ({
      mutateAsync: vi.fn(),
      isPending: false,
    }),
  };
});

const mkEntry = (overrides: Partial<SalesEntry> = {}): SalesEntry => ({
  id: 'entry-1',
  customer_id: 'cust-1',
  property_id: null,
  lead_id: null,
  job_type: 'Spring startup',
  status: 'schedule_estimate',
  last_contact_date: null,
  notes: null,
  override_flag: false,
  closed_reason: null,
  signwell_document_id: null,
  created_at: '2026-04-25T00:00:00Z',
  updated_at: '2026-04-25T00:00:00Z',
  customer_name: 'Viktor Petrov',
  customer_phone: '+15551234567',
  property_address: '1428 Maple Dr',
  ...overrides,
});

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return React.createElement(
    QueryClientProvider,
    { client: qc },
    React.createElement(MemoryRouter, null, children),
  );
}

describe('ScheduleVisitModal', () => {
  it('renders title "Schedule estimate visit" for new bookings', () => {
    render(
      <ScheduleVisitModal
        entry={mkEntry()}
        currentEvent={null}
        open
        onOpenChange={() => {}}
      />,
      { wrapper },
    );
    expect(screen.getByText('Schedule estimate visit')).toBeInTheDocument();
  });

  it('renders title "Reschedule estimate visit" when currentEvent is provided', () => {
    const event: SalesCalendarEvent = {
      id: 'e1',
      sales_entry_id: 'entry-1',
      customer_id: 'cust-1',
      title: 't',
      scheduled_date: '2026-04-23',
      start_time: '14:00:00',
      end_time: '15:00:00',
      notes: null,
      assigned_to_user_id: null,
      created_at: '',
      updated_at: '',
    };
    render(
      <ScheduleVisitModal
        entry={mkEntry({ status: 'estimate_scheduled' })}
        currentEvent={event}
        open
        onOpenChange={() => {}}
      />,
      { wrapper },
    );
    expect(screen.getByText('Reschedule estimate visit')).toBeInTheDocument();
  });

  it('Confirm button is disabled when pick is null', () => {
    render(
      <ScheduleVisitModal
        entry={mkEntry()}
        currentEvent={null}
        open
        onOpenChange={() => {}}
      />,
      { wrapper },
    );
    expect(screen.getByTestId('schedule-visit-confirm-btn')).toBeDisabled();
  });

  it('renders the customer card with the entry name', () => {
    render(
      <ScheduleVisitModal
        entry={mkEntry()}
        currentEvent={null}
        open
        onOpenChange={() => {}}
      />,
      { wrapper },
    );
    expect(screen.getByTestId('schedule-visit-customer-card')).toHaveTextContent(
      'Viktor Petrov',
    );
  });

  it('renders the assignee dropdown', () => {
    render(
      <ScheduleVisitModal
        entry={mkEntry()}
        currentEvent={null}
        open
        onOpenChange={() => {}}
      />,
      { wrapper },
    );
    expect(screen.getByTestId('schedule-visit-assignee')).toBeInTheDocument();
  });

  it('shows the no-pick summary message when pick is null', () => {
    render(
      <ScheduleVisitModal
        entry={mkEntry()}
        currentEvent={null}
        open
        onOpenChange={() => {}}
      />,
      { wrapper },
    );
    expect(
      screen.getByTestId('schedule-visit-pick-summary'),
    ).toHaveTextContent(/No time picked yet/i);
  });

  it('does not render when open=false', () => {
    render(
      <ScheduleVisitModal
        entry={mkEntry()}
        currentEvent={null}
        open={false}
        onOpenChange={() => {}}
      />,
      { wrapper },
    );
    expect(screen.queryByTestId('schedule-visit-modal')).not.toBeInTheDocument();
  });

  it('renders the new CTA copy with a trailing arrow icon for new bookings', () => {
    render(
      <ScheduleVisitModal
        entry={mkEntry()}
        currentEvent={null}
        open
        onOpenChange={() => {}}
      />,
      { wrapper },
    );
    const btn = screen.getByTestId('schedule-visit-confirm-btn');
    // sales-pipeline-estimate-visit-confirmation-lifecycle Task 14:
    // submit button now reads "Send confirmation text message" — clicking
    // both books the slot and triggers the Y/R/C SMS atomically.
    expect(btn).toHaveTextContent('Send confirmation text message');
    expect(btn.querySelector('svg')).not.toBeNull();
    // Calendar-emoji prefix from v1 must be gone.
    expect(btn.textContent ?? '').not.toContain('📅');
  });

  it('renders "Update appointment" without an arrow on the reschedule path', () => {
    const event: SalesCalendarEvent = {
      id: 'e1',
      sales_entry_id: 'entry-1',
      customer_id: 'cust-1',
      title: 't',
      scheduled_date: '2026-04-23',
      start_time: '14:00:00',
      end_time: '15:00:00',
      notes: null,
      assigned_to_user_id: null,
      created_at: '',
      updated_at: '',
    };
    render(
      <ScheduleVisitModal
        entry={mkEntry({ status: 'estimate_scheduled' })}
        currentEvent={event}
        open
        onOpenChange={() => {}}
      />,
      { wrapper },
    );
    const btn = screen.getByTestId('schedule-visit-confirm-btn');
    // Reschedule path: button reads "Update & resend confirmation text"
    // because the new slot triggers a fresh Y/R/C SMS so the customer
    // sees the new time. See
    // sales-pipeline-estimate-visit-confirmation-lifecycle Task 14.
    expect(btn).toHaveTextContent('Update & resend confirmation text');
    expect(btn.textContent ?? '').not.toContain('📅');
    expect(btn.querySelector('svg')).not.toBeNull();
  });

  it('renders the stage pill with the entry status label', () => {
    render(
      <ScheduleVisitModal
        entry={mkEntry()}
        currentEvent={null}
        open
        onOpenChange={() => {}}
      />,
      { wrapper },
    );
    expect(screen.getByText(/Stage 1 · Schedule Estimate/)).toBeInTheDocument();
  });

  it('renders the SAL-XXXX id pill', () => {
    render(
      <ScheduleVisitModal
        entry={mkEntry()}
        currentEvent={null}
        open
        onOpenChange={() => {}}
      />,
      { wrapper },
    );
    expect(screen.getByText(/^SAL-/)).toBeInTheDocument();
  });

  it('renders the "From lead" tag when entry.lead_id is set', () => {
    render(
      <ScheduleVisitModal
        entry={mkEntry({ lead_id: 'lead-abc' })}
        currentEvent={null}
        open
        onOpenChange={() => {}}
      />,
      { wrapper },
    );
    expect(screen.getByText('From lead')).toBeInTheDocument();
  });

  it('does NOT render the "From lead" tag when entry.lead_id is null', () => {
    render(
      <ScheduleVisitModal
        entry={mkEntry({ lead_id: null })}
        currentEvent={null}
        open
        onOpenChange={() => {}}
      />,
      { wrapper },
    );
    expect(screen.queryByText('From lead')).not.toBeInTheDocument();
  });
});
