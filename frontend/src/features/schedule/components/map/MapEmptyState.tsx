/**
 * MapEmptyState component - Empty state for no jobs, no schedule, all filtered.
 */

import { Card, CardContent } from '@/components/ui/card';
import { Calendar, MapPin } from 'lucide-react';

interface MapEmptyStateProps {
  type: 'no-jobs' | 'no-schedule' | 'all-filtered';
  date?: string;
}

export function MapEmptyState({ type, date }: MapEmptyStateProps) {
  const messages = {
    'no-jobs': {
      icon: Calendar,
      title: 'No jobs for this date',
      description: date
        ? `There are no jobs scheduled for ${date}. Try selecting a different date.`
        : 'There are no jobs scheduled for this date.',
    },
    'no-schedule': {
      icon: MapPin,
      title: 'Schedule not generated',
      description:
        'Generate a schedule to see job locations and routes on the map.',
    },
    'all-filtered': {
      icon: MapPin,
      title: 'No jobs match filters',
      description:
        'All jobs are hidden by the current filters. Try adjusting your filter selection.',
    },
  };

  const { icon: Icon, title, description } = messages[type];

  return (
    <Card data-testid="map-empty-state" className="h-[500px]">
      <CardContent className="flex flex-col items-center justify-center h-full text-center">
        <Icon className="h-12 w-12 text-muted-foreground mb-4" />
        <h3 className="text-lg font-semibold mb-2">{title}</h3>
        <p className="text-sm text-muted-foreground max-w-sm">{description}</p>
      </CardContent>
    </Card>
  );
}
