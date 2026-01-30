/**
 * MapErrorState component - Error state with retry button.
 */

import { Button } from '@/components/ui/button';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface MapErrorStateProps {
  error: string;
  onRetry?: () => void;
}

export function MapErrorState({ error, onRetry }: MapErrorStateProps) {
  return (
    <div 
      data-testid="map-error-state" 
      className="flex flex-col items-center justify-center h-full py-12 bg-red-50"
    >
      <AlertTriangle className="w-16 h-16 text-red-400" />
      <h3 className="text-lg font-semibold text-red-700 mt-4">Failed to load map</h3>
      <p className="text-sm text-red-500 mt-2 text-center max-w-xs">{error}</p>
      {onRetry && (
        <Button 
          onClick={onRetry} 
          className="bg-red-100 hover:bg-red-200 text-red-700 px-4 py-2 rounded-lg mt-4"
        >
          <RefreshCw className="mr-2 h-4 w-4" />
          Retry
        </Button>
      )}
    </div>
  );
}
