/**
 * ResourceSuggestionsList Component
 *
 * Mobile suggestions for the Resource role: pre-job prep,
 * upsell opportunity, departure timing, parts low, pending approval.
 */

import {
  ClipboardList,
  TrendingUp,
  Clock,
  Package,
  Hourglass,
  X,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  useResourceSuggestions,
  useDismissResourceSuggestion,
} from '../hooks/useResourceSchedule';
import type { ResourceSuggestion, ResourceSuggestionType } from '../types';

// ── Suggestion type config ─────────────────────────────────────────────

const SUGGESTION_CONFIG: Record<
  ResourceSuggestionType,
  { icon: typeof ClipboardList; color: string; bg: string }
> = {
  prejob_prep: {
    icon: ClipboardList,
    color: 'text-blue-600',
    bg: 'bg-blue-50',
  },
  upsell_opportunity: {
    icon: TrendingUp,
    color: 'text-green-600',
    bg: 'bg-green-50',
  },
  departure_timing: {
    icon: Clock,
    color: 'text-teal-600',
    bg: 'bg-teal-50',
  },
  parts_low: {
    icon: Package,
    color: 'text-amber-600',
    bg: 'bg-amber-50',
  },
  pending_approval: {
    icon: Hourglass,
    color: 'text-purple-600',
    bg: 'bg-purple-50',
  },
};

// ── Single suggestion card ─────────────────────────────────────────────

function SuggestionItem({
  suggestion,
  onDismiss,
}: {
  suggestion: ResourceSuggestion;
  onDismiss: (id: string) => void;
}) {
  const config =
    SUGGESTION_CONFIG[suggestion.suggestion_type] ??
    SUGGESTION_CONFIG.prejob_prep;
  const Icon = config.icon;

  return (
    <div
      className={`rounded-xl border border-slate-200 p-3 space-y-2 ${config.bg}`}
      data-testid={`resource-suggestion-${suggestion.id}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <Icon className={`h-4 w-4 flex-shrink-0 ${config.color}`} />
          <span className="font-medium text-slate-800 text-sm">
            {suggestion.title}
          </span>
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="h-6 w-6 p-0 text-slate-400 hover:text-red-500"
          onClick={() => onDismiss(suggestion.id)}
          aria-label="Dismiss suggestion"
        >
          <X className="h-3.5 w-3.5" />
        </Button>
      </div>

      <p className="text-xs text-slate-600 ml-6">{suggestion.description}</p>

      {suggestion.action_label && (
        <div className="ml-6">
          <Button
            variant="outline"
            size="sm"
            className="text-xs h-7"
            onClick={() => {
              if (suggestion.action_url) {
                window.location.href = suggestion.action_url;
              }
            }}
          >
            {suggestion.action_label}
          </Button>
        </div>
      )}

      <p className="text-xs text-slate-400 ml-6">
        {new Date(suggestion.created_at).toLocaleTimeString()}
      </p>
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────

export function ResourceSuggestionsList() {
  const { data: suggestions, isLoading, error } = useResourceSuggestions();
  const dismiss = useDismissResourceSuggestion();

  if (isLoading) {
    return (
      <div
        className="p-4 text-center text-slate-400 text-sm"
        data-testid="resource-suggestions-list"
      >
        Loading suggestions…
      </div>
    );
  }

  if (error) {
    return (
      <div
        className="p-4 text-center text-red-500 text-sm"
        data-testid="resource-suggestions-list"
      >
        Failed to load suggestions
      </div>
    );
  }

  const items = (suggestions ?? []).filter((s) => !s.is_dismissed);

  return (
    <div className="space-y-3 p-4" data-testid="resource-suggestions-list">
      <div className="flex items-center justify-between">
        <h3 className="font-bold text-slate-800">Suggestions</h3>
        {items.length > 0 && (
          <span className="rounded-full bg-green-100 text-green-700 px-2 py-0.5 text-xs font-medium">
            {items.length}
          </span>
        )}
      </div>

      {items.length === 0 ? (
        <p className="text-center text-slate-400 text-sm py-6">
          No suggestions right now
        </p>
      ) : (
        <div className="space-y-2">
          {items.map((suggestion) => (
            <SuggestionItem
              key={suggestion.id}
              suggestion={suggestion}
              onDismiss={(id) => dismiss.mutate(id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
