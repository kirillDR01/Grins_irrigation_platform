/**
 * ClearResultsButton component.
 * Button to clear schedule generation results.
 */

import { X } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface ClearResultsButtonProps {
  onClear: () => void;
}

export function ClearResultsButton({ onClear }: ClearResultsButtonProps) {
  return (
    <Button
      variant="outline"
      size="sm"
      onClick={onClear}
      data-testid="clear-results-btn"
    >
      <X className="mr-2 h-4 w-4" />
      Clear Results
    </Button>
  );
}
