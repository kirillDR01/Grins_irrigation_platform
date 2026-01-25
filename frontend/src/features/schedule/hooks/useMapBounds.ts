/**
 * useMapBounds hook - Calculates bounds to fit all markers with padding.
 */

import { useMemo, useCallback } from 'react';
import type { ScheduleStaffAssignment } from '../types';
import { BOUNDS_PADDING } from '../utils/mapStyles';

interface UseMapBoundsResult {
  bounds: google.maps.LatLngBounds | null;
  fitBounds: (map: google.maps.Map | null) => void;
}

export function useMapBounds(
  assignments: ScheduleStaffAssignment[]
): UseMapBoundsResult {
  // Calculate bounds from all markers
  const bounds = useMemo(() => {
    if (typeof google === 'undefined') {
      return null;
    }

    const latLngBounds = new google.maps.LatLngBounds();
    let hasPoints = false;

    for (const assignment of assignments) {
      // Add staff home location
      if (assignment.start_lat !== null && assignment.start_lng !== null) {
        latLngBounds.extend({
          lat: assignment.start_lat,
          lng: assignment.start_lng,
        });
        hasPoints = true;
      }

      // Add job locations
      for (const job of assignment.jobs) {
        if (job.latitude !== null && job.longitude !== null) {
          latLngBounds.extend({
            lat: job.latitude,
            lng: job.longitude,
          });
          hasPoints = true;
        }
      }
    }

    return hasPoints ? latLngBounds : null;
  }, [assignments]);

  // Function to fit map to bounds
  const fitBounds = useCallback(
    (map: google.maps.Map | null) => {
      if (map && bounds) {
        map.fitBounds(bounds, BOUNDS_PADDING);
      }
    },
    [bounds]
  );

  return { bounds, fitBounds };
}
