/**
 * useMapData hook - Transforms schedule data into map-friendly format.
 */

import { useMemo } from 'react';
import type { ScheduleGenerateResponse, ScheduleStaffAssignment } from '../types';
import type { MapJob, MapRoute } from '../types/map';
import { getStaffColor } from '../utils/staffColors';

interface UseMapDataResult {
  jobs: MapJob[];
  routes: MapRoute[];
  totalJobs: number;
  missingCoordinates: number;
}

export function useMapData(
  scheduleData: ScheduleGenerateResponse | null
): UseMapDataResult {
  return useMemo(() => {
    if (!scheduleData) {
      return {
        jobs: [],
        routes: [],
        totalJobs: 0,
        missingCoordinates: 0,
      };
    }

    const jobs: MapJob[] = [];
    const routes: MapRoute[] = [];
    let missingCoordinates = 0;

    for (const assignment of scheduleData.assignments) {
      // Build route for this staff
      const waypoints: MapRoute['waypoints'] = [];

      for (const job of assignment.jobs) {
        // Add to jobs list
        jobs.push({
          job_id: job.job_id,
          customer_name: job.customer_name,
          address: job.address,
          city: job.city,
          latitude: job.latitude,
          longitude: job.longitude,
          service_type: job.service_type,
          staff_id: assignment.staff_id,
          staff_name: assignment.staff_name,
          sequence_index: job.sequence_index,
          start_time: job.start_time,
          end_time: job.end_time,
          travel_time_minutes: job.travel_time_minutes,
        });

        // Track missing coordinates
        if (job.latitude === null || job.longitude === null) {
          missingCoordinates++;
        } else {
          // Add to route waypoints
          waypoints.push({
            lat: job.latitude,
            lng: job.longitude,
            job_id: job.job_id,
            sequence: job.sequence_index,
          });
        }
      }

      // Build route if we have start location and waypoints
      if (
        assignment.start_lat !== null &&
        assignment.start_lng !== null &&
        waypoints.length > 0
      ) {
        routes.push({
          staff_id: assignment.staff_id,
          staff_name: assignment.staff_name,
          color: getStaffColor(assignment.staff_name),
          start_location: {
            lat: assignment.start_lat,
            lng: assignment.start_lng,
          },
          waypoints,
          total_jobs: assignment.total_jobs,
          total_travel_minutes: assignment.total_travel_minutes,
        });
      }
    }

    return {
      jobs,
      routes,
      totalJobs: jobs.length,
      missingCoordinates,
    };
  }, [scheduleData]);
}
