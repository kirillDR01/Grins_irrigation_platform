/**
 * Resource mobile feature exports.
 */

// Types
export type {
  JobStatus,
  ResourceJobCard,
  ResourceDaySchedule,
  ResourceAlertType,
  ResourceAlert,
  ResourceSuggestionType,
  ResourceSuggestion,
  ResourceScheduleParams,
  ResourceAlertsParams,
  ResourceSuggestionsParams,
} from './types';

// API
export { resourceApi } from './api/resourceApi';

// Hooks
export {
  resourceKeys,
  useResourceSchedule,
  useResourceAlerts,
  useMarkAlertRead,
  useResourceSuggestions,
  useDismissResourceSuggestion,
} from './hooks/useResourceSchedule';

// Components
export { ResourceScheduleView } from './components/ResourceScheduleView';
export { ResourceAlertsList } from './components/ResourceAlertsList';
export { ResourceSuggestionsList } from './components/ResourceSuggestionsList';
export { ResourceMobileView } from './components/ResourceMobileView';
