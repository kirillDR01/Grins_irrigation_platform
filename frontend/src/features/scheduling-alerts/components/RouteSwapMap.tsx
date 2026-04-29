/**
 * RouteSwapMap — map visualization for route swap suggestions.
 * Shows before/after drive times for two resource routes.
 */
interface RouteSwapMapProps {
  affectedJobIds: string[];
  affectedStaffIds: string[];
  onAccept?: () => void;
  onDismiss?: () => void;
}

export function RouteSwapMap({
  affectedJobIds,
  affectedStaffIds,
  onAccept,
  onDismiss,
}: RouteSwapMapProps) {
  return (
    <div
      data-testid="route-swap-map"
      className="rounded-lg border border-gray-200 p-4 space-y-3"
    >
      <div className="text-sm font-medium text-gray-700">Route Swap Preview</div>
      <div className="bg-gray-100 rounded h-40 flex items-center justify-center text-sm text-gray-500">
        Map visualization — {affectedStaffIds.length} resources,{' '}
        {affectedJobIds.length} jobs
      </div>
      <div className="flex gap-2">
        {onAccept && (
          <button
            onClick={onAccept}
            className="px-3 py-1 text-xs font-medium rounded-md bg-green-600 text-white hover:bg-green-700"
          >
            Accept Swap
          </button>
        )}
        {onDismiss && (
          <button
            onClick={onDismiss}
            className="px-3 py-1 text-xs font-medium rounded-md bg-white border border-gray-300 text-gray-600 hover:bg-gray-50"
          >
            Keep Current
          </button>
        )}
      </div>
    </div>
  );
}
