/**
 * Inline duplicate customer warning banner.
 *
 * Displays when Tier 1 duplicate check finds matching customers
 * during creation or lead conversion.
 *
 * Validates: Requirement 6.13
 */

import { AlertTriangle, UserCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { Customer } from '../types';

interface DuplicateWarningProps {
  matches: Customer[];
  onUseExisting: (customer: Customer) => void;
}

export function DuplicateWarning({ matches, onUseExisting }: DuplicateWarningProps) {
  if (matches.length === 0) return null;

  return (
    <div
      className="rounded-lg border border-amber-300 bg-amber-50 p-3 space-y-2"
      data-testid="duplicate-warning"
    >
      <div className="flex items-center gap-2 text-amber-800 text-sm font-medium">
        <AlertTriangle className="h-4 w-4 shrink-0" />
        Possible match found
      </div>
      {matches.map((c) => (
        <div
          key={c.id}
          className="flex items-center justify-between gap-2 text-sm text-amber-700"
        >
          <span>
            {c.first_name} {c.last_name} — {c.phone}
            {c.email ? ` — ${c.email}` : ''}
          </span>
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="shrink-0 border-amber-400 text-amber-800 hover:bg-amber-100"
            onClick={() => onUseExisting(c)}
            data-testid={`use-existing-${c.id}`}
          >
            <UserCheck className="mr-1 h-3 w-3" />
            Use existing
          </Button>
        </div>
      ))}
    </div>
  );
}
