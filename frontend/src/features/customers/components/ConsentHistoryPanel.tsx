/**
 * ConsentHistoryPanel (Gap 06).
 *
 * Chronological list of SmsConsentRecord rows for a customer, newest
 * first. Rendered on CustomerDetail under the comm-prefs accordion so
 * admins can audit every consent state change.
 */
import { memo } from 'react';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useCustomerConsentHistory } from '../hooks/useConsentHistory';

interface ConsentHistoryPanelProps {
  customerId: string;
}

function formatTimestamp(ts: string): string {
  const d = new Date(ts);
  return d.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

export const ConsentHistoryPanel = memo(function ConsentHistoryPanel({
  customerId,
}: ConsentHistoryPanelProps) {
  const { data, isLoading, error } = useCustomerConsentHistory(customerId);

  return (
    <Card data-testid="consent-history-panel">
      <CardHeader>
        <CardTitle className="text-base">SMS Consent History</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading && <div className="text-sm text-gray-500">Loading consent history…</div>}
        {error && (
          <div className="text-sm text-red-600">Failed to load consent history.</div>
        )}
        {data && data.items.length === 0 && (
          <div className="text-sm text-gray-500" data-testid="consent-history-empty">
            No consent events recorded for this customer yet.
          </div>
        )}
        {data && data.items.length > 0 && (
          <ul className="space-y-3" data-testid="consent-history-list">
            {data.items.map((entry) => (
              <li
                key={entry.id}
                className="flex flex-col border-b border-gray-100 pb-3 last:border-b-0 last:pb-0"
                data-testid="consent-history-row"
              >
                <div className="flex items-center gap-2">
                  <Badge
                    variant="secondary"
                    className={
                      entry.consent_given
                        ? 'bg-emerald-100 text-emerald-700'
                        : 'bg-red-100 text-red-700'
                    }
                  >
                    {entry.consent_given ? 'Opted in' : 'Opted out'}
                  </Badge>
                  <span className="text-xs text-gray-500">
                    {formatTimestamp(entry.consent_timestamp)}
                  </span>
                </div>
                <div className="mt-1 text-sm text-gray-700">
                  <span className="font-medium">Method:</span> {entry.consent_method}
                  {entry.created_by_staff_id && (
                    <span className="ml-2 text-xs text-gray-500">
                      (actor {entry.created_by_staff_id.slice(0, 8)}…)
                    </span>
                  )}
                </div>
                {entry.consent_language_shown && (
                  <div className="mt-1 text-xs text-gray-500 italic">
                    "{entry.consent_language_shown}"
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
});
