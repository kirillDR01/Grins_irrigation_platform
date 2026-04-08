/**
 * CampaignReview — Step 3 of the campaign wizard.
 *
 * Shows per-source breakdown, consent filter summary, time-zone warning,
 * estimated completion time, send now / schedule options, and typed
 * confirmation friction for large audiences.
 *
 * Validates: Requirements 15.11, 15.12, 33, 36
 */

import { useState, useMemo } from 'react';
import { AlertTriangle, Clock, Send, CalendarIcon, Shield } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Separator } from '@/components/ui/separator';
import type { AudiencePreview } from '../types/campaign';
import { countSegments } from '../utils/segmentCounter';

// --- Constants ---

const SENDS_PER_HOUR = 140;
/** CT time window: 8 AM – 9 PM (13 hours) */
const WINDOW_HOURS = 13;
const LARGE_AUDIENCE_THRESHOLD = 50;

// --- Props ---

export interface CampaignReviewProps {
  /** Audience preview data from the preview endpoint */
  preview: AudiencePreview | null;
  /** Message body (for segment count) */
  messageBody: string;
  /** Callback when user confirms send-now */
  onSendNow: () => void;
  /** Callback when user confirms schedule */
  onSchedule: (scheduledAt: string) => void;
  /** Whether the send/schedule mutation is pending */
  isSending?: boolean;
}

/** Estimate completion time in human-readable format */
function formatEstimate(totalRecipients: number): string {
  if (totalRecipients <= 0) return '0 minutes';
  const hours = totalRecipients / SENDS_PER_HOUR;
  if (hours < 1) {
    const mins = Math.ceil(hours * 60);
    return `~${mins} minute${mins !== 1 ? 's' : ''}`;
  }
  // Account for time-window gaps (13h window per day)
  const days = Math.floor(hours / WINDOW_HOURS);
  const remainingHours = hours - days * WINDOW_HOURS;
  if (days > 0) {
    const rh = Math.ceil(remainingHours * 10) / 10;
    return `~${days} day${days !== 1 ? 's' : ''} ${rh > 0 ? `+ ${rh}h` : ''}`;
  }
  const rh = Math.ceil(hours * 10) / 10;
  return `~${rh} hour${rh !== 1 ? 's' : ''}`;
}

