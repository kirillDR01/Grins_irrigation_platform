// Business settings types (Req 87)

export interface BusinessSettings {
  company_name: string;
  company_address: string;
  company_phone: string;
  company_email: string;
  company_logo_url: string | null;
  company_website: string;
  default_payment_terms_days: number;
  late_fee_percentage: number;
  lien_warning_days: number;
  lien_filing_days: number;
  day_of_reminder_time: string; // "07:00"
  sms_time_window_start: string; // "08:00"
  sms_time_window_end: string; // "21:00"
  enable_delay_notifications: boolean;
  default_valid_days: number;
  follow_up_intervals_days: string; // "3,7,14,21"
  enable_auto_follow_ups: boolean;
}

export type BusinessSettingsKey = keyof BusinessSettings;

export interface BusinessSettingEntry {
  setting_key: string;
  setting_value: unknown;
  updated_at: string | null;
}
