/**
 * Staff types matching backend schemas.
 */

export type StaffRole = 'tech' | 'sales' | 'admin';
export type SkillLevel = 'junior' | 'senior' | 'lead';

export interface Staff {
  id: string;
  name: string;
  phone: string;
  email: string | null;
  role: StaffRole;
  skill_level: SkillLevel | null;
  certifications: string[] | null;
  is_available: boolean;
  availability_notes: string | null;
  hourly_rate: number | null;
  is_active: boolean;
  // Cluster F — admin-set auth surface.
  username: string | null;
  is_login_enabled: boolean;
  last_login: string | null;
  locked_until: string | null;
  created_at: string;
  updated_at: string;
}

export interface StaffCreate {
  name: string;
  phone: string;
  email?: string | null;
  role: StaffRole;
  skill_level?: SkillLevel | null;
  certifications?: string[] | null;
  hourly_rate?: number | null;
  is_available?: boolean;
  availability_notes?: string | null;
  // Cluster F — optional credentials on create (admin only).
  username?: string;
  password?: string;
  is_login_enabled?: boolean;
}

export interface StaffUpdate {
  name?: string;
  phone?: string;
  email?: string | null;
  role?: StaffRole;
  skill_level?: SkillLevel | null;
  certifications?: string[] | null;
  hourly_rate?: number | null;
  is_active?: boolean;
  // Cluster F — optional credential rotation on update (admin only).
  username?: string;
  password?: string;
  is_login_enabled?: boolean;
}

export interface ResetPasswordPayload {
  new_password: string;
}

export interface StaffAvailabilityUpdate {
  is_available: boolean;
  availability_notes?: string | null;
}

export interface StaffListParams {
  page?: number;
  page_size?: number;
  role?: StaffRole;
  skill_level?: SkillLevel;
  is_available?: boolean;
  is_active?: boolean;
  search?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface PaginatedStaffResponse {
  items: Staff[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export const STAFF_ROLES: { value: StaffRole; label: string }[] = [
  { value: 'tech', label: 'Technician' },
  { value: 'sales', label: 'Sales' },
  { value: 'admin', label: 'Admin' },
];

export const SKILL_LEVELS: { value: SkillLevel; label: string }[] = [
  { value: 'junior', label: 'Junior' },
  { value: 'senior', label: 'Senior' },
  { value: 'lead', label: 'Lead' },
];
