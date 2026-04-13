import { memo } from 'react';
import { cn } from '@/shared/utils/cn';

export interface PropertyTagsProps {
  propertyType?: string | null;
  isHoa?: boolean;
  isSubscription?: boolean;
  className?: string;
}

const TAG_CONFIG = {
  residential: { label: 'Residential', className: 'bg-sky-50 text-sky-700 border-sky-100' },
  commercial: { label: 'Commercial', className: 'bg-purple-50 text-purple-700 border-purple-100' },
  hoa: { label: 'HOA', className: 'bg-amber-50 text-amber-700 border-amber-100' },
  subscription: { label: 'Subscription', className: 'bg-indigo-50 text-indigo-700 border-indigo-100' },
} as const;

const tagBase = 'inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium';

export const PropertyTags = memo(function PropertyTags({
  propertyType,
  isHoa,
  isSubscription,
  className,
}: PropertyTagsProps) {
  const tags: { key: string; label: string; cls: string }[] = [];

  if (propertyType === 'residential' || propertyType === 'commercial') {
    const cfg = TAG_CONFIG[propertyType];
    tags.push({ key: propertyType, label: cfg.label, cls: cfg.className });
  }
  if (isHoa) tags.push({ key: 'hoa', label: TAG_CONFIG.hoa.label, cls: TAG_CONFIG.hoa.className });
  if (isSubscription) tags.push({ key: 'subscription', label: TAG_CONFIG.subscription.label, cls: TAG_CONFIG.subscription.className });

  if (tags.length === 0) return null;

  return (
    <span className={cn('inline-flex flex-wrap gap-1', className)} data-testid="property-tags">
      {tags.map((t) => (
        <span key={t.key} className={cn(tagBase, t.cls)} data-testid={`property-tag-${t.key}`}>
          {t.label}
        </span>
      ))}
    </span>
  );
});
