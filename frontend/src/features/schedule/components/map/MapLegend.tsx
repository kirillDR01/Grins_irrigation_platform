/**
 * MapLegend component - Shows staff colors and job counts.
 */

import { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import type { ScheduleStaffAssignment } from '../../types';
import { getStaffColor } from '../../utils/staffColors';

interface MapLegendProps {
  assignments: ScheduleStaffAssignment[];
}

export function MapLegend({ assignments }: MapLegendProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  if (assignments.length === 0) {
    return null;
  }

  return (
    <div
      data-testid="map-legend"
      className="bg-white rounded-xl shadow-md border border-slate-100 p-4"
    >
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-slate-700">Staff Assignments</h3>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-slate-400 hover:text-slate-600 cursor-pointer transition-colors"
          data-testid="legend-toggle"
          aria-label={isExpanded ? 'Collapse legend' : 'Expand legend'}
        >
          {isExpanded ? (
            <ChevronUp className="w-4 h-4" />
          ) : (
            <ChevronDown className="w-4 h-4" />
          )}
        </button>
      </div>

      {isExpanded && (
        <div className="space-y-2">
          {assignments.map((assignment) => (
            <div
              key={assignment.staff_id}
              className="flex items-center gap-2 text-sm text-slate-600"
              data-testid={`legend-staff-${assignment.staff_name}`}
            >
              <div
                className="w-4 h-4 rounded-full"
                style={{ backgroundColor: getStaffColor(assignment.staff_name) }}
              />
              <span className="text-sm text-slate-600">
                {assignment.staff_name}
              </span>
              <span className="text-xs text-slate-400 ml-auto">
                ({assignment.total_jobs} jobs)
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
