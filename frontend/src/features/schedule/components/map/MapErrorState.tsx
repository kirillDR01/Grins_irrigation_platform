/**
 * MapErrorState component - Error state with retry button.
 */

import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { AlertCircle, RefreshCw } from 'lucide-react';

interface MapErrorStateProps {
  error: string;
  onRetry?: () => void;
}

export function MapErrorState({ error, onRetry }: MapErrorStateProps) {
  return (
    <Card data-testid="map-error-state" className="h-[500px] border-red-200">
      <CardContent className="flex flex-col items-center justify-center h-full text-center">
        <AlertCircle className="h-12 w-12 text-red-500 mb-4" />
        <h3 className="text-lg font-semibold mb-2">Failed to load map</h3>
        <p className="text-sm text-muted-foreground max-w-sm mb-4">{error}</p>
        {onRetry && (
          <Button onClick={onRetry} variant="outline">
            <RefreshCw className="mr-2 h-4 w-4" />
            Retry
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
