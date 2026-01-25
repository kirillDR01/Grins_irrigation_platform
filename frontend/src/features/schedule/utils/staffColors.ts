/**
 * Staff color mapping for map visualization.
 * Each staff member has a consistent color across all views.
 */

export const STAFF_COLORS: Record<string, string> = {
  Viktor: '#EF4444', // Red
  Vas: '#3B82F6', // Blue
  Dad: '#22C55E', // Green
  Gennadiy: '#22C55E', // Green (alias for Dad)
  Steven: '#F59E0B', // Amber
  Vitallik: '#8B5CF6', // Purple
};

export const UNASSIGNED_COLOR = '#6B7280'; // Gray
export const DEFAULT_COLOR = '#9CA3AF'; // Light gray for unknown

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
