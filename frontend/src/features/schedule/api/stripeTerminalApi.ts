/**
 * Stripe Terminal API client for tap-to-pay integration.
 * Validates: Requirements 16.2, 16.6, 16.7
 */

import { apiClient } from '@/core/api/client';

interface ConnectionTokenResponse {
  secret: string;
}

interface CreatePaymentIntentRequest {
  amount_cents: number;
  currency?: string;
  description?: string;
}

export interface PaymentIntentResponse {
  id: string;
  client_secret: string;
  amount: number;
  currency: string;
  status: string;
}

export const stripeTerminalApi = {
  /**
   * Get a connection token for the Stripe Terminal SDK.
   */
  async getConnectionToken(): Promise<string> {
    const response = await apiClient.post<ConnectionTokenResponse>(
      '/stripe/terminal/connection-token'
    );
    return response.data.secret;
  },

  /**
   * Create a PaymentIntent for tap-to-pay collection.
   */
  async createPaymentIntent(
    data: CreatePaymentIntentRequest
  ): Promise<PaymentIntentResponse> {
    const response = await apiClient.post<PaymentIntentResponse>(
      '/stripe/terminal/create-payment-intent',
      data
    );
    return response.data;
  },
};
