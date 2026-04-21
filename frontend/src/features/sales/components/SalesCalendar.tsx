/**
 * Sales Calendar — Req 15.1, 15.2, 15.3
 * Dedicated estimate scheduling calendar, independent from main schedule.
 */

import { useState, useMemo, useCallback } from 'react';
import FullCalendar from '@fullcalendar/react';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import type { DateClickArg } from '@fullcalendar/interaction';
import type { DatesSetArg, EventInput, EventClickArg } from '@fullcalendar/core';
import { format, startOfMonth, endOfMonth, addMonths } from 'date-fns';
import { toast } from 'sonner';
import { CalendarDays, Plus, Trash2, X, ExternalLink } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { LoadingSpinner } from '@/shared/components/LoadingSpinner';
import { CustomerContextBlock } from '@/shared/components/CustomerContextBlock';
import { InternalNotesCard } from '@/shared/components/InternalNotesCard';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useUpdateCustomer } from '@/features/customers/hooks';
import { invalidateAfterCustomerInternalNotesSave } from '@/shared/utils/invalidationHelpers';
import { customerApi } from '@/features/customers/api/customerApi';
import { Link } from 'react-router-dom';
import {
  useSalesCalendarEvents,
  useCreateCalendarEvent,
  useUpdateCalendarEvent,
  useDeleteCalendarEvent,
  useSalesPipeline,
} from '../hooks/useSalesPipeline';
import type { SalesCalendarEvent } from '../types/pipeline';
import '@/features/schedule/components/CalendarView.css';

interface EventFormState {
  mode: 'create' | 'edit';
  eventId?: string;
  salesEntryId: string;
  customerId: string;
  title: string;
  scheduledDate: string;
  startTime: string;
  endTime: string;
  notes: string;
}

