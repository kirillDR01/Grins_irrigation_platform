/**
 * MapFilters component - Filter panel with staff toggles.
 */

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
    <div data-testid="map-filters" className="bg-white rounded-xl shadow-md border border-slate-100 p-2 flex gap-2">
      {assignments.map((assignment) => {
        const isActive = visibleStaff.has(assignment.staff_name);
        return (
          <button
            key={assignment.staff_id}
            onClick={() => onStaffToggle(assignment.staff_name, !isActive)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              isActive
                ? 'bg-teal-100 text-teal-700'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
            data-testid={`staff-filter-${assignment.staff_name}`}
          >
            <div className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: getStaffColor(assignment.staff_name) }}
              />
              <span>{assignment.staff_name}</span>
            </div>
          </button>
        );
      })}
    </div>
  );
}
