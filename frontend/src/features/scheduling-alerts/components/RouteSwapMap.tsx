/**
 * RouteSwapMap — map visualization placeholder for route swap suggestions.
 * Shows before/after drive times for two resource routes with proposed swap.
 */

interface RouteSwapMapProps {
  resourceA: { name: string; beforeMinutes: number; afterMinutes: number };
  resourceB: { name: string; beforeMinutes: number; afterMinutes: number };
  onAccept?: () => void;
  onDismiss?: () => void;
}

export function RouteSwapMap({
  resourceA,
  resourceB,
  onAccept,
  onDismiss,
}: RouteSwapMapProps) {
  const totalSaved =
    resourceA.beforeMinutes +
    resourceB.beforeMinutes -
    (resourceA.afterMinutes + resourceB.afterMinutes);

  return (
    <div
      data-testid="route-swap-map"
      className="rounded-lg border border-gray-200 bg-white p-4"
    >
      <h4 className="mb-3 text-sm font-semibold text-gray-900">Route Swap Visualization</h4>

      {/* Placeholder map area */}
      <div className="mb-3 flex h-48 items-center justify-center rounded-md bg-gray-100 text-sm text-gray-400">
        Map visualization — integration pending
      </div>

      {/* Drive time comparison */}
      <div className="mb-3 grid grid-cols-2 gap-3 text-xs">
        <div className="rounded border border-gray-200 p-2">
          <div className="font-medium text-gray-900">{resourceA.name}</div>
          <div className="text-gray-500">
            Before: {resourceA.beforeMinutes} min → After: {resourceA.afterMinutes} min
          </div>
        </div>
        <div className="rounded border border-gray-200 p-2">
          <div className="font-medium text-gray-900">{resourceB.name}</div>
          <div className="text-gray-500">
            Before: {resourceB.beforeMinutes} min → After: {resourceB.afterMinutes} min
          </div>
        </div>
      </div>

      {totalSaved > 0 && (
        <p className="mb-3 text-xs font-medium text-green-700">
          Saves {totalSaved} min total drive time
        </p>
      )}

      <div className="flex gap-2">
        <button
          onClick={onAccept}
          className="rounded-md bg-green-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-green-700"
        >
          Accept Swap
        </button>
        <button
          onClick={onDismiss}
          className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50"
        >
          Dismiss
        </button>
      </div>
    </div>
  );
}
