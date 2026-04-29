// Public API for resource-mobile feature
export { ResourceScheduleView, ResourceAlertsList, ResourceSuggestionsList } from './components';
export { ResourceMobileView } from './components/ResourceMobileView';
export {
  useResourceSchedule,
  useResourceAlerts,
  useResourceSuggestions,
  useDismissResourceAlert,
  useAcceptResourceSuggestion,
  resourceKeys,
} from './hooks/useResourceSchedule';
export { resourceApi } from './api/resourceApi';
export type {
  ResourceJob,
  ResourceSchedule,
  ResourceAlert,
  ResourceSuggestion,
} from './types';
