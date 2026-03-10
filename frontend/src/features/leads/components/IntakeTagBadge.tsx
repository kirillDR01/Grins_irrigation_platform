import { memo } from 'react';
import { cn } from '@/shared/utils/cn';
import type { IntakeTag } from '../types';
import { INTAKE_TAG_LABELS } from '../types';

interface IntakeTagBadgeProps {
  tag: IntakeTag | null;
  className?: string;
}

const tagColors: Record<string, string> = {
  schedule: 'bg-green-100 text-green-800',
  follow_up: 'bg-orange-100 text-orange-800',
};

export const IntakeTagBadge = memo(function IntakeTagBadge({
  tag,
  className,
}: IntakeTagBadgeProps) {
  const label = tag ? (INTAKE_TAG_LABELS[tag] ?? tag) : 'Untagged';
  const color = tag ? (tagColors[tag] ?? 'bg-gray-100 text-gray-600') : 'bg-gray-100 text-gray-500';

  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-3 py-1 text-xs font-medium',
        color,
        className
      )}
      data-testid={`intake-tag-${tag ?? 'none'}`}
    >
      {label}
    </span>
  );
});
