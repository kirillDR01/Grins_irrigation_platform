/**
 * @deprecated Architecture C (Stripe Payment Links via SMS) replaces
 * Tap-to-Pay terminal collection as of 2026-04-28. New code MUST NOT
 * import this client; use `useSendPaymentLink` from the invoices feature
 * instead. The file is retained until backend `/stripe/terminal/*`
 * routes are removed in a follow-up cleanup PR.
 *
 * References:
 * - Plan of record: `.agents/plans/stripe-tap-to-pay-and-invoicing.md`
 * - Operational runbook: `docs/payments-runbook.md`
 *
 * Validates (legacy): Requirements 16.2, 16.6, 16.7.
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
