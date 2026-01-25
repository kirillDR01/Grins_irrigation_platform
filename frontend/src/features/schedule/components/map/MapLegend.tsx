/**
 * MapLegend component - Shows staff colors and job counts.
 */

import { Card, CardContent } from '@/components/ui/card';
import type { ScheduleStaffAssignment } from '../../types';
import { getStaffColor } from '../../utils/staffColors';

interface MapLegendProps {
  assignments: ScheduleStaffAssignment[];
}

export function MapLegend({ assignments }: MapLegendProps) {
  if (assignments.length === 0) {
    return null;
  }

  return (
    <Card data-testid="map-legend" className="mt-4">
      <CardContent className="pt-4">
        <div className="flex flex-wrap gap-4">
          {assignments.map((assignment) => (
            <div
              key={assignment.staff_id}
              className="flex items-center gap-2"
              data-testid={`legend-staff-${assignment.staff_name}`}
            >
              <div
                className="w-4 h-4 rounded-full"
                style={{ backgroundColor: getStaffColor(assignment.staff_name) }}
              />
              <span className="text-sm font-medium">
                {assignment.staff_name}
              </span>
              <span className="text-sm text-muted-foreground">
                ({assignment.total_jobs} jobs)
              </span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
