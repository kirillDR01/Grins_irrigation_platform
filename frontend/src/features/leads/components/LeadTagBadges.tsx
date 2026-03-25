import { Badge } from '@/components/ui/badge';
import type { ActionTag } from '../types';
import { ACTION_TAG_LABELS, ACTION_TAG_COLORS } from '../types';

interface LeadTagBadgesProps {
  tags: ActionTag[];
  className?: string;
}

export function LeadTagBadges({ tags, className }: LeadTagBadgesProps) {
  if (!tags || tags.length === 0) return null;

  return (
    <div className={`flex flex-wrap gap-1 ${className ?? ''}`} data-testid="lead-tag-badges">
      {tags.map((tag) => (
        <Badge
          key={tag}
          variant="outline"
          className={`text-xs font-medium ${ACTION_TAG_COLORS[tag]}`}
          data-testid={`tag-${tag.toLowerCase()}`}
        >
          {ACTION_TAG_LABELS[tag]}
        </Badge>
      ))}
    </div>
  );
}
