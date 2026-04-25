import { renderHook, act, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';

const mockCreate = vi.fn();
const mockUpdate = vi.fn();

vi.mock('./useSalesPipeline', async () => {
  const actual =
    await vi.importActual<typeof import('./useSalesPipeline')>('./useSalesPipeline');
  return {
    ...actual,
    useSalesCalendarEvents: () => ({ data: [], isLoading: false }),
    useCreateCalendarEvent: () => ({
      mutateAsync: mockCreate,
      isPending: false,
    }),
    useUpdateCalendarEvent: () => ({
      mutateAsync: mockUpdate,
      isPending: false,
    }),
  };
});

import { useScheduleVisit } from './useScheduleVisit';
import type { SalesEntry, SalesCalendarEvent } from '../types/pipeline';

const NOW = new Date(2026, 4, 5, 9, 0); // Tue May 5, 2026, 9:00 AM

const mkEntry = (overrides: Partial<SalesEntry> = {}): SalesEntry => ({
  id: 'entry-1',
  customer_id: 'cust-1',
  property_id: null,
  lead_id: null,
  job_type: 'spring_startup',
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

const mkEvent = (overrides: Partial<SalesCalendarEvent> = {}): SalesCalendarEvent => ({
  id: 'event-1',
  sales_entry_id: 'entry-1',
  customer_id: 'cust-1',
  title: 'Estimate - Viktor Petrov',
  scheduled_date: '2026-05-07',
  start_time: '14:00:00',
  end_time: '15:00:00',
  notes: 'gate code 4412',
  assigned_to_user_id: 'staff-2',
  created_at: '',
  updated_at: '',
  ...overrides,
});

function makeWrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(
      QueryClientProvider,
      { client: qc },
      children,
    );
  };
}

describe('useScheduleVisit', () => {
  beforeEach(() => {
    mockCreate.mockReset();
    mockUpdate.mockReset();
  });

  it('initial pick is null for new bookings', () => {
    const { result } = renderHook(
      () =>
        useScheduleVisit({
          entry: mkEntry(),
          customerId: 'cust-1',
          customerName: 'Viktor Petrov',
          jobSummary: 'Spring startup',
          currentEvent: null,
          now: NOW,
        }),
      { wrapper: makeWrapper() },
    );
    expect(result.current.pick).toBeNull();
    expect(result.current.isReschedule).toBe(false);
  });

  it('initial pick is pre-filled when currentEvent is provided', () => {
    const event = mkEvent();
    const { result } = renderHook(
      () =>
        useScheduleVisit({
          entry: mkEntry({ status: 'estimate_scheduled' }),
          customerId: 'cust-1',
          customerName: 'Viktor Petrov',
          jobSummary: 'Spring startup',
          currentEvent: event,
          now: NOW,
        }),
      { wrapper: makeWrapper() },
    );
    expect(result.current.pick).toEqual({
      date: '2026-05-07',
      start: 14 * 60,
      end: 15 * 60,
    });
    expect(result.current.isReschedule).toBe(true);
  });

  it('setPickFromCalendarClick uses default duration 60', () => {
    const { result } = renderHook(
      () =>
        useScheduleVisit({
          entry: mkEntry(),
          customerId: 'cust-1',
          customerName: 'Viktor Petrov',
          jobSummary: '',
          currentEvent: null,
          now: NOW,
        }),
      { wrapper: makeWrapper() },
    );
    act(() => {
      result.current.setPickFromCalendarClick('2026-05-06', 14 * 60);
    });
    expect(result.current.pick).toEqual({
      date: '2026-05-06',
      start: 14 * 60,
      end: 14 * 60 + 60,
    });
  });

  it('setPickFromCalendarDrag sets pick + updates duration when 30/60/90/120', () => {
    const { result } = renderHook(
      () =>
        useScheduleVisit({
          entry: mkEntry(),
          customerId: 'cust-1',
          customerName: 'Viktor Petrov',
          jobSummary: '',
          currentEvent: null,
          now: NOW,
        }),
      { wrapper: makeWrapper() },
    );
    act(() => {
      result.current.setPickFromCalendarDrag(
        '2026-05-06',
        14 * 60,
        15 * 60 + 30,
      );
    });
    expect(result.current.pick).toEqual({
      date: '2026-05-06',
      start: 14 * 60,
      end: 15 * 60 + 30,
    });
    expect(result.current.durationMin).toBe(90);
  });

  it('setPickDate jumps weekStart to that week', () => {
    const { result } = renderHook(
      () =>
        useScheduleVisit({
          entry: mkEntry(),
          customerId: 'cust-1',
          customerName: 'Viktor Petrov',
          jobSummary: '',
          currentEvent: null,
          now: NOW,
        }),
      { wrapper: makeWrapper() },
    );
    act(() => {
      result.current.setPickDate('2026-06-15');
    });
    // Mon Jun 15 2026 is itself a Monday → weekStart should be Jun 15.
    expect(result.current.weekStart.getFullYear()).toBe(2026);
    expect(result.current.weekStart.getMonth()).toBe(5);
    expect(result.current.weekStart.getDate()).toBe(15);
  });

  it('setPickStart re-derives end from current duration', () => {
    const { result } = renderHook(
      () =>
        useScheduleVisit({
          entry: mkEntry(),
          customerId: 'cust-1',
          customerName: 'Viktor Petrov',
          jobSummary: '',
          currentEvent: null,
          now: NOW,
        }),
      { wrapper: makeWrapper() },
    );
    act(() => {
      result.current.setPickFromCalendarClick('2026-05-06', 14 * 60);
    });
    act(() => {
      result.current.setPickStart(15 * 60);
    });
    expect(result.current.pick).toEqual({
      date: '2026-05-06',
      start: 15 * 60,
      end: 15 * 60 + 60,
    });
  });

  it('conflict detection — same-date overlap surfaces in conflicts', async () => {
    // Override the mock to return one event in the visible week.
    const ev = mkEvent({
      id: 'conflict-evt',
      scheduled_date: '2026-05-06',
      start_time: '14:00:00',
      end_time: '15:00:00',
    });
    const usp = await import('./useSalesPipeline');
    vi.spyOn(usp, 'useSalesCalendarEvents').mockReturnValue({
      data: [ev],
      isLoading: false,
    } as ReturnType<typeof usp.useSalesCalendarEvents>);

    const { result } = renderHook(
      () =>
        useScheduleVisit({
          entry: mkEntry(),
          customerId: 'cust-1',
          customerName: 'Viktor Petrov',
          jobSummary: '',
          currentEvent: null,
          now: NOW,
        }),
      { wrapper: makeWrapper() },
    );
    act(() => {
      result.current.setPickFromCalendarClick('2026-05-06', 14 * 60 + 30);
    });
    await waitFor(() => {
      expect(result.current.hasConflict).toBe(true);
    });
  });

  it('submit() calls create.mutateAsync when no currentEvent', async () => {
    mockCreate.mockResolvedValueOnce({});
    const { result } = renderHook(
      () =>
        useScheduleVisit({
          entry: mkEntry(),
          customerId: 'cust-1',
          customerName: 'Viktor Petrov',
          jobSummary: '',
          currentEvent: null,
          now: NOW,
        }),
      { wrapper: makeWrapper() },
    );
    act(() => {
      result.current.setPickFromCalendarClick('2026-05-06', 14 * 60);
    });
    await act(async () => {
      const r = await result.current.submit();
      expect(r.ok).toBe(true);
    });
    expect(mockCreate).toHaveBeenCalledTimes(1);
    expect(mockUpdate).not.toHaveBeenCalled();
  });

  it('submit() calls update.mutateAsync on reschedule', async () => {
    mockUpdate.mockResolvedValueOnce({});
    const event = mkEvent();
    const { result } = renderHook(
      () =>
        useScheduleVisit({
          entry: mkEntry({ status: 'estimate_scheduled' }),
          customerId: 'cust-1',
          customerName: 'Viktor Petrov',
          jobSummary: '',
          currentEvent: event,
          now: NOW,
        }),
      { wrapper: makeWrapper() },
    );
    await act(async () => {
      const r = await result.current.submit();
      expect(r.ok).toBe(true);
    });
    expect(mockUpdate).toHaveBeenCalledTimes(1);
    expect(mockCreate).not.toHaveBeenCalled();
  });
});
