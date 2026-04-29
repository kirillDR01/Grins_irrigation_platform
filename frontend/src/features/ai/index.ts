/**
 * Public API for the AI feature.
 * Re-exports all components, hooks, and types.
 */

// Components
export {
  AILoadingState,
  AIErrorState,
  AIStreamingText,
  AIQueryChat,
  AIScheduleGenerator,
  AICategorization,
  AICommunicationDrafts,
  AIEstimateGenerator,
  MorningBriefing,
  CommunicationsQueue,
  SchedulingChat,
  ResourceMobileChat,
  PreJobChecklist,
} from './components/index';

// Hooks
export { useSchedulingChat, schedulingChatKeys } from './hooks/useSchedulingChat';
export type { ChatMessage } from './hooks/useSchedulingChat';

// Types
export type {
  ScheduleChange,
  ChatRequest,
  ChatResponse,
  PreJobChecklist as PreJobChecklistData,
  CriterionResult,
} from './types/aiScheduling';
