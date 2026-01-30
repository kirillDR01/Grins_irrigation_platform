/**
 * MapLoadingState component - Loading spinner for map data.
 */

export function MapLoadingState() {
  return (
    <div data-testid="map-loading" className="flex flex-col items-center justify-center h-full py-12">
      <div className="w-12 h-12 border-4 border-teal-200 border-t-teal-500 rounded-full animate-spin" />
      <p className="text-slate-600 mt-4">Loading map...</p>
    </div>
  );
}
