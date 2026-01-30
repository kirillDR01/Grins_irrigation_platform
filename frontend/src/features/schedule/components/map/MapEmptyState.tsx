/**
 * MapEmptyState component - Empty state for no jobs, no schedule, all filtered.
 */

import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Calendar, MapPin } from 'lucide-react';

interface MapEmptyStateProps {
  type: 'no-jobs' | 'no-schedule' | 'all-filtered';
  date?: string;
  onAction?: () => void;
}

export function MapEmptyState({ type, date, onAction }: MapEmptyStateProps) {
  const messages = {
    'no-jobs': {
      icon: Calendar,
      title: 'No Jobs to Display',
      description: date
        ? `There are no jobs scheduled for ${date}. Try selecting a different date.`
        : 'There are no jobs scheduled for this date.',
      actionLabel: 'Add Jobs',
    },
    'no-schedule': {
      icon: MapPin,
      title: 'No Jobs to Display',
      description:
        'Generate a schedule to see job locations and routes on the map.',
      actionLabel: 'Generate Schedule',
    },
    'all-filtered': {
      icon: MapPin,
      title: 'No Jobs to Display',
      description:
        'All jobs are hidden by the current filters. Try adjusting your filter selection.',
      actionLabel: 'Clear Filters',
    },
  };

  const { icon: Icon, title, description, actionLabel } = messages[type];

  return (
    <Card data-testid="map-empty-state" className="h-[500px]">
      <CardContent className="flex flex-col items-center justify-center h-full py-12">
        <Icon className="w-16 h-16 text-slate-300" />
        <h3 className="text-lg font-semibold text-slate-600 mt-4">{title}</h3>
        <p className="text-sm text-slate-400 mt-2 text-center max-w-xs">
          {description}
        </p>
        {onAction && (
          <Button
            onClick={onAction}
            className="mt-6"
            data-testid="empty-state-action-btn"
          >
            {actionLabel}
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
