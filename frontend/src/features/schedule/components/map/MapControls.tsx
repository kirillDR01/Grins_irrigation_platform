/**
 * MapControls component - Fit bounds button.
 */

import { Button } from '@/components/ui/button';
import { Maximize2 } from 'lucide-react';

interface MapControlsProps {
  onFitBounds: () => void;
}

export function MapControls({ onFitBounds }: MapControlsProps) {
  return (
    <Button
      variant="outline"
      size="sm"
      onClick={onFitBounds}
      data-testid="fit-bounds-btn"
    >
      <Maximize2 className="h-4 w-4 mr-2" />
      Fit All
    </Button>
  );
}
