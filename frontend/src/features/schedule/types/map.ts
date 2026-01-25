/**
 * Map-specific types for the schedule map view.
 */

export interface MapJob {
  job_id: string;
  customer_name: string;
  address: string | null;
  city: string | null;
  latitude: number | null;
  longitude: number | null;
  service_type: string;
  staff_id: string | null;
  staff_name: string | null;
  sequence_index: number | null;
  start_time: string | null;
  end_time: string | null;
  travel_time_minutes: number | null;
}

export interface MapRoute {
  staff_id: string;
  staff_name: string;
  color: string;
  start_location: { lat: number; lng: number };
  waypoints: Array<{
    lat: number;
    lng: number;
    job_id: string;
    sequence: number;
  }>;
  total_jobs: number;
  total_travel_minutes: number;
}

export interface MapUnscheduledJob {
  job_id: string;
  customer_name: string;
  address: string;
  city: string;
  latitude: number | null;
  longitude: number | null;
  service_type: string;
  zone_count: number | null;
  priority_level: number;
}

export type MapMode = 'planning' | 'scheduled';
export type ViewMode = 'list' | 'map';

export interface MapFilters {
  staffIds: string[];
  showRoutes: boolean;
  mode: MapMode;
}

export interface MapBounds {
  north: number;
  south: number;
  east: number;
  west: number;
}

export interface MapCenter {
  lat: number;
  lng: number;
}
