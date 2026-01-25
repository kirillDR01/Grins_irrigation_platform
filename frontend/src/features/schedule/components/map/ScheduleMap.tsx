/**
 * ScheduleMap component - Main map container for schedule visualization.
 */

import { GoogleMap } from '@react-google-maps/api';
import { useCallback, useState, useMemo } from 'react';
import type { ScheduleStaffAssignment } from '../../types';
import { MAP_OPTIONS, DEFAULT_CENTER, DEFAULT_ZOOM } from '../../utils/mapStyles';
import { MapMarker } from './MapMarker';
import { MapLegend } from './MapLegend';
import { StaffHomeMarker } from './StaffHomeMarker';
import { RoutePolyline } from './RoutePolyline';
import { MapInfoWindow } from './MapInfoWindow';
import { MapFilters } from './MapFilters';
import { MapControls } from './MapControls';
import { MapEmptyState } from './MapEmptyState';
import { MissingCoordsWarning } from './MissingCoordsWarning';
import { MobileJobSheet } from './MobileJobSheet';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';

const containerStyle = {
  width: '100%',
  height: '500px',
};

interface ScheduleMapProps {
  assignments: ScheduleStaffAssignment[];
  selectedJobId: string | null;
  onJobSelect: (jobId: string | null) => void;
  showRoutes: boolean;
}

