/**
 * ClearDayButton component.
 * Button to clear all appointments for a specific day.
 */

import { Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface ClearDayButtonProps {
  onClick: () => void;
  disabled?: boolean;
}

export function ClearDayButton({ onClick, disabled }: ClearDayButtonProps) {
  return (
    <Button
      variant="outline"
      size="sm"
      onClick={onClick}
      disabled={disabled}
      className="text-destructive border-destructive hover:bg-destructive/10"
      data-testid="clear-day-btn"
    >
      <Trash2 className="mr-2 h-4 w-4" />
      Clear Day
    </Button>
  );
}
