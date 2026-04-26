import { Phone, Mail, MapPin, Briefcase, ExternalLink } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useCustomer } from '@/features/customers';
import type { SalesEntry } from '../../types/pipeline';

type Props = {
  entry: SalesEntry;
};

function initials(name: string | null | undefined): string {
  if (!name) return '—';
  const parts = name.trim().split(/\s+/);
  const first = parts[0]?.[0] ?? '';
  const second = parts.length > 1 ? parts[parts.length - 1]?.[0] ?? '' : '';
  return (first + second).toUpperCase() || '—';
}

export function PrefilledCustomerCard({ entry }: Props) {
  const { data: customer } = useCustomer(entry.customer_id);
  const customerName = entry.customer_name ?? 'Unknown Customer';

  return (
    <section
      role="group"
      aria-label="Customer information"
      data-testid="schedule-visit-customer-card"
      className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-[0_1px_2px_rgba(15,23,42,0.06)]"
    >
      <div className="flex items-start gap-2.5 mb-2.5">
        <div className="flex h-9 w-9 flex-none items-center justify-center rounded-full bg-gradient-to-br from-slate-800 to-slate-600 text-[14px] font-bold tracking-tight text-white">
          {initials(customerName)}
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="m-0 text-[15px] font-bold leading-[1.2] text-slate-900">
            {customerName}
          </h3>
          {entry.lead_id && (
            <div className="mt-0.5 inline-flex items-center gap-1 text-[11.5px] text-slate-500">
              <ExternalLink size={11} strokeWidth={2.5} />
              from{' '}
              <Link
                to={`/leads/${entry.lead_id}`}
                className="font-semibold text-blue-700 no-underline hover:underline"
              >
                Leads · LD-{entry.lead_id.slice(0, 4).toUpperCase()}
              </Link>
            </div>
          )}
        </div>
      </div>

      <div className="flex flex-col gap-1.5">
        {entry.customer_phone && (
          <Row icon={<Phone size={14} strokeWidth={2} />}>
            <a
              href={`tel:${entry.customer_phone}`}
              className="font-mono font-semibold text-slate-800 no-underline hover:underline"
            >
              {entry.customer_phone}
            </a>
          </Row>
        )}
        {customer?.email && (
          <Row icon={<Mail size={14} strokeWidth={2} />}>
            <a
              href={`mailto:${customer.email}`}
              className="font-medium text-slate-800 no-underline hover:underline"
            >
              {customer.email}
            </a>
          </Row>
        )}
        {entry.property_address && (
          <Row icon={<MapPin size={14} strokeWidth={2} />}>
            <span className="font-medium text-slate-800">{entry.property_address}</span>
          </Row>
        )}
        {entry.job_type && (
          <Row icon={<Briefcase size={14} strokeWidth={2} />}>
            <span className="font-semibold text-slate-800">{entry.job_type}</span>
          </Row>
        )}
      </div>
    </section>
  );
}

function Row({ icon, children }: { icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[16px_1fr] items-center gap-2 text-[12.5px] text-slate-800">
      <span className="text-slate-400">{icon}</span>
      <span className="min-w-0 overflow-hidden text-ellipsis whitespace-nowrap">{children}</span>
    </div>
  );
}
