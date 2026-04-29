export interface ResourceJob {
  id: string;
  job_type: string;
  address: string;
  customer_name: string;
  estimated_duration_minutes: number;
  eta: string;
  status: 'scheduled' | 'in_progress' | 'completed';
  notes: string | null;
  gate_code: string | null;
  requires_special_prep: boolean;
  route_order: number;
}

export interface ResourceSchedule {
  date: string;
  staff_id: string;
  staff_name: string;
  jobs: ResourceJob[];
  total_drive_minutes: number;
}

export interface ResourceAlert {
  id: string;
  type:
    | 'job_added'
    | 'job_removed'
    | 'route_resequenced'
    | 'special_equipment'
    | 'customer_access';
  title: string;
  description: string;
  job_id: string | null;
  created_at: string;
}

export interface ResourceSuggestion {
  id: string;
  type:
    | 'prejob_prep'
    | 'upsell_opportunity'
    | 'departure_timing'
    | 'parts_low'
    | 'pending_approval';
  title: string;
  description: string;
  job_id: string | null;
  action_label: string;
  created_at: string;
}
