/**
 * RoutePolyline component - Draws route lines connecting jobs in sequence.
 * Uses manual cleanup to ensure Google Maps removes the polyline.
 */

import { useEffect, useRef, useMemo, useState } from 'react';
import { useGoogleMap } from '@react-google-maps/api';
import type { ScheduleStaffAssignment } from '../../types';
import { getStaffColor } from '../../utils/staffColors';

interface RoutePolylineProps {
  assignment: ScheduleStaffAssignment;
  visible?: boolean;
  selected?: boolean;
}

export function RoutePolyline({ assignment, visible = true, selected = false }: RoutePolylineProps) {
  const map = useGoogleMap();
  const polylineRef = useRef<google.maps.Polyline | null>(null);
  const [isHovered, setIsHovered] = useState(false);
  const color = getStaffColor(assignment.staff_name);

  // Build path from start location through all jobs
  const path = useMemo(() => {
    const points: google.maps.LatLngLiteral[] = [];

    // Add start location if available
    if (assignment.start_lat !== null && assignment.start_lng !== null) {
      points.push({ lat: assignment.start_lat, lng: assignment.start_lng });
    }

    // Add job locations in sequence order
    const sortedJobs = [...assignment.jobs].sort(
      (a, b) => a.sequence_index - b.sequence_index
    );

    for (const job of sortedJobs) {
      if (job.latitude !== null && job.longitude !== null) {
        points.push({ lat: job.latitude, lng: job.longitude });
      }
    }

    return points;
  }, [assignment]);

  // Create/update/remove polyline manually
  useEffect(() => {
    if (!map || path.length < 2) {
      return;
    }

    // Determine styling based on state
    const strokeWeight = selected ? 6 : isHovered ? 5 : 4;
    const strokeOpacity = selected ? 0.8 : 0.6;

    // Create polyline if it doesn't exist
    if (!polylineRef.current) {
      polylineRef.current = new google.maps.Polyline({
        path,
        strokeColor: color,
        strokeOpacity,
        strokeWeight,
        map: visible ? map : null,
      });

      // Add hover listeners
      google.maps.event.addListener(polylineRef.current, 'mouseover', () => {
        setIsHovered(true);
      });
      google.maps.event.addListener(polylineRef.current, 'mouseout', () => {
        setIsHovered(false);
      });
    } else {
      // Update existing polyline
      polylineRef.current.setPath(path);
      polylineRef.current.setOptions({
        strokeColor: color,
        strokeOpacity,
        strokeWeight,
      });
      polylineRef.current.setMap(visible ? map : null);
    }

    // Cleanup on unmount - CRITICAL: setMap(null) removes from map
    return () => {
      if (polylineRef.current) {
        google.maps.event.clearInstanceListeners(polylineRef.current);
        polylineRef.current.setMap(null);
        polylineRef.current = null;
      }
    };
  }, [map, path, color, visible, selected, isHovered]);

  // Also update visibility when visible prop changes
  useEffect(() => {
    if (polylineRef.current) {
      polylineRef.current.setMap(visible ? map : null);
    }
  }, [visible, map]);

  return null; // We manage the polyline manually, no React component needed
}
