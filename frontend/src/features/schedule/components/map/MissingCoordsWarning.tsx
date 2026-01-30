/**
 * MissingCoordsWarning component - Warning banner for jobs without coordinates.
 */

import { AlertTriangle } from 'lucide-react';

interface MissingCoordsWarningProps {
  count: number;
}

export function MissingCoordsWarning({ count }: MissingCoordsWarningProps) {
  if (count === 0) {
    return null;
  }

  return (
    <div
      data-testid="missing-coords-warning"
      className="bg-amber-50 rounded-xl p-4 border border-amber-100"
    >
      <div className="flex items-start gap-3">
        <AlertTriangle className="h-5 w-5 text-amber-500 flex-shrink-0 mt-0.5" />
        <div className="flex-1">
          <h4 className="font-medium text-amber-800">
            Missing Location Data
          </h4>
          <p className="text-sm text-amber-600 mt-1">
            {count} job{count === 1 ? '' : 's'} cannot be displayed on the map due to missing coordinates.
          </p>
        </div>
      </div>
    </div>
  );
}
