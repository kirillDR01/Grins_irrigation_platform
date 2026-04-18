/**
 * CustomerContextBlock — read-only customer context for appointment modals.
 *
 * Displays customer name, phone (tap-to-call), primary address (maps link),
 * job type, last_contacted_at, preferred_service_time, is_priority badge,
 * dogs_on_property warning, gate_code, access_instructions,
 * is_red_flag/is_slow_payer pills. Groups safety warnings separately.
 *
 * Validates: april-16th-fixes-enhancements Requirement 10A
 */

import {
  Phone,
  MapPin,
  AlertTriangle,
  Dog,
  Star,
  Clock,
  Shield,
  Key,
  Info,
  ExternalLink,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { format } from 'date-fns';

interface CustomerContextData {
  customer_name?: string;
  customer_phone?: string;
  primary_address?: string;
  primary_city?: string;
  primary_state?: string;
  primary_zip?: string;
  job_type?: string;
  last_contacted_at?: string;
  preferred_service_time?: string;
  is_priority?: boolean;
  dogs_on_property?: boolean;
  gate_code?: string;
  access_instructions?: string;
  is_red_flag?: boolean;
  is_slow_payer?: boolean;
}

interface CustomerContextBlockProps {
  data: CustomerContextData;
}

function formatAddress(data: CustomerContextData): string | null {
  const parts = [
    data.primary_address,
    [data.primary_city, data.primary_state].filter(Boolean).join(', '),
    data.primary_zip,
  ].filter(Boolean);
  return parts.length > 0 ? parts.join(' ') : null;
}

function getMapsUrl(address: string): string {
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(address)}`;
}

export function CustomerContextBlock({ data }: CustomerContextBlockProps) {
  const address = formatAddress(data);
  const hasSafetyWarnings =
    data.dogs_on_property ||
    data.is_red_flag ||
    data.is_slow_payer ||
    data.is_priority ||
    data.gate_code;

  return (
    <div
      className="rounded-lg border border-slate-200 bg-slate-50 p-4 space-y-3"
      data-testid="customer-context-block"
    >
      {/* Biographical info */}
      <div className="space-y-2">
        {data.customer_name && (
          <p className="text-sm font-semibold text-slate-800" data-testid="ctx-customer-name">
            {data.customer_name}
          </p>
        )}

        {data.customer_phone && (
          <div className="flex items-center gap-2">
            <Phone className="h-3.5 w-3.5 text-slate-400" />
            <a
              href={`tel:${data.customer_phone}`}
              className="text-sm text-teal-600 hover:text-teal-700 underline-offset-2 hover:underline"
              data-testid="ctx-customer-phone"
            >
              {data.customer_phone}
            </a>
          </div>
        )}

        {address && (
          <div className="flex items-center gap-2">
            <MapPin className="h-3.5 w-3.5 text-slate-400" />
            <a
              href={getMapsUrl(address)}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-teal-600 hover:text-teal-700 underline-offset-2 hover:underline flex items-center gap-1"
              data-testid="ctx-address"
            >
              {address}
              <ExternalLink className="h-3 w-3" />
            </a>
          </div>
        )}

        {data.job_type && (
          <div className="flex items-center gap-2">
            <Info className="h-3.5 w-3.5 text-slate-400" />
            <span className="text-sm text-slate-600" data-testid="ctx-job-type">
              {data.job_type}
            </span>
          </div>
        )}

        {data.last_contacted_at && (
          <div className="flex items-center gap-2">
            <Clock className="h-3.5 w-3.5 text-slate-400" />
            <span className="text-xs text-slate-500" data-testid="ctx-last-contacted">
              Last contacted{' '}
              {format(new Date(data.last_contacted_at), 'MMM d, yyyy')}
            </span>
          </div>
        )}

        {data.preferred_service_time && (
          <div className="flex items-center gap-2">
            <Clock className="h-3.5 w-3.5 text-slate-400" />
            <span className="text-xs text-slate-500" data-testid="ctx-preferred-time">
              Preferred: {data.preferred_service_time}
            </span>
          </div>
        )}
      </div>

      {/* Safety & operational warnings */}
      {hasSafetyWarnings && (
        <div className="border-t border-slate-200 pt-2 space-y-1.5" data-testid="ctx-warnings">
          <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
            Warnings & Access
          </p>
          <div className="flex flex-wrap gap-1.5">
            {data.is_priority && (
              <Badge
                className="bg-amber-100 text-amber-800 border-amber-200 text-[10px] px-1.5 py-0"
                data-testid="ctx-priority-badge"
              >
                <Star className="h-3 w-3 mr-0.5" />
                Priority
              </Badge>
            )}
            {data.is_red_flag && (
              <Badge
                className="bg-red-100 text-red-800 border-red-200 text-[10px] px-1.5 py-0"
                data-testid="ctx-red-flag-pill"
              >
                <AlertTriangle className="h-3 w-3 mr-0.5" />
                Red Flag
              </Badge>
            )}
            {data.is_slow_payer && (
              <Badge
                className="bg-orange-100 text-orange-800 border-orange-200 text-[10px] px-1.5 py-0"
                data-testid="ctx-slow-payer-pill"
              >
                <Shield className="h-3 w-3 mr-0.5" />
                Slow Payer
              </Badge>
            )}
            {data.dogs_on_property && (
              <Badge
                className="bg-yellow-100 text-yellow-800 border-yellow-200 text-[10px] px-1.5 py-0"
                data-testid="ctx-dogs-warning"
              >
                <Dog className="h-3 w-3 mr-0.5" />
                Dogs on Property
              </Badge>
            )}
          </div>

          {data.gate_code && (
            <div className="flex items-center gap-1.5 text-xs text-slate-600">
              <Key className="h-3 w-3 text-slate-400" />
              <span data-testid="ctx-gate-code">Gate: {data.gate_code}</span>
            </div>
          )}

          {data.access_instructions && (
            <p
              className="text-xs text-slate-600 pl-4.5"
              data-testid="ctx-access-instructions"
            >
              {data.access_instructions}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
