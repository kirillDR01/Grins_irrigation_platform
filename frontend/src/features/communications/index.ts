// Components
export { CommunicationsDashboard } from './components';
export { CommunicationsQueue } from './components';
export { SentMessagesLog } from './components';

// Hooks
export {
  communicationsKeys,
  useUnaddressedCommunications,
  useUnaddressedCount,
  useMarkAddressed,
  useSentMessages,
} from './hooks';

// Types
export type {
  Communication,
  CommunicationChannel,
  CommunicationDirection,
  SentMessage,
  DeliveryStatus,
  SentMessageListParams,
  UnaddressedCountResponse,
} from './types';

// API
export { communicationsApi } from './api/communicationsApi';
