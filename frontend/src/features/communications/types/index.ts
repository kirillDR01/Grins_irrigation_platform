import type { PaginationParams } from '@/core/api';

// Communication channels and directions
export type CommunicationChannel = 'SMS' | 'EMAIL' | 'PHONE';
export type CommunicationDirection = 'INBOUND' | 'OUTBOUND';

// Inbound communication record
export interface Communication {
  id: string;
  customer_id: string;
  customer_name: string;
  channel: CommunicationChannel;
  direction: CommunicationDirection;
  content: string;
  addressed: boolean;
  addressed_at: string | null;
  addressed_by: string | null;
  created_at: string;
}

// Delivery status for outbound messages
export type DeliveryStatus = 'pending' | 'sent' | 'delivered' | 'failed';

// Sent message (outbound notification)
//
// NOTE: the backend may omit content/sent_at/recipient_name entirely for
// pending or failed rows (content is populated on insert but sent_at
// only lands after the provider confirms, and recipient_name is derived
// from an optional Customer/Lead FK). Treat all of these as nullable in
// the UI so the table doesn't crash on partial data.
export interface SentMessage {
  id: string;
  recipient_name: string | null;
  recipient_phone: string | null;
  message_type: string;
  content: string | null;
  delivery_status: DeliveryStatus;
  error_message: string | null;
  sent_at: string | null;
}

// Sent messages filter params
export interface SentMessageListParams extends PaginationParams {
  message_type?: string;
  delivery_status?: DeliveryStatus;
  date_from?: string;
  date_to?: string;
  search?: string;
}

// Unaddressed count response
export interface UnaddressedCountResponse {
  count: number;
}

// Campaign types (CallRail SMS Integration)
export type {
  CampaignType,
  CampaignStatus,
  RecipientDeliveryStatus,
  CustomerAudienceFilter,
  LeadAudienceFilter,
  AdHocAudienceFilter,
  TargetAudience,
  Campaign,
  CampaignCreate,
  CampaignRecipient,
  CampaignSendAccepted,
  CampaignCancelResult,
  CampaignStats,
  AudiencePreviewRecipient,
  AudiencePreview,
  CsvRejectedRow,
  CsvUploadResult,
  RateLimitInfo,
  WorkerHealth,
} from './campaign';
