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
export interface SentMessage {
  id: string;
  recipient_name: string;
  recipient_phone: string | null;
  message_type: string;
  content: string;
  delivery_status: DeliveryStatus;
  error_message: string | null;
  sent_at: string;
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
