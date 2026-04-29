import { useState } from 'react';
import { formatDistanceToNow } from 'date-fns';
import type { ChangeRequest } from '../types';
import { useApproveChangeRequest, useDenyChangeRequest } from '../hooks/useAlerts';

interface ChangeRequestCardProps {
  request: ChangeRequest;
}

export function ChangeRequestCard({ request }: ChangeRequestCardProps) {
  const [denyReason, setDenyReason] = useState('');
  const [showDenyInput, setShowDenyInput] = useState(false);
  const approve = useApproveChangeRequest();
  const deny = useDenyChangeRequest();

  const timeAgo = formatDistanceToNow(new Date(request.created_at), {
    addSuffix: true,
  });

  const handleApprove = () => {
    approve.mutate({ id: request.id });
  };

  const handleDeny = () => {
    if (!showDenyInput) {
      setShowDenyInput(true);
      return;
    }
    deny.mutate({ id: request.id, reason: denyReason || 'Denied by admin' });
    setShowDenyInput(false);
  };

  return (
    <div
      data-testid={`change-request-card-${request.id}`}
      className="border border-gray-200 rounded-lg p-4 space-y-2 bg-white"
    >
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold text-gray-800">
          {request.resource_name} — {request.request_type.replace(/_/g, ' ')}
        </span>
        <span className="text-xs text-gray-500">{timeAgo}</span>
      </div>
      <p className="text-sm text-gray-600">{request.details}</p>
      {request.recommended_action && (
        <p className="text-xs text-blue-600 font-medium">
          AI recommendation: {request.recommended_action}
        </p>
      )}
      {request.status === 'pending' && (
        <div className="space-y-2 pt-1">
          {showDenyInput && (
            <input
              type="text"
              value={denyReason}
              onChange={(e) => setDenyReason(e.target.value)}
              placeholder="Reason for denial..."
              className="w-full text-xs border border-gray-300 rounded px-2 py-1"
            />
          )}
          <div className="flex gap-2">
            <button
              onClick={handleApprove}
              disabled={approve.isPending}
              className="px-3 py-1 text-xs font-medium rounded-md bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
            >
              Approve
            </button>
            <button
              onClick={handleDeny}
              disabled={deny.isPending}
              className="px-3 py-1 text-xs font-medium rounded-md bg-white border border-red-400 text-red-600 hover:bg-red-50 disabled:opacity-50"
            >
              {showDenyInput ? 'Confirm Deny' : 'Deny'}
            </button>
          </div>
        </div>
      )}
      {request.status !== 'pending' && (
        <span
          className={`text-xs font-medium px-2 py-0.5 rounded-full ${
            request.status === 'approved'
              ? 'bg-green-100 text-green-700'
              : 'bg-red-100 text-red-700'
          }`}
        >
          {request.status}
        </span>
      )}
    </div>
  );
}
