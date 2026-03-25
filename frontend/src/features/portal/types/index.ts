// Portal types — public-facing, no internal IDs exposed

export interface PortalBusinessInfo {
  company_name: string;
  company_logo_url: string | null;
  company_address: string | null;
  company_phone: string | null;
}

// Estimate portal types
export interface PortalEstimateLineItem {
  item: string;
  description: string;
  unit_price: number;
  quantity: number;
}

export interface PortalEstimateTier {
  name: string;
  line_items: PortalEstimateLineItem[];
  total: number;
}

export interface PortalEstimate {
  business: PortalBusinessInfo;
  customer_name: string;
  estimate_number: string;
  status: string;
  line_items: PortalEstimateLineItem[];
  tiers: PortalEstimateTier[] | null;
  subtotal: number;
  tax_amount: number;
  discount_amount: number;
  total: number;
  promotion_code: string | null;
  notes: string | null;
  valid_until: string | null;
  created_at: string;
  is_readonly: boolean;
}

export interface PortalApproveRequest {
  selected_tier?: string;
}

export interface PortalRejectRequest {
  reason?: string;
}

// Contract portal types
export interface PortalContract {
  business: PortalBusinessInfo;
  customer_name: string;
  contract_body: string;
  terms_and_conditions: string | null;
  is_signed: boolean;
  signed_at: string | null;
}

export interface PortalSignRequest {
  signature_data: string; // base64 PNG from canvas
}

// Invoice portal types
export interface PortalInvoiceLineItem {
  description: string;
  quantity: number;
  unit_price: number;
  total: number;
}

export interface PortalInvoice {
  business: PortalBusinessInfo;
  invoice_number: string;
  invoice_date: string;
  due_date: string;
  customer_name: string;
  line_items: PortalInvoiceLineItem[];
  total_amount: number;
  amount_paid: number;
  balance_due: number;
  payment_status: string;
  stripe_payment_url: string | null;
}

// Error response for expired tokens
export interface PortalExpiredResponse {
  message: string;
  contact_phone: string | null;
  contact_email: string | null;
}
