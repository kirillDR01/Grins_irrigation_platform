/**
 * CapacityHeatMap — bottom row of the schedule grid showing daily utilization.
 * Color coding: >90% red (overbooking), 60–90% green (healthy), <60% yellow (underutilization).
 */

import { cn } from '@/shared/utils/cn';

export interface CapacityDay {
  date: string; // ISO date YYYY-MM-DD
  label: string; // e.g. "Mon 2/16"
  utilization: number; // 0–100
}

interface CapacityHeatMapProps {
  days: CapacityDay[];
}

function getColorClass(utilization: number): string {
  if (utilization > 90) return 'bg-red-100 text-red-800 border-red-200';
  if (utilization >= 60) return 'bg-green-100 text-green-800 border-green-200';
  return 'bg-yellow-100 text-yellow-800 border-yellow-200';
}

export function CapacityHeatMap({ days }: CapacityHeatMapProps) {
  return (
    <div
      data-testid="capacity-heat-map"
      className="flex border-t border-gray-200 bg-gray-50"
    >
      <div className="w-40 shrink-0 px-3 py-2 text-xs font-semibold text-gray-500 flex items-center">
        Capacity
      </div>
      {days.map((day) => (
        <div
          key={day.date}
          data-testid={`capacity-cell-${day.date}`}
          className={cn(
            'flex-1 px-2 py-2 text-center text-xs font-medium border-l border-gray-200',
            getColorClass(day.utilization)
          )}
        >
          {day.utilization.toFixed(0)}%
        </div>
      ))}
    </div>
  );
}
