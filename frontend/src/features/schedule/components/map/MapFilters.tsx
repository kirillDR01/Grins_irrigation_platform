/**
 * MapFilters component - Filter panel with staff toggles.
 */

import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import type { ScheduleStaffAssignment } from '../../types';
import { getStaffColor } from '../../utils/staffColors';

interface MapFiltersProps {
  assignments: ScheduleStaffAssignment[];
  visibleStaff: Set<string>;
  onStaffToggle: (staffName: string, checked: boolean) => void;
}

export function MapFilters({
  assignments,
  visibleStaff,
  onStaffToggle,
}: MapFiltersProps) {
  return (
    <div data-testid="map-filters" className="flex flex-wrap items-center gap-4">
      <span className="text-sm text-muted-foreground">Filter:</span>
      {assignments.map((assignment) => (
        <div
          key={assignment.staff_id}
          className="flex items-center space-x-2"
          data-testid={`staff-filter-${assignment.staff_name}`}
        >
          <Switch
            id={`staff-${assignment.staff_id}`}
            checked={visibleStaff.has(assignment.staff_name)}
            onCheckedChange={(checked) =>
              onStaffToggle(assignment.staff_name, checked)
            }
          />
          <div
            className="w-3 h-3 rounded-full"
            style={{ backgroundColor: getStaffColor(assignment.staff_name) }}
          />
          <Label
            htmlFor={`staff-${assignment.staff_id}`}
            className="text-sm font-normal cursor-pointer"
          >
            {assignment.staff_name}
          </Label>
        </div>
      ))}
    </div>
  );
}
