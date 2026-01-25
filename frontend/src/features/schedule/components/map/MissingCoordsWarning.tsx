/**
 * MissingCoordsWarning component - Warning banner for jobs without coordinates.
 */

import { Card, CardContent } from '@/components/ui/card';
import { AlertTriangle } from 'lucide-react';

interface MissingCoordsWarningProps {
  count: number;
}

export function MissingCoordsWarning({ count }: MissingCoordsWarningProps) {
  if (count === 0) {
    return null;
  }

  return (
    <Card
      data-testid="missing-coords-warning"
      className="border-yellow-200 bg-yellow-50"
    >
      <CardContent className="flex items-center gap-2 py-3">
        <AlertTriangle className="h-4 w-4 text-yellow-600" />
        <span className="text-sm text-yellow-800">
          {count} job{count === 1 ? '' : 's'} cannot be displayed due to missing
          location data.
        </span>
      </CardContent>
    </Card>
  );
}