export function ScheduleMap({
  assignments,
  selectedJobId,
  onJobSelect,
  showRoutes: initialShowRoutes,
}: ScheduleMapProps) {
  const [map, setMap] = useState<google.maps.Map | null>(null);
  const [showRoutes, setShowRoutes] = useState(initialShowRoutes);
  const [visibleStaff, setVisibleStaff] = useState<Set<string>>(
    new Set(assignments.map((a) => a.staff_name))
  );

  const onLoad = useCallback((map: google.maps.Map) => {
    setMap(map);
  }, []);

  const onUnmount = useCallback(() => {
    setMap(null);
  }, []);

  // Close info window when clicking on map
  const handleMapClick = useCallback(() => {
    onJobSelect(null);
  }, [onJobSelect]);

  // Filter assignments by visible staff
  const filteredAssignments = useMemo(
    () => assignments.filter((a) => visibleStaff.has(a.staff_name)),
    [assignments, visibleStaff]
  );

  // Create a key suffix for route polylines to force re-render when filters change
  const visibleStaffKey = useMemo(
    () => Array.from(visibleStaff).sort().join(','),
    [visibleStaff]
  );

  // Count jobs missing coordinates
  const missingCoordsCount = useMemo(() => {
    let count = 0;
    for (const assignment of assignments) {
      for (const job of assignment.jobs) {
        if (job.latitude === null || job.longitude === null) {
          count++;
        }
      }
    }
    return count;
  }, [assignments]);

  // Get all jobs with coordinates, with per-staff display sequence (1-indexed)
  const allJobs = useMemo(() => {
    const jobs: Array<{
      job: ScheduleStaffAssignment['jobs'][0];
      staffName: string;
      displaySequence: number; // 1-indexed sequence within this staff's jobs
    }> = [];
    for (const assignment of filteredAssignments) {
      // Sort jobs by sequence_index to get correct order
      const sortedJobs = [...assignment.jobs].sort(
        (a, b) => a.sequence_index - b.sequence_index
      );
      let displaySeq = 1;
      for (const job of sortedJobs) {
        if (job.latitude !== null && job.longitude !== null) {
          jobs.push({ job, staffName: assignment.staff_name, displaySequence: displaySeq });
          displaySeq++;
        }
      }
    }
    return jobs;
  }, [filteredAssignments]);

  // Find selected job and its staff name
  const selectedJobInfo = useMemo(() => {
    if (!selectedJobId) return null;
    for (const assignment of filteredAssignments) {
      const job = assignment.jobs.find((j) => j.job_id === selectedJobId);
      if (job) {
        return { job, staffName: assignment.staff_name };
      }
    }
    return null;
  }, [selectedJobId, filteredAssignments]);

  // Handle staff filter toggle
  const handleStaffToggle = (staffName: string, checked: boolean) => {
    setVisibleStaff((prev) => {
      const next = new Set(prev);
      if (checked) {
        next.add(staffName);
      } else {
        next.delete(staffName);
      }
      return next;
    });
  };

  // Fit bounds to show all markers
  const handleFitBounds = useCallback(() => {
    if (!map || filteredAssignments.length === 0) return;

    const bounds = new google.maps.LatLngBounds();
    let hasPoints = false;

    for (const assignment of filteredAssignments) {
      if (assignment.start_lat && assignment.start_lng) {
        bounds.extend({ lat: assignment.start_lat, lng: assignment.start_lng });
        hasPoints = true;
      }
      for (const job of assignment.jobs) {
        if (job.latitude && job.longitude) {
          bounds.extend({ lat: job.latitude, lng: job.longitude });
          hasPoints = true;
        }
      }
    }

    if (hasPoints) {
      map.fitBounds(bounds, 50);
    }
  }, [map, filteredAssignments]);

  // Show empty state if no assignments at all
  if (assignments.length === 0) {
    return <MapEmptyState type="no-schedule" />;
  }

  const allFiltered = filteredAssignments.length === 0;

  return (
    <div data-testid="schedule-map" className="space-y-4">
      {/* Missing coordinates warning */}
      {missingCoordsCount > 0 && (
        <MissingCoordsWarning count={missingCoordsCount} />
      )}

      {/* Controls Row - always visible so user can toggle filters back */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        {/* Filters */}
        <MapFilters
          assignments={assignments}
          visibleStaff={visibleStaff}
          onStaffToggle={handleStaffToggle}
        />

        {/* Show Routes Toggle */}
        <div className="flex items-center gap-2">
          <Switch
            id="show-routes"
            checked={showRoutes}
            onCheckedChange={setShowRoutes}
            data-testid="show-routes-toggle"
          />
          <Label htmlFor="show-routes">Show Routes</Label>
        </div>

        {/* Map Controls */}
        <MapControls onFitBounds={handleFitBounds} />
      </div>

      {/* Map or Empty State */}
      {allFiltered ? (
        <MapEmptyState type="all-filtered" />
      ) : (
        <div className="relative">
          <GoogleMap
            mapContainerStyle={containerStyle}
            center={DEFAULT_CENTER}
            zoom={DEFAULT_ZOOM}
            options={MAP_OPTIONS}
            onLoad={onLoad}
            onUnmount={onUnmount}
            onClick={handleMapClick}
          >
            {/* Layer 1: Route polylines (bottom) */}
            {assignments.map((assignment) => {
              const isVisible = showRoutes && visibleStaff.has(assignment.staff_name);
              return (
                <RoutePolyline
                  key={`route-${assignment.staff_id}-${isVisible}`}
                  assignment={assignment}
                  visible={isVisible}
                />
              );
            })}

            {/* Layer 2: Job markers */}
            {allJobs.map(({ job, staffName, displaySequence }) => (
              <MapMarker
                key={job.job_id}
                job={job}
                staffName={staffName}
                isSelected={selectedJobId === job.job_id}
                onClick={() => onJobSelect(job.job_id)}
                displaySequence={displaySequence}
              />
            ))}

            {/* Layer 3: Staff home markers (rendered after jobs to be on top) */}
            {filteredAssignments.map(
              (assignment) =>
                assignment.start_lat !== null &&
                assignment.start_lng !== null && (
                  <StaffHomeMarker
                    key={`home-${assignment.staff_id}`}
                    staffId={assignment.staff_id}
                    staffName={assignment.staff_name}
                    lat={assignment.start_lat}
                    lng={assignment.start_lng}
                  />
                )
            )}

            {/* Layer 4: Info window for selected job */}
            {selectedJobInfo && (
              <MapInfoWindow
                job={selectedJobInfo.job}
                staffName={selectedJobInfo.staffName}
                onClose={() => onJobSelect(null)}
              />
            )}
          </GoogleMap>
        </div>
      )}

      {/* Legend */}
      <MapLegend assignments={filteredAssignments} />

      {/* Mobile Job Sheet */}
      {selectedJobInfo && (
        <MobileJobSheet
          job={selectedJobInfo.job}
          staffName={selectedJobInfo.staffName}
          onClose={() => onJobSelect(null)}
        />
      )}
    </div>
  );
}
