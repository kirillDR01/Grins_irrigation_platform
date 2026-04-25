import { useCustomer } from '@/features/customers';
import type { SalesEntry } from '../../types/pipeline';

type Props = {
  entry: SalesEntry;
};

export function PrefilledCustomerCard({ entry }: Props) {
  // Resolve email via the customer detail query (SalesEntry doesn't denormalize email).
  // Cached → near-instant on most renders; fine if it loads slightly after the modal mounts.
  const { data: customer } = useCustomer(entry.customer_id);

  return (
    <section
      role="group"
      aria-label="Customer information"
      data-testid="schedule-visit-customer-card"
      className="rounded-md border border-dashed border-slate-700 bg-amber-50 p-3 text-sm leading-relaxed"
    >
      <div className="text-xs uppercase tracking-wider text-slate-500 mb-1 font-bold">
        Customer
      </div>
      <div>
        <strong>{entry.customer_name ?? 'Unknown Customer'}</strong>
        {entry.lead_id ? (
          <span className="ml-2 text-xs text-slate-500">from Leads tab</span>
        ) : null}
      </div>
      {entry.customer_phone ? (
        <Row label="Phone" value={entry.customer_phone} />
      ) : null}
      {customer?.email ? <Row label="Email" value={customer.email} /> : null}
      {entry.property_address ? (
        <Row label="Address" value={entry.property_address} />
      ) : null}
      {entry.job_type ? <Row label="Job" value={entry.job_type} /> : null}
    </section>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span className="text-xs uppercase tracking-wider text-slate-500 mr-1">
        {label}
      </span>
      {value}
    </div>
  );
}
