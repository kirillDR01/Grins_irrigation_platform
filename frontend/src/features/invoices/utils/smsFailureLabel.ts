import type { SendPaymentLinkResponse } from '../types';

type SmsFailureReason = NonNullable<SendPaymentLinkResponse['sms_failure_reason']>;

const SMS_FAILURE_LABEL: Record<SmsFailureReason, string> = {
  consent: 'opted out',
  rate_limit: 'rate-limited; retrying shortly',
  provider_error: 'provider error; will retry',
  no_phone: 'no phone on file',
};

export function humanizeSmsFailure(reason: SmsFailureReason): string {
  return SMS_FAILURE_LABEL[reason];
}
