// PrefilledCustomerCard.tsx
// Read-only block at the top of the left column. NO edit affordances —
// edits live on the Lead detail screen. This component never owns mutable
// state; it's a pure render of the customer data.

import React from 'react';
import type { CustomerSummary } from './data-shapes';

export function PrefilledCustomerCard({ customer }: { customer: CustomerSummary }) {
  return (
    <section className="prefilled" role="group" aria-label="Customer information">
      <label className="fl">Customer</label>
      <div>
        <strong>{customer.name}</strong>{' '}
        {customer.source === 'lead' ? (
          <span className="pf-label">from Leads tab</span>
        ) : null}
      </div>
      {customer.phone ? <Row label="Phone" value={customer.phone} /> : null}
      {customer.email ? <Row label="Email" value={customer.email} /> : null}
      {customer.address ? <Row label="Address" value={customer.address} /> : null}
      <Row label="Job" value={customer.job_summary} />
    </section>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span className="pf-label">{label}</span> {value}
    </div>
  );
}
