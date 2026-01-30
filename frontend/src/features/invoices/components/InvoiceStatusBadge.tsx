import { memo } from 'react';
import { cn } from '@/lib/utils';
import type { InvoiceStatus } from '../types';
import { getInvoiceStatusConfig } from '../types';

interface InvoiceStatusBadgeProps {
  status: InvoiceStatus;
  className?: string;
}

export const InvoiceStatusBadge = memo(function InvoiceStatusBadge({
  status,
  className,
}: InvoiceStatusBadgeProps) {
  const config = getInvoiceStatusConfig(status);

  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-3 py-1 text-xs font-medium',
        config.bgColor,
        config.color,
        className
      )}
      data-testid={`invoice-status-${status}`}
    >
      {config.label}
    </span>
  );
});
