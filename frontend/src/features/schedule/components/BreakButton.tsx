/**
 * Break button with type selector (Req 42).
 * "Take Break" button with dropdown for break type (Lunch, Gas, Personal, Other).
 * Shows active break indicator when break is in progress with "End Break" option.
 */

import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Coffee, Loader2, Fuel, User, MoreHorizontal, Square } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { appointmentApi } from '../api/appointmentApi';
import type { BreakType, StaffBreak } from '../types';

const BREAK_OPTIONS: { type: BreakType; label: string; icon: typeof Coffee }[] = [
  { type: 'lunch', label: 'Lunch', icon: Coffee },
  { type: 'gas', label: 'Gas', icon: Fuel },
  { type: 'personal', label: 'Personal', icon: User },
  { type: 'other', label: 'Other', icon: MoreHorizontal },
];

interface BreakButtonProps {
  staffId: string;
  /** Currently active break, if any */
  activeBreak?: StaffBreak | null;
  onBreakChange?: (brk: StaffBreak | null) => void;
}

export function BreakButton({
  staffId,
  activeBreak = null,
  onBreakChange,
}: BreakButtonProps) {
  const queryClient = useQueryClient();
  const [currentBreak, setCurrentBreak] = useState<StaffBreak | null>(
    activeBreak
  );

  const startBreakMutation = useMutation({
    mutationFn: (breakType: BreakType) =>
      appointmentApi.startBreak(staffId, { break_type: breakType }),
    onSuccess: (data) => {
      setCurrentBreak(data);
      onBreakChange?.(data);
      queryClient.invalidateQueries({ queryKey: ['appointments'] });
      toast.success('Break Started', {
        description: `${data.break_type.charAt(0).toUpperCase() + data.break_type.slice(1)} break started.`,
      });
    },
    onError: () => {
      toast.error('Error', { description: 'Failed to start break.' });
    },
  });

  const endBreakMutation = useMutation({
    mutationFn: () => {
      if (!currentBreak) throw new Error('No active break');
      return appointmentApi.endBreak(staffId, currentBreak.id);
    },
    onSuccess: () => {
      setCurrentBreak(null);
      onBreakChange?.(null);
      queryClient.invalidateQueries({ queryKey: ['appointments'] });
      toast.success('Break Ended', { description: 'Break has been ended.' });
    },
    onError: () => {
      toast.error('Error', { description: 'Failed to end break.' });
    },
  });

  const isLoading = startBreakMutation.isPending || endBreakMutation.isPending;

  // Active break state — show indicator + end break button
  if (currentBreak) {
    const breakLabel =
      currentBreak.break_type.charAt(0).toUpperCase() +
      currentBreak.break_type.slice(1);

    return (
      <div
        className="flex items-center gap-2"
        data-testid="break-active-indicator"
      >
        <div className="flex items-center gap-1.5 px-2 py-1 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-700">
          <Coffee className="h-3 w-3" />
          <span data-testid="break-type-label">{breakLabel} Break</span>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="border-red-200 text-red-600 hover:bg-red-50 h-7 text-xs"
          onClick={() => endBreakMutation.mutate()}
          disabled={isLoading}
          data-testid="end-break-btn"
        >
          {endBreakMutation.isPending ? (
            <Loader2 className="mr-1 h-3 w-3 animate-spin" />
          ) : (
            <Square className="mr-1 h-3 w-3" />
          )}
          End Break
        </Button>
      </div>
    );
  }

  // Default state — dropdown to select break type
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className="border-slate-200 text-slate-700 hover:bg-slate-50 h-8 text-xs"
          disabled={isLoading}
          data-testid="take-break-btn"
        >
          {startBreakMutation.isPending ? (
            <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
          ) : (
            <Coffee className="mr-1.5 h-3.5 w-3.5" />
          )}
          Take Break
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" data-testid="break-type-menu">
        {BREAK_OPTIONS.map(({ type, label, icon: Icon }) => (
          <DropdownMenuItem
            key={type}
            onClick={() => startBreakMutation.mutate(type)}
            data-testid={`break-option-${type}`}
          >
            <Icon className="mr-2 h-3.5 w-3.5" />
            {label}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