export function CampaignReview({
  preview,
  messageBody,
  onSendNow,
  onSchedule,
  isSending = false,
}: CampaignReviewProps) {
  const [mode, setMode] = useState<'now' | 'schedule'>('now');
  const [scheduledDate, setScheduledDate] = useState('');
  const [scheduledTime, setScheduledTime] = useState('09:00');
  const [typedConfirmation, setTypedConfirmation] = useState('');

  const total = preview?.total ?? 0;
  const customersCount = preview?.customers_count ?? 0;
  const leadsCount = preview?.leads_count ?? 0;
  const adHocCount = preview?.ad_hoc_count ?? 0;
  const rawTotal = customersCount + leadsCount + adHocCount;
  const blocked = rawTotal - total;

  // Segment info
  const { segments } = useMemo(() => countSegments(messageBody), [messageBody]);

  // Determine if large audience (typed confirmation required)
  const isLargeAudience = total >= LARGE_AUDIENCE_THRESHOLD;
  const expectedConfirmation = `SEND ${total}`;
  const confirmationValid = !isLargeAudience || typedConfirmation === expectedConfirmation;

  // Estimated completion time
  const estimatedTime = formatEstimate(total);

  // Handle confirm
  const handleConfirm = () => {
    if (!confirmationValid) return;
    if (mode === 'schedule' && scheduledDate) {
      const isoDate = `${scheduledDate}T${scheduledTime}:00`;
      onSchedule(isoDate);
    } else {
      onSendNow();
    }
  };

  return (
    <div data-testid="campaign-review" className="space-y-5">
      {/* Per-source breakdown */}
      <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 space-y-3">
        <h4 className="text-sm font-semibold text-slate-700">Recipient Breakdown</h4>
        <div className="grid grid-cols-3 gap-3 text-center">
          <div>
            <p className="text-2xl font-bold text-teal-700" data-testid="customers-count">
              {customersCount}
            </p>
            <p className="text-xs text-slate-500">Customers</p>
          </div>
          <div>
            <p className="text-2xl font-bold text-blue-700" data-testid="leads-count">
              {leadsCount}
            </p>
            <p className="text-xs text-slate-500">Leads</p>
          </div>
          <div>
            <p className="text-2xl font-bold text-purple-700" data-testid="adhoc-count">
              {adHocCount}
            </p>
            <p className="text-xs text-slate-500">Ad-hoc</p>
          </div>
        </div>

        <Separator />

        {/* Consent filter breakdown */}
        <div className="flex items-center justify-between text-sm" data-testid="consent-breakdown">
          <span className="text-slate-600">
            {rawTotal} total → <span className="font-semibold text-teal-700">{total} will send</span>
            {blocked > 0 && (
              <span className="text-red-600"> ({blocked} blocked by consent)</span>
            )}
          </span>
        </div>
      </div>

      {/* Time-zone warning (H1) */}
      {total > 0 && (
        <Alert data-testid="timezone-warning">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription className="text-sm">
            All recipients will be texted during the <strong>8 AM – 9 PM Central Time</strong> window.
            Recipients with non-Central area codes may receive messages outside their local time window.
            Per-recipient timezone enforcement is not yet supported.
          </AlertDescription>
        </Alert>
      )}

      {/* Estimated completion time */}
      <div className="flex items-center gap-3 rounded-lg border border-slate-200 p-3" data-testid="time-estimate">
        <Clock className="h-5 w-5 text-slate-400 shrink-0" />
        <div className="text-sm">
          <p className="text-slate-700">
            Estimated completion: <span className="font-semibold">{estimatedTime}</span>
          </p>
          <p className="text-xs text-slate-500">
            Sending at ~{SENDS_PER_HOUR}/hour within the 8 AM – 9 PM CT window
            {segments > 1 && (
              <span className="text-amber-600">
                {' '}· {segments} segments per message (cost ×{segments})
              </span>
            )}
          </p>
        </div>
      </div>

      {/* Send mode selection */}
      <div className="space-y-3">
        <Label className="text-sm font-semibold text-slate-700">When to send</Label>
        <div className="flex gap-3">
          <Button
            type="button"
            variant={mode === 'now' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setMode('now')}
            data-testid="send-now-btn"
            className="gap-2"
          >
            <Send className="h-4 w-4" />
            Send now
          </Button>
          <Button
            type="button"
            variant={mode === 'schedule' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setMode('schedule')}
            data-testid="schedule-btn"
            className="gap-2"
          >
            <CalendarIcon className="h-4 w-4" />
            Schedule
          </Button>
        </div>

        {mode === 'schedule' && (
          <div className="flex gap-3 items-end" data-testid="schedule-inputs">
            <div className="space-y-1">
              <Label className="text-xs text-slate-500">Date</Label>
              <Input
                type="date"
                value={scheduledDate}
                onChange={(e) => setScheduledDate(e.target.value)}
                min={new Date().toISOString().split('T')[0]}
                data-testid="schedule-date"
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs text-slate-500">Time (CT)</Label>
              <Input
                type="time"
                value={scheduledTime}
                onChange={(e) => setScheduledTime(e.target.value)}
                data-testid="schedule-time"
              />
            </div>
            <p className="text-xs text-slate-400 pb-2">Central Time</p>
          </div>
        )}

        {mode === 'schedule' && scheduledDate && (
          <p className="text-xs text-slate-500" data-testid="schedule-note">
            Scheduled for {scheduledDate} at {scheduledTime} CT. You can still cancel before it starts.
          </p>
        )}
      </div>

      <Separator />

      {/* Confirmation friction */}
      {isLargeAudience ? (
        <div className="space-y-3" data-testid="typed-confirmation">
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 space-y-3">
            <div className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-red-600" />
              <p className="text-sm font-semibold text-red-800">
                Large audience confirmation required
              </p>
            </div>
            <p className="text-sm text-red-700">
              You are about to send SMS to <strong>{total} people</strong>. This cannot be undone.
              Type <strong className="font-mono">{expectedConfirmation}</strong> below to confirm.
            </p>
            <Input
              value={typedConfirmation}
              onChange={(e) => setTypedConfirmation(e.target.value)}
              placeholder={expectedConfirmation}
              data-testid="confirmation-input"
              className="font-mono"
            />
          </div>
        </div>
      ) : (
        total > 0 && (
          <p className="text-sm text-slate-600" data-testid="simple-confirmation">
            Ready to send to <strong>{total}</strong> recipient{total !== 1 ? 's' : ''}.
          </p>
        )
      )}

      {/* Final confirm button */}
      <Button
        type="button"
        variant="destructive"
        className="w-full"
        disabled={
          total === 0 ||
          !confirmationValid ||
          isSending ||
          (mode === 'schedule' && !scheduledDate)
        }
        onClick={handleConfirm}
        data-testid="confirm-send-btn"
      >
        {isSending
          ? 'Sending...'
          : mode === 'schedule'
            ? `Schedule for ${scheduledDate || '...'}`
            : `Send to ${total} recipient${total !== 1 ? 's' : ''}`}
      </Button>
    </div>
  );
}
