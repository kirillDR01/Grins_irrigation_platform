/**
 * ChangeRequestCard — resource change request with approve/deny buttons.
 */

import { useState } from 'react';
import type { ChangeRequest } from '../types';
import { useApproveChangeRequest, useDenyChangeRequest } from '../hooks/useAlerts';

interface ChangeRequestCardProps {
  request: ChangeRequest;
}

const REQUEST_TYPE_LABELS: Record<string, string> = {
  delay_report: 'Delay Report',
  followup_job: 'Follow-Up Job Request',
  access_issue: 'Access Issue',
  nearby_pickup: 'Nearby Pickup Request',
  resequence: 'Route Resequence',
  crew_assist: 'Crew Assistance',
  parts_log: 'Parts Log',
  upgrade_quote: 'Upgrade Quote',
};

export function ChangeRequestCard({ request }: ChangeRequestCardProps) {
  const [denyReason, setDenyReason] = useState('');
  const [showDenyInput, setShowDenyInput] = useState(false);
  const approve = useApproveChangeRequest();
  const deny = useDenyChangeRequest();

  const handleApprove = () => {
    approve.mutate({ id: request.id });
  };

  const handleDeny = () => {
    if (!showDenyInput) {
      setShowDenyInput(true);
      return;
    }
    if (denyReason.trim()) {
      deny.mutate({ id: request.id, data: { reason: denyReason.trim() } });
    }
  };

  const isPending = approve.isPending || deny.isPending;
  const typeLabel = REQUEST_TYPE_LABELS[request.request_type] ?? request.request_type;

  return (
    <div
      data-testid={`change-request-card-${request.id}`}
      className="rounded-lg border border-amber-200 bg-amber-50 p-3"
    >
      <div className="mb-1 flex items-center justify-between">
        <span className="text-sm font-semibold text-amber-800">
          📋 CHANGE REQUEST — {typeLabel}
        </span>
        <span className="rounded-full bg-amber-200 px-2 py-0.5 text-[10px] font-medium text-amber-800">
          {request.status}
        </span>
      </div>

      {request.resource_name && (
        <p className="mb-1 text-xs text-amber-700">
          From: <span className="font-medium">{request.resource_name}</span>
        </p>
      )}

      {request.recommended_action && (
        <p className="mb-2 text-xs text-amber-900">
          AI Recommendation: {request.recommended_action}
        </p>
      )}

      {request.details && Object.keys(request.details).length > 0 && (
        <div className="mb-2 rounded bg-amber-100/50 p-2 text-xs text-amber-800">
          {Object.entries(request.details).map(([key, value]) => (
            <div key={key}>
              <span className="font-medium">{key}:</span> {String(value)}
            </div>
          ))}
        </div>
      )}

      {showDenyInput && (
        <input
          type="text"
          value={denyReason}
          onChange={(e) => setDenyReason(e.target.value)}
          placeholder="Reason for denial..."
          className="mb-2 w-full rounded border border-amber-300 px-2 py-1 text-xs"
        />
      )}

      {request.status === 'pending' && (
        <div className="flex gap-2">
          <button
            onClick={handleApprove}
            disabled={isPending}
            className="rounded-md bg-green-600 px-2.5 py-1 text-xs font-medium text-white hover:bg-green-700 disabled:opacity-50"
          >
            Approve
          </button>
          <button
            onClick={handleDeny}
            disabled={isPending}
            className="rounded-md border border-red-300 bg-white px-2.5 py-1 text-xs font-medium text-red-700 hover:bg-red-50 disabled:opacity-50"
          >
            {showDenyInput ? 'Confirm Deny' : 'Deny'}
          </button>
        </div>
      )}
    </div>
  );
}
