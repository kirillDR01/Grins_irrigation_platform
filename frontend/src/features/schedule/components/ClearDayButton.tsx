/**
 * ClearDayButton component.
 * Button to clear all appointments for a specific day.
 */

import { Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface ClearDayButtonProps {
  onClick: () => void;
  disabled?: boolean;
  /** Whether a day has been selected */
  hasSelectedDay?: boolean;
}

export function ClearDayButton({ onClick, disabled, hasSelectedDay = true }: ClearDayButtonProps) {
  const isDisabled = disabled || !hasSelectedDay;
  
  return (
    <Button
      variant="outline"
      size="sm"
      onClick={onClick}
      disabled={isDisabled}
      className="text-destructive border-destructive hover:bg-destructive/10 disabled:opacity-50 disabled:cursor-not-allowed"
      data-testid="clear-day-btn"
      title={!hasSelectedDay ? 'Select a day first to clear its appointments' : undefined}
    >
      <Trash2 className="mr-2 h-4 w-4" />
      Clear Day
    </Button>
  );
}
