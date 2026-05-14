/**
 * Staff feature exports.
 */

// Types
export type {
  Staff,
  StaffCreate,
  StaffUpdate,
  StaffAvailabilityUpdate,
  StaffListParams,
  PaginatedStaffResponse,
  StaffRole,
  SkillLevel,
  ResetPasswordPayload,
} from './types';
export { STAFF_ROLES, SKILL_LEVELS } from './types';

// API
export { staffApi } from './api/staffApi';

// Hooks
export {
  staffKeys,
  useStaff,
  useStaffMember,
  useAvailableStaff,
  useCreateStaff,
  useUpdateStaff,
  useDeleteStaff,
  useUpdateStaffAvailability,
  useResetStaffPassword,
} from './hooks';

// Components
export {
  StaffList,
  StaffDetail,
  StaffForm,
  ResetPasswordDialog,
} from './components';
