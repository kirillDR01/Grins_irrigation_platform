/**
 * AlertCard component for dashboard alerts.
 * Clickable card that navigates to a target page with query params for filtering and highlighting.
 */

import { useNavigate } from 'react-router-dom';
import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import type { ComponentType } from 'react';
import type { LucideProps } from 'lucide-react';

export interface AlertCardProps {
  /** Title text displayed on the card */
  title: string;
  /** Description text below the title */
  description: string;
  /** Numeric count to display */
  count: number;
  /** Icon component to render */
  icon: ComponentType<LucideProps>;
  /** Navigation path (e.g., '/jobs') */
  targetPath: string;
  /** Query params to append (e.g., { status: 'requested', highlight: 'job-123' }) */
  queryParams?: Record<string, string>;
  /** Visual variant for color theming */
  variant?: 'amber' | 'red' | 'blue' | 'teal' | 'emerald';
  /** data-testid for E2E testing */
  testId?: string;
}

const variantStyles: Record<
  NonNullable<AlertCardProps['variant']>,
  { border: string; bg: string; iconBg: string; iconText: string; countText: string }
> = {
  amber: {
    border: 'border-amber-200',
    bg: 'hover:bg-amber-50/50',
    iconBg: 'bg-amber-100',
    iconText: 'text-amber-600',
    countText: 'text-amber-700',
  },
  red: {
    border: 'border-red-200',
    bg: 'hover:bg-red-50/50',
    iconBg: 'bg-red-100',
    iconText: 'text-red-600',
    countText: 'text-red-700',
  },
  blue: {
    border: 'border-blue-200',
    bg: 'hover:bg-blue-50/50',
    iconBg: 'bg-blue-100',
    iconText: 'text-blue-600',
    countText: 'text-blue-700',
  },
  teal: {
    border: 'border-teal-200',
    bg: 'hover:bg-teal-50/50',
    iconBg: 'bg-teal-100',
    iconText: 'text-teal-600',
    countText: 'text-teal-700',
  },
  emerald: {
    border: 'border-emerald-200',
    bg: 'hover:bg-emerald-50/50',
    iconBg: 'bg-emerald-100',
    iconText: 'text-emerald-600',
    countText: 'text-emerald-700',
  },
};

export function AlertCard({
  title,
  description,
  count,
  icon: Icon,
  targetPath,
  queryParams = {},
  variant = 'amber',
  testId,
}: AlertCardProps) {
  const navigate = useNavigate();
  const styles = variantStyles[variant];

  const handleClick = () => {
    const params = new URLSearchParams(queryParams);
    const search = params.toString();
    navigate(search ? `${targetPath}?${search}` : targetPath);
  };

  return (
    <Card
      data-testid={testId ?? 'alert-card'}
      className={cn(
        'cursor-pointer transition-all hover:shadow-md border-l-4',
        styles.border,
        styles.bg,
      )}
      onClick={handleClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          handleClick();
        }
      }}
    >
      <CardContent className="p-4">
        <div className="flex items-center gap-3">
          <div className={cn('p-2 rounded-full', styles.iconBg)}>
            <Icon className={cn('h-4 w-4', styles.iconText)} />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-slate-800 truncate">{title}</p>
            <p className="text-xs text-slate-500 mt-0.5 truncate">{description}</p>
          </div>
          <span className={cn('text-2xl font-bold', styles.countText)} data-testid="alert-card-count">
            {count}
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
