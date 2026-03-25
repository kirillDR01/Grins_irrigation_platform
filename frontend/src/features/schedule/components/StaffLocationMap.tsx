/**
 * Staff location map with real-time tracking and staff panel (Req 41).
 * Google Maps embed showing staff pins with tooltips.
 * Auto-refreshes every 30 seconds via TanStack Query refetchInterval.
 * Includes a staff panel listing active staff with current appointment,
 * time elapsed, and estimated time remaining.
 */

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { MapPin, Clock, User, RefreshCw, AlertCircle } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { LoadingSpinner } from '@/shared/components/LoadingSpinner';
import { appointmentApi } from '../api/appointmentApi';
import type { StaffLocation } from '../types';

const REFETCH_INTERVAL = 30_000; // 30 seconds

/** Query key factory for staff locations */
export const staffLocationKeys = {
  all: ['staff', 'locations'] as const,
};

interface StaffLocationMapProps {
  /** Estimated duration per appointment in minutes (used for time remaining calc) */
  defaultEstimatedMinutes?: number;
}

export function StaffLocationMap({
  defaultEstimatedMinutes = 60,
}: StaffLocationMapProps) {
  const [selectedStaffId, setSelectedStaffId] = useState<string | null>(null);

  const {
    data: locations,
    isLoading,
    error,
    dataUpdatedAt,
  } = useQuery({
    queryKey: staffLocationKeys.all,
    queryFn: () => appointmentApi.getStaffLocations(),
    refetchInterval: REFETCH_INTERVAL,
  });

  const activeStaff = locations?.filter((loc) => loc.current_appointment) ?? [];
  const selectedLocation = locations?.find((l) => l.staff_id === selectedStaffId);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64" data-testid="staff-map-loading">
        <LoadingSpinner />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 text-center" data-testid="staff-map-error">
        <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center mx-auto mb-2">
          <AlertCircle className="h-5 w-5 text-red-600" />
        </div>
        <p className="text-sm text-slate-800 font-medium">Failed to load staff locations</p>
        <p className="text-xs text-slate-500 mt-1">Please try again later</p>
      </div>
    );
  }

  const lastUpdated = dataUpdatedAt
    ? new Date(dataUpdatedAt).toLocaleTimeString()
    : null;

  return (
    <div data-testid="staff-location-map" className="flex flex-col gap-4">
      {/* Map Section */}
      <div className="relative rounded-xl overflow-hidden border border-slate-200 bg-slate-100">
        <div className="h-80 relative" data-testid="staff-map-embed">
          {/* Google Maps embed with staff pin markers */}
          <StaffMapEmbed
            locations={locations ?? []}
            selectedStaffId={selectedStaffId}
            onSelectStaff={setSelectedStaffId}
          />
        </div>

        {/* Last updated indicator */}
        {lastUpdated && (
          <div className="absolute top-2 right-2 flex items-center gap-1.5 bg-white/90 backdrop-blur-sm rounded-lg px-2 py-1 text-xs text-slate-500 shadow-sm">
            <RefreshCw className="h-3 w-3" />
            <span>Updated {lastUpdated}</span>
          </div>
        )}
      </div>

      {/* Staff Panel */}
      <div className="bg-white rounded-xl border border-slate-200" data-testid="staff-panel">
        <div className="px-4 py-3 border-b border-slate-100">
          <h3 className="text-sm font-semibold text-slate-800">
            Active Staff ({activeStaff.length})
          </h3>
        </div>
        <div className="divide-y divide-slate-100">
          {activeStaff.length === 0 ? (
            <div className="p-4 text-center text-xs text-slate-500">
              No active staff members
            </div>
          ) : (
            activeStaff.map((staff) => (
              <StaffPanelRow
                key={staff.staff_id}
                staff={staff}
                defaultEstimatedMinutes={defaultEstimatedMinutes}
                isSelected={staff.staff_id === selectedStaffId}
                onSelect={() =>
                  setSelectedStaffId(
                    staff.staff_id === selectedStaffId ? null : staff.staff_id
                  )
                }
              />
            ))
          )}
        </div>
      </div>

      {/* Selected staff tooltip detail */}
      {selectedLocation && (
        <div
          className="bg-white rounded-xl border border-teal-200 p-3"
          data-testid="staff-detail-tooltip"
        >
          <div className="flex items-center gap-2 mb-1">
            <div className="w-6 h-6 rounded-full bg-teal-100 flex items-center justify-center">
              <User className="h-3.5 w-3.5 text-teal-600" />
            </div>
            <span className="text-sm font-medium text-slate-800">
              {selectedLocation.staff_name}
            </span>
          </div>
          <div className="pl-8 space-y-0.5 text-xs text-slate-600">
            <p>Appointment: {selectedLocation.current_appointment ?? 'None'}</p>
            <p>Time elapsed: {selectedLocation.time_elapsed_minutes} min</p>
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

interface StaffMapEmbedProps {
  locations: StaffLocation[];
  selectedStaffId: string | null;
  onSelectStaff: (id: string) => void;
}

/**
 * Google Maps embed placeholder with staff pin markers.
 * In production this would use @react-google-maps/api or similar.
 */
function StaffMapEmbed({
  locations,
  selectedStaffId,
  onSelectStaff,
}: StaffMapEmbedProps) {
  if (locations.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-slate-400 text-sm">
        <MapPin className="h-5 w-5 mr-2" />
        No staff locations available
      </div>
    );
  }

  return (
    <div className="relative h-full bg-slate-200" data-testid="map-container">
      {/* Map background placeholder */}
      <div className="absolute inset-0 flex items-center justify-center text-slate-400 text-xs">
        Google Maps
      </div>

      {/* Staff pin markers */}
      {locations.map((loc) => {
        const isSelected = loc.staff_id === selectedStaffId;
        return (
          <Button
            key={loc.staff_id}
            variant="ghost"
            size="sm"
            className={`absolute p-1 rounded-full ${
              isSelected
                ? 'bg-teal-500 text-white shadow-lg scale-110'
                : 'bg-white text-teal-600 shadow-md hover:bg-teal-50'
            }`}
            style={{
              // Normalize lat/lng to percentage positions within the map
              left: `${((loc.longitude + 180) / 360) * 100}%`,
              top: `${((90 - loc.latitude) / 180) * 100}%`,
            }}
            onClick={() => onSelectStaff(loc.staff_id)}
            data-testid={`staff-pin-${loc.staff_id}`}
            title={`${loc.staff_name} — ${loc.current_appointment ?? 'Idle'} — ${loc.time_elapsed_minutes} min`}
          >
            <MapPin className="h-4 w-4" />
          </Button>
        );
      })}
    </div>
  );
}

interface StaffPanelRowProps {
  staff: StaffLocation;
  defaultEstimatedMinutes: number;
  isSelected: boolean;
  onSelect: () => void;
}

function StaffPanelRow({
  staff,
  defaultEstimatedMinutes,
  isSelected,
  onSelect,
}: StaffPanelRowProps) {
  const estimatedRemaining = Math.max(
    0,
    defaultEstimatedMinutes - staff.time_elapsed_minutes
  );

  return (
    <button
      type="button"
      className={`w-full text-left px-4 py-3 flex items-center justify-between hover:bg-slate-50 transition-colors ${
        isSelected ? 'bg-teal-50' : ''
      }`}
      onClick={onSelect}
      data-testid={`staff-row-${staff.staff_id}`}
    >
      <div className="flex items-center gap-2.5">
        <div className="w-7 h-7 rounded-full bg-teal-100 flex items-center justify-center">
          <User className="h-3.5 w-3.5 text-teal-600" />
        </div>
        <div>
          <p className="text-sm font-medium text-slate-800">{staff.staff_name}</p>
          <p className="text-xs text-slate-500">
            {staff.current_appointment ?? 'No active appointment'}
          </p>
        </div>
      </div>
      <div className="flex items-center gap-3 text-xs">
        <div className="flex items-center gap-1 text-slate-500">
          <Clock className="h-3 w-3" />
          <span data-testid={`elapsed-${staff.staff_id}`}>
            {staff.time_elapsed_minutes}m elapsed
          </span>
        </div>
        <Badge
          className="bg-slate-100 text-slate-600 text-[10px] px-1.5 py-0.5"
          data-testid={`remaining-${staff.staff_id}`}
        >
          ~{estimatedRemaining}m left
        </Badge>
      </div>
    </button>
  );
}