export function SalesCalendar() {
  const [dateRange, setDateRange] = useState(() => {
    const today = new Date();
    return {
      start: format(startOfMonth(today), 'yyyy-MM-dd'),
      end: format(endOfMonth(addMonths(today, 1)), 'yyyy-MM-dd'),
    };
  });

  const [formState, setFormState] = useState<EventFormState | null>(null);

  const { data: events, isLoading } = useSalesCalendarEvents({
    start_date: dateRange.start,
    end_date: dateRange.end,
  });

  // Fetch pipeline entries for the sales_entry_id dropdown
  const { data: pipelineData } = useSalesPipeline({ limit: 200 });

  const createEvent = useCreateCalendarEvent();
  const updateEvent = useUpdateCalendarEvent();
  const deleteEvent = useDeleteCalendarEvent();
  const updateCustomerMutation = useUpdateCustomer();
  const queryClient = useQueryClient();

  const calendarEvents: EventInput[] = useMemo(() => {
    if (!events) return [];
    return events.map((e) => {
      const start = e.start_time
        ? `${e.scheduled_date}T${e.start_time}`
        : e.scheduled_date;
      const end = e.end_time
        ? `${e.scheduled_date}T${e.end_time}`
        : undefined;
      return {
        id: e.id,
        title: e.title,
        start,
        end,
        backgroundColor: '#dbeafe',
        borderColor: '#3b82f6',
        textColor: '#1e40af',
        extendedProps: { event: e },
      };
    });
  }, [events]);

  const handleDatesSet = useCallback((arg: DatesSetArg) => {
    setDateRange({
      start: format(arg.start, 'yyyy-MM-dd'),
      end: format(arg.end, 'yyyy-MM-dd'),
    });
  }, []);

  const handleDateClick = useCallback(
    (arg: DateClickArg) => {
      setFormState({
        mode: 'create',
        salesEntryId: '',
        customerId: '',
        title: '',
        scheduledDate: arg.dateStr.slice(0, 10),
        startTime: '09:00',
        endTime: '10:00',
        notes: '',
      });
    },
    [],
  );

  const handleEventClick = useCallback((arg: EventClickArg) => {
    const e = arg.event.extendedProps.event as SalesCalendarEvent;
    setFormState({
      mode: 'edit',
      eventId: e.id,
      salesEntryId: e.sales_entry_id,
      customerId: e.customer_id,
      title: e.title,
      scheduledDate: e.scheduled_date,
      startTime: e.start_time ?? '',
      endTime: e.end_time ?? '',
      notes: e.notes ?? '',
    });
  }, []);

  const handleSave = useCallback(async () => {
    if (!formState) return;
    if (!formState.title.trim() || !formState.salesEntryId) {
      toast.error('Title and Sales Entry are required');
      return;
    }
    try {
      if (formState.mode === 'create') {
        await createEvent.mutateAsync({
          sales_entry_id: formState.salesEntryId,
          customer_id: formState.customerId,
          title: formState.title,
          scheduled_date: formState.scheduledDate,
          start_time: formState.startTime || null,
          end_time: formState.endTime || null,
          notes: formState.notes || null,
        });
        toast.success('Estimate appointment created');
      } else if (formState.eventId) {
        await updateEvent.mutateAsync({
          eventId: formState.eventId,
          body: {
            title: formState.title,
            scheduled_date: formState.scheduledDate,
            start_time: formState.startTime || null,
            end_time: formState.endTime || null,
            notes: formState.notes || null,
          },
        });
        toast.success('Estimate appointment updated');
      }
      setFormState(null);
    } catch {
      toast.error('Failed to save appointment');
    }
  }, [formState, createEvent, updateEvent]);

  const handleDelete = useCallback(async () => {
    if (!formState?.eventId) return;
    try {
      await deleteEvent.mutateAsync(formState.eventId);
      toast.success('Appointment deleted');
      setFormState(null);
    } catch {
      toast.error('Failed to delete appointment');
    }
  }, [formState, deleteEvent]);

  // When a sales entry is selected, auto-fill customer_id
  const handleEntryChange = useCallback(
    (entryId: string) => {
      const entry = pipelineData?.items.find((e) => e.id === entryId);
      setFormState((prev) =>
        prev
          ? {
              ...prev,
              salesEntryId: entryId,
              customerId: entry?.customer_id ?? '',
              title: prev.title || (entry?.customer_name ? `Estimate - ${entry.customer_name}` : ''),
            }
          : null,
      );
    },
    [pipelineData],
  );

  // Fetch customer data for context block when editing
  const { data: contextCustomer } = useQuery({
    queryKey: ['customers', 'detail', formState?.customerId],
    queryFn: () => customerApi.get(formState!.customerId),
    enabled: !!formState?.customerId,
  });

  // Internal notes save handler — PATCHes the customer
  const handleSaveEstimateNotes = useCallback(
    async (next: string | null) => {
      if (!formState?.customerId) return;
      await updateCustomerMutation.mutateAsync({
        id: formState.customerId,
        data: { internal_notes: next },
      });
      invalidateAfterCustomerInternalNotesSave(queryClient, formState.customerId);
    },
    [formState, updateCustomerMutation, queryClient],
  );

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64" data-testid="loading-spinner">
        <LoadingSpinner />
      </div>
    );
  }

  return (
    <div data-testid="sales-calendar" className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-slate-600">
          <CalendarDays className="h-5 w-5" />
          <span className="text-sm font-medium">Estimate Appointments</span>
        </div>
        <Button
          size="sm"
          onClick={() =>
            setFormState({
              mode: 'create',
              salesEntryId: '',
              customerId: '',
              title: '',
              scheduledDate: format(new Date(), 'yyyy-MM-dd'),
              startTime: '09:00',
              endTime: '10:00',
              notes: '',
            })
          }
          data-testid="add-calendar-event-btn"
        >
          <Plus className="h-4 w-4 mr-1" />
          New Appointment
        </Button>
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-4">
        <FullCalendar
          plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin]}
          initialView="dayGridMonth"
          headerToolbar={{
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek',
          }}
          events={calendarEvents}
          datesSet={handleDatesSet}
          dateClick={handleDateClick}
          eventClick={handleEventClick}
          height="auto"
          editable={false}
          selectable
        />
      </div>

      {/* Event form modal */}
      {formState && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div
            className="bg-white rounded-xl shadow-xl w-full max-w-md p-6 space-y-4"
            data-testid="calendar-event-form"
          >
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-slate-800">
                {formState.mode === 'create'
                  ? 'New Estimate Appointment'
                  : 'Edit Appointment'}
              </h3>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setFormState(null)}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>

            <div className="space-y-3">
              {/* Customer Context Block — Req 10A */}
              {contextCustomer && (
                <CustomerContextBlock
                  data={{
                    customer_name: [contextCustomer.first_name, contextCustomer.last_name].filter(Boolean).join(' '),
                    customer_phone: contextCustomer.phone,
                    primary_address: contextCustomer.properties?.find((p: { is_primary?: boolean }) => p.is_primary)?.address,
                    primary_city: contextCustomer.properties?.find((p: { is_primary?: boolean }) => p.is_primary)?.city,
                    primary_state: contextCustomer.properties?.find((p: { is_primary?: boolean }) => p.is_primary)?.state,
                    primary_zip: contextCustomer.properties?.find((p: { is_primary?: boolean }) => p.is_primary)?.zip_code,
                    is_priority: contextCustomer.is_priority,
                    is_red_flag: contextCustomer.is_red_flag,
                    is_slow_payer: contextCustomer.is_slow_payer,
                    dogs_on_property: contextCustomer.properties?.find((p: { is_primary?: boolean }) => p.is_primary)?.dogs_on_property,
                    gate_code: contextCustomer.properties?.find((p: { is_primary?: boolean }) => p.is_primary)?.gate_code,
                    access_instructions: contextCustomer.properties?.find((p: { is_primary?: boolean }) => p.is_primary)?.access_instructions,
                    last_contacted_at: contextCustomer.last_contacted_at,
                  }}
                />
              )}

              {/* Source record link — Req 10B */}
              {formState.salesEntryId && (
                <Link
                  to={`/sales?entry=${formState.salesEntryId}`}
                  className="text-sm text-purple-600 hover:text-purple-700 flex items-center gap-1"
                  data-testid="view-sales-entry-link"
                >
                  View sales entry <ExternalLink className="h-3 w-3" />
                </Link>
              )}

              <div>
                <Label htmlFor="sales-entry">Sales Entry</Label>
                <select
                  id="sales-entry"
                  className="w-full mt-1 rounded-md border border-slate-200 px-3 py-2 text-sm"
                  value={formState.salesEntryId}
                  onChange={(e) => handleEntryChange(e.target.value)}
                  disabled={formState.mode === 'edit'}
                >
                  <option value="">Select a sales entry...</option>
                  {pipelineData?.items
                    .filter(
                      (e) =>
                        e.status !== 'closed_won' && e.status !== 'closed_lost',
                    )
                    .map((e) => (
                      <option key={e.id} value={e.id}>
                        {e.customer_name ?? 'Unknown'} — {e.job_type ?? 'N/A'}
                      </option>
                    ))}
                </select>
              </div>

              <div>
                <Label htmlFor="event-title">Title</Label>
                <Input
                  id="event-title"
                  value={formState.title}
                  onChange={(e) =>
                    setFormState((prev) =>
                      prev ? { ...prev, title: e.target.value } : null,
                    )
                  }
                  placeholder="Estimate appointment title"
                />
              </div>

              <div>
                <Label htmlFor="event-date">Date</Label>
                <Input
                  id="event-date"
                  type="date"
                  value={formState.scheduledDate}
                  onChange={(e) =>
                    setFormState((prev) =>
                      prev ? { ...prev, scheduledDate: e.target.value } : null,
                    )
                  }
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label htmlFor="event-start">Start Time</Label>
                  <Input
                    id="event-start"
                    type="time"
                    value={formState.startTime}
                    onChange={(e) =>
                      setFormState((prev) =>
                        prev ? { ...prev, startTime: e.target.value } : null,
                      )
                    }
                  />
                </div>
                <div>
                  <Label htmlFor="event-end">End Time</Label>
                  <Input
                    id="event-end"
                    type="time"
                    value={formState.endTime}
                    onChange={(e) =>
                      setFormState((prev) =>
                        prev ? { ...prev, endTime: e.target.value } : null,
                      )
                    }
                  />
                </div>
              </div>

              <div>
                <Label htmlFor="event-notes">Notes</Label>
                <Textarea
                  id="event-notes"
                  value={formState.notes}
                  onChange={(e) =>
                    setFormState((prev) =>
                      prev ? { ...prev, notes: e.target.value } : null,
                    )
                  }
                  placeholder="Optional notes..."
                  rows={2}
                />
              </div>

              {/* Internal Notes Card — customer's internal_notes */}
              {formState.customerId ? (
                <InternalNotesCard
                  value={contextCustomer?.internal_notes ?? null}
                  onSave={handleSaveEstimateNotes}
                  isSaving={updateCustomerMutation.isPending}
                  data-testid-prefix="sales-calendar-"
                />
              ) : (
                <p className="text-sm text-slate-400 italic">
                  Notes will appear here once the customer is created
                </p>
              )}
            </div>

            <div className="flex items-center justify-between pt-2">
              {formState.mode === 'edit' ? (
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={handleDelete}
                  disabled={deleteEvent.isPending}
                  data-testid="delete-calendar-event-btn"
                >
                  <Trash2 className="h-4 w-4 mr-1" />
                  Delete
                </Button>
              ) : (
                <div />
              )}
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setFormState(null)}
                >
                  Cancel
                </Button>
                <Button
                  size="sm"
                  onClick={handleSave}
                  disabled={createEvent.isPending || updateEvent.isPending}
                  data-testid="save-calendar-event-btn"
                >
                  {formState.mode === 'create' ? 'Create' : 'Save'}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
