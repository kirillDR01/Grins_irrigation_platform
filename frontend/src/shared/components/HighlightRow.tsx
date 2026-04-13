import { forwardRef, type HTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

export interface HighlightRowProps extends HTMLAttributes<HTMLTableRowElement> {
  /** Whether this row is currently highlighted */
  active: boolean;
}

/**
 * Table row wrapper that applies an amber/yellow pulse animation
 * fading over 3 seconds when `active` is true.
 *
 * Usage:
 * ```tsx
 * const { isHighlighted, highlightRef } = useHighlight();
 * <HighlightRow
 *   active={isHighlighted(row.id)}
 *   ref={isHighlighted(row.id) ? highlightRef : undefined}
 * >
 *   <td>...</td>
 * </HighlightRow>
 * ```
 */
export const HighlightRow = forwardRef<HTMLTableRowElement, HighlightRowProps>(
  ({ active, className, children, ...props }, ref) => (
    <tr
      ref={ref}
      className={cn(className, active && 'animate-highlight-pulse')}
      data-testid={active ? 'highlighted-row' : undefined}
      {...props}
    >
      {children}
    </tr>
  ),
);

HighlightRow.displayName = 'HighlightRow';
