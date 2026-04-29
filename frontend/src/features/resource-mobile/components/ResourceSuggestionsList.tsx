/**
 * ResourceSuggestionsList — Mobile suggestions for field resources.
 * Shows pre-job prep, upsell opportunities, departure timing, parts low, and pending approvals.
 */

import type { ResourceSuggestion } from '../types';

interface Props {
  suggestions: ResourceSuggestion[];
  onAccept: (suggestionId: string) => void;
}

const SUGGESTION_ICONS: Record<string, string> = {
  prejob_prep: '📋',
  upsell_opportunity: '💰',
  departure_timing: '🕐',
  parts_low: '📦',
  pending_approval: '⏳',
};

const SUGGESTION_LABELS: Record<string, string> = {
  prejob_prep: 'Pre-Job Prep',
  upsell_opportunity: 'Upsell Opportunity',
  departure_timing: 'Departure Timing',
  parts_low: 'Parts Low',
  pending_approval: 'Pending Approval',
};

export function ResourceSuggestionsList({ suggestions, onAccept }: Props) {
  return (
    <div data-testid="resource-suggestions-list" className="flex flex-col gap-2 p-4">
      <h3 className="text-sm font-semibold text-gray-700">Suggestions</h3>

      {suggestions.length === 0 ? (
        <p className="text-sm text-gray-400 py-2">No suggestions.</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {suggestions.map((suggestion) => (
            <li
              key={suggestion.id}
              data-testid={`resource-suggestion-${suggestion.id}`}
              className="bg-green-50 border border-green-200 rounded-xl p-3"
            >
              <div className="flex items-start gap-2">
                <span className="text-base" aria-hidden="true">
                  {SUGGESTION_ICONS[suggestion.type] ?? '💡'}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-semibold text-green-800">
                    {SUGGESTION_LABELS[suggestion.type] ?? suggestion.type}
                  </p>
                  <p className="text-sm font-medium text-gray-900">{suggestion.title}</p>
                  <p className="text-xs text-gray-600 mt-0.5">{suggestion.description}</p>
                  <button
                    onClick={() => onAccept(suggestion.id)}
                    className="mt-2 text-xs font-medium text-green-700 hover:text-green-900 transition-colors"
                    aria-label={`${suggestion.action_label}: ${suggestion.title}`}
                  >
                    {suggestion.action_label} →
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
