/**
 * CapacityHeatMap — capacity row showing daily aggregate utilization percentages.
 * Color coding: >90% red (overbooking), 60–90% green (healthy), <60% yellow (underutilization).
 */

import { cn } from '@/shared/utils/cn';

export interface CapacityHeatMapData {
  day: string;
  utilization: number;
}

interface CapacityHeatMapProps {
  data: CapacityHeatMapData[];
}

function getUtilizationColor(utilization: number): string {
  if (utilization > 90) return 'bg-red-100 text-red-800 border-red-300';
  if (utilization >= 60) return 'bg-green-100 text-green-800 border-green-300';
  return 'bg-yellow-100 text-yellow-800 border-yellow-300';
}

function getUtilizationLabel(utilization: number): string {
  if (utilization > 90) return 'Overbooking risk';
  if (utilization >= 60) return 'Healthy';
  return 'Underutilized';
}

export function CapacityHeatMap({ data }: CapacityHeatMapProps) {
  return (
    <div
      data-testid="capacity-heat-map"
      className="flex border-t border-gray-200"
    >
      <div className="flex w-48 shrink-0 items-center border-r border-gray-200 bg-gray-50 px-3 py-2 text-xs font-semibold text-gray-600">
        Capacity
      </div>
      <div className="grid flex-1" style={{ gridTemplateColumns: `repeat(${data.length}, minmax(0, 1fr))` }}>
        {data.map((cell) => (
          <div
            key={cell.day}
            data-testid={`capacity-cell-${cell.day}`}
            className={cn(
              'flex flex-col items-center justify-center border-r border-gray-200 px-2 py-2 text-xs font-medium last:border-r-0',
              getUtilizationColor(cell.utilization)
            )}
            title={getUtilizationLabel(cell.utilization)}
          >
            <span className="text-sm font-bold">{Math.round(cell.utilization)}%</span>
            <span className="text-[10px] opacity-75">{getUtilizationLabel(cell.utilization)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
