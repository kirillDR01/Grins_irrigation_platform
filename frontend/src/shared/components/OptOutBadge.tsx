/**
 * Shared SMS opt-out badge (Gap 06).
 *
 * Renders a short, color-coded pill beside a customer name when:
 *  - Red fill: the customer has opted out via explicit STOP (`text_stop`).
 *  - Amber fill: the admin confirmed an informal opt-out
 *    (`admin_confirmed_informal`).
 *  - Amber outline: an unacknowledged `INFORMAL_OPT_OUT` alert is
 *    pending review, but no consent record has been written yet.
 *
 * Renders nothing when the customer is fully opted in. Tooltip uses the
 * native `title=` attribute (no Radix Tooltip is installed in this repo).
 */
import { memo } from 'react';

import { Badge } from '@/components/ui/badge';
import { useCustomerConsentStatus } from '@/features/customers/hooks/useConsentStatus';
import { cn } from '@/shared/utils/cn';

export interface OptOutBadgeProps {
  customerId: string | null | undefined;
  compact?: boolean;
  className?: string;
}

function methodLabel(method: string | null): string {
  switch (method) {
    case 'text_stop':
      return 'STOP keyword';
    case 'admin_confirmed_informal':
      return 'admin confirmation';
    default:
      return method ?? 'unknown';
  }
}

function formatTimestamp(ts: string | null): string {
  if (!ts) return 'unknown date';
  const d = new Date(ts);
  return d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
}

export const OptOutBadge = memo(function OptOutBadge({
  customerId,
  compact = false,
  className,
}: OptOutBadgeProps) {
  const { data, isLoading } = useCustomerConsentStatus(customerId);

  if (isLoading || !data) return null;
  if (!data.is_opted_out && !data.pending_informal_opt_out_alert_id) return null;

  const sizeClasses = compact
    ? 'px-1.5 py-0 text-[10px] leading-4 h-4'
    : 'px-2 py-0.5 text-xs';

  // Variant ordering: hard stop > admin confirmed > pending.
  let variantClasses = 'bg-red-100 text-red-700 hover:bg-red-100 border border-red-200';
  let label = 'Opted out';
  let tooltip = `Customer opted out via ${methodLabel(data.opt_out_method)} on ${formatTimestamp(data.opt_out_timestamp)}.`;

  if (data.is_opted_out && data.opt_out_method === 'admin_confirmed_informal') {
    variantClasses = 'bg-amber-100 text-amber-800 hover:bg-amber-100 border border-amber-200';
    label = 'Opted out';
    tooltip = `Admin-confirmed informal opt-out on ${formatTimestamp(data.opt_out_timestamp)}.`;
  } else if (!data.is_opted_out && data.pending_informal_opt_out_alert_id) {
    variantClasses = 'bg-white text-amber-800 hover:bg-amber-50 border border-amber-400';
    label = 'Opt-out pending';
    tooltip = 'Informal opt-out signal detected. Awaiting admin review.';
  }

  return (
    <Badge
      variant="secondary"
      title={tooltip}
      data-testid="opt-out-badge"
      data-variant={
        data.is_opted_out && data.opt_out_method === 'text_stop'
          ? 'hard-stop'
          : data.is_opted_out
            ? 'admin-confirmed'
            : 'pending'
      }
      className={cn('rounded-full font-medium capitalize', sizeClasses, variantClasses, className)}
    >
      {label}
    </Badge>
  );
});
