import { useState } from 'react';
import { toast } from 'sonner';
import axios from 'axios';
import { format } from 'date-fns';
import { useQueryClient } from '@tanstack/react-query';
import { X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  useAdvanceSalesEntry,
  useMarkSalesLost,
  useCreateCalendarEvent,
  pipelineKeys,
} from '../hooks/useSalesPipeline';
import {
  SALES_STATUS_CONFIG,
  TERMINAL_STATUSES,
  type SalesEntry,
} from '../types/pipeline';
import { CreateJobModal } from '@/features/jobs/components/CreateJobModal';

interface StatusActionButtonProps {
  entry: SalesEntry;
}

export function StatusActionButton({ entry }: StatusActionButtonProps) {
  const queryClient = useQueryClient();
  const advance = useAdvanceSalesEntry();
  const markLost = useMarkSalesLost();
  const createCalendarEvent = useCreateCalendarEvent();
  const [showLostConfirm, setShowLostConfirm] = useState(false);
  const [showCalendarForm, setShowCalendarForm] = useState(false);
  const [createJobOpen, setCreateJobOpen] = useState(false);
  const [calendarForm, setCalendarForm] = useState({
    title: '',
    scheduledDate: '',
    startTime: '09:00',
    endTime: '10:00',
    notes: '',
  });

  const config = SALES_STATUS_CONFIG[entry.status];
  const isTerminal = TERMINAL_STATUSES.includes(entry.status);
  const isSendContract = entry.status === 'send_contract';

  const isScheduleEstimate = entry.status === 'schedule_estimate';

  if (isTerminal) return null;

  const openCalendarForm = () => {
    const customerName = entry.customer_name ?? 'Customer';
    setCalendarForm({
      title: `Estimate - ${customerName}`,
      scheduledDate: format(new Date(), 'yyyy-MM-dd'),
      startTime: '09:00',
      endTime: '10:00',
      notes: entry.property_address ? `Property: ${entry.property_address}` : '',
    });
    setShowCalendarForm(true);
  };

  const handleSaveCalendarEvent = async () => {
    if (!calendarForm.title.trim()) {
      toast.error('Title is required');
      return;
    }
    try {
      // Inline schedule form: book the slot WITHOUT auto-sending the
      // Y/R/C SMS — the modal-based ScheduleVisitModal owns the
      // book+send combined flow. This call site is the legacy fallback
      // and intentionally leaves confirmation dispatch to staff.
      await createCalendarEvent.mutateAsync({
        body: {
          sales_entry_id: entry.id,
          customer_id: entry.customer_id,
          title: calendarForm.title,
          scheduled_date: calendarForm.scheduledDate,
          start_time: calendarForm.startTime || null,
          end_time: calendarForm.endTime || null,
          notes: calendarForm.notes || null,
        },
      });
      queryClient.invalidateQueries({ queryKey: pipelineKeys.lists() });
      toast.success('Estimate appointment scheduled');
      setShowCalendarForm(false);
    } catch {
      toast.error('Failed to create estimate appointment');
    }
  };

  const handleAdvance = (e: React.MouseEvent) => {
    e.stopPropagation();
    // For schedule_estimate, open calendar form instead of advancing directly
    if (isScheduleEstimate) {
      openCalendarForm();
      return;
    }
    if (isSendContract) {
      // Cluster C: SignWell-gated convert removed. The "Convert to Job"
      // button now opens CreateJobModal which owns the create + closed_won
      // two-call shape.
      setCreateJobOpen(true);
      return;
    }
    advance.mutate(entry.id, {
      onSuccess: () => {
        toast.success('Status advanced');
      },
      onError: (err) => {
        const msg = axios.isAxiosError(err)
          ? (err.response?.data?.detail ?? 'Failed to advance')
          : 'Failed to advance';
        if (
          typeof msg === 'string'
          && /upload an estimate|pending_approval/i.test(msg)
        ) {
          // Defensive: as of the Q-B gate-drop the API no longer returns
          // this 422 — advancing send_estimate → pending_approval is
          // gate-free. Kept in case server-side gates are reintroduced;
          // harmless dead branch otherwise.
          toast.error('Upload an estimate before advancing', {
            description:
              'This sales entry needs a signing document on file before it can move to pending approval.',
          });
        } else {
          toast.error('Error', { description: typeof msg === 'string' ? msg : 'Failed to advance' });
        }
      },
    });
  };

  const handleMarkLost = (e: React.MouseEvent) => {
    e.stopPropagation();
    setShowLostConfirm(true);
  };

  const confirmMarkLost = () => {
    markLost.mutate(
      { id: entry.id },
      {
        onSuccess: () => {
          toast.success('Marked as lost');
          setShowLostConfirm(false);
        },
        onError: () => {
          toast.error('Failed to mark as lost');
          setShowLostConfirm(false);
        },
      },
    );
  };

  return (
    <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
      {config.action && (
        <Button
          size="sm"
          variant="outline"
          onClick={handleAdvance}
          disabled={advance.isPending}
          data-testid={`advance-btn-${entry.id}`}
        >
          {advance.isPending ? 'Processing...' : config.action}
        </Button>
      )}
      <Button
        size="sm"
        variant="ghost"
        className="text-red-500 hover:text-red-700 hover:bg-red-50"
        onClick={handleMarkLost}
        disabled={markLost.isPending}
        data-testid={`mark-lost-btn-${entry.id}`}
      >
        Mark Lost
      </Button>

      {/* Mark lost confirmation */}
      <Dialog open={showLostConfirm} onOpenChange={setShowLostConfirm}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Mark as Lost?</DialogTitle>
            <DialogDescription>
              This will close the sales entry as lost. This action cannot be
              undone via the action button.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowLostConfirm(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={confirmMarkLost}
            >
              Mark Lost
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Schedule estimate calendar event form */}
      {showCalendarForm && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
          onClick={(e) => e.stopPropagation()}
        >
          <div
            className="bg-white rounded-xl shadow-xl w-full max-w-md p-6 space-y-4"
            data-testid="schedule-estimate-form"
          >
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-slate-800">
                Schedule Estimate Appointment
              </h3>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowCalendarForm(false)}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>

            {entry.customer_name && (
              <p className="text-sm text-slate-600">
                Customer: <span className="font-medium">{entry.customer_name}</span>
                {entry.property_address && (
                  <> — {entry.property_address}</>
                )}
              </p>
            )}

            <div className="space-y-3">
              <div>
                <Label htmlFor="estimate-title">Title</Label>
                <Input
                  id="estimate-title"
                  value={calendarForm.title}
                  onChange={(e) =>
                    setCalendarForm((prev) => ({ ...prev, title: e.target.value }))
                  }
                  placeholder="Estimate appointment title"
                />
              </div>

              <div>
                <Label htmlFor="estimate-date">Date</Label>
                <Input
                  id="estimate-date"
                  type="date"
                  value={calendarForm.scheduledDate}
                  onChange={(e) =>
                    setCalendarForm((prev) => ({ ...prev, scheduledDate: e.target.value }))
                  }
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label htmlFor="estimate-start">Start Time</Label>
                  <Input
                    id="estimate-start"
                    type="time"
                    value={calendarForm.startTime}
                    onChange={(e) =>
                      setCalendarForm((prev) => ({ ...prev, startTime: e.target.value }))
                    }
                  />
                </div>
                <div>
                  <Label htmlFor="estimate-end">End Time</Label>
                  <Input
                    id="estimate-end"
                    type="time"
                    value={calendarForm.endTime}
                    onChange={(e) =>
                      setCalendarForm((prev) => ({ ...prev, endTime: e.target.value }))
                    }
                  />
                </div>
              </div>

              <div>
                <Label htmlFor="estimate-notes">Notes</Label>
                <Textarea
                  id="estimate-notes"
                  value={calendarForm.notes}
                  onChange={(e) =>
                    setCalendarForm((prev) => ({ ...prev, notes: e.target.value }))
                  }
                  placeholder="Optional notes..."
                  rows={2}
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowCalendarForm(false)}
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={handleSaveCalendarEvent}
                disabled={createCalendarEvent.isPending}
                data-testid="save-estimate-event-btn"
              >
                {createCalendarEvent.isPending ? 'Scheduling...' : 'Schedule'}
              </Button>
            </div>
          </div>
        </div>
      )}

      <CreateJobModal
        open={createJobOpen}
        onOpenChange={setCreateJobOpen}
        salesEntry={entry}
      />
    </div>
  );
}
