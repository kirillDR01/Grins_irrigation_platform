/**
 * Staff color mapping for map visualization.
 * Each staff member has a consistent color across all views.
 */

export const STAFF_COLORS: Record<string, string> = {
  Viktor: '#14B8A6', // Teal-500
  Vas: '#8B5CF6', // Violet-500
  Dad: '#F59E0B', // Amber-500
  Gennadiy: '#F59E0B', // Amber-500 (alias for Dad)
  Steven: '#F43F5E', // Rose-500
  Vitallik: '#3B82F6', // Blue-500
};

export const UNASSIGNED_COLOR = '#64748B'; // Slate-500
export const DEFAULT_COLOR = '#10B981'; // Emerald-500 for additional staff

/**
 * Get the color for a staff member by name.
 * Returns DEFAULT_COLOR if staff name is not in the mapping.
 */
export function getStaffColor(staffName: string): string {
  return STAFF_COLORS[staffName] || DEFAULT_COLOR;
}

/**
 * Get all staff names that have assigned colors.
 */
export function getColoredStaffNames(): string[] {
  return Object.keys(STAFF_COLORS);
}
