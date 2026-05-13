import type { MouseEvent } from 'react';
import { MapPin, Navigation, Check, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Appointment } from '@/features/schedule/types';
import { deriveCardState } from '../utils/cardState';
import { buildMapsUrl } from '../utils/mapsLink';
import { formatTimeWindow } from '../utils/formatTimeWindow';

interface MobileJobCardProps {
  appointment: Appointment;
  onOpen: (id: string) => void;
}

export function MobileJobCard({ appointment, onOpen }: MobileJobCardProps) {
  const state = deriveCardState(appointment.status);
  if (state === 'hidden') return null;

  const property = appointment.property_summary ?? null;
  const fullAddress = property
    ? `${property.address}, ${property.city}, ${property.state}${
        property.zip_code ? ` ${property.zip_code}` : ''
      }`.trim()
    : '';

  const handleNavigate = (e: MouseEvent<HTMLButtonElement>) => {
    e.stopPropagation();
    if (!fullAddress) return;
    window.open(buildMapsUrl(fullAddress), '_blank', 'noopener,noreferrer');
  };

  const handleDetails = (e: MouseEvent<HTMLButtonElement>) => {
    e.stopPropagation();
    onOpen(appointment.id);
  };

  return (
    <div
      role="button"
      tabIndex={0}
      data-testid={`mobile-job-card-${state}`}
      data-appointment-id={appointment.id}
      onClick={() => onOpen(appointment.id)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') onOpen(appointment.id);
      }}
      className={cn(
        'relative bg-white rounded-2xl border border-slate-200 px-3.5 pt-3.5 pb-3',
        'border-l-4 border-l-blue-700 cursor-pointer',
        state === 'current' &&
          'border-teal-500 border-[1.5px] shadow-[0_6px_20px_rgba(20,184,166,0.18)]',
        state === 'complete' && 'opacity-75'
      )}
    >
      {state === 'current' && (
        <span className="absolute -top-2.5 left-3 bg-teal-600 text-white text-[9px] font-bold tracking-wider px-2 py-0.5 rounded">
          NOW · IN PROGRESS
        </span>
      )}

      <div className="flex justify-between gap-3">
        <div className="flex-1 min-w-0">
          {appointment.customer_name && (
            <p className="text-base font-bold text-slate-900 truncate">
              {appointment.customer_name}
            </p>
          )}
          {appointment.job_type && (
            <p className="text-sm text-slate-700 mt-1 font-medium truncate">
              {appointment.job_type}
            </p>
          )}
          {property && (
            <div className="flex items-start gap-1.5 mt-2 text-xs text-slate-600">
              <MapPin className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
              <div className="leading-snug">
                <div>{property.address}</div>
                <div>
                  {property.city}, {property.state}
                  {property.zip_code ? ` ${property.zip_code}` : ''}
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="flex flex-col items-end gap-1">
          <span
            className={cn(
              'font-mono text-xs font-bold whitespace-nowrap',
              state === 'current' ? 'text-teal-700' : 'text-slate-900'
            )}
          >
            {formatTimeWindow(
              appointment.time_window_start,
              appointment.time_window_end
            )}
          </span>
          {state === 'complete' && (
            <span className="bg-green-50 text-green-700 text-[10px] font-bold tracking-wider px-2 py-0.5 rounded">
              COMPLETE
            </span>
          )}
        </div>
      </div>

      {property &&
        (property.zone_count !== null || property.system_type !== null) && (
          <div className="flex flex-wrap gap-1.5 mt-3">
            {property.zone_count !== null && (
              <span className="bg-slate-100 text-slate-700 text-[11px] font-medium px-2 py-0.5 rounded">
                {property.zone_count} zones
              </span>
            )}
            {property.system_type && (
              <span className="bg-slate-100 text-slate-700 text-[11px] font-medium px-2 py-0.5 rounded">
                {formatSystemType(property.system_type)}
              </span>
            )}
          </div>
        )}

      <div className="mt-3">
        {state === 'current' && (
          <button
            type="button"
            onClick={handleDetails}
            className="w-full bg-teal-600 text-white text-sm font-semibold py-2.5 rounded-xl flex items-center justify-center gap-1"
          >
            Job details <ChevronRight className="w-4 h-4" />
          </button>
        )}
        {state === 'complete' && (
          <div className="space-y-2">
            <div className="flex items-center justify-center gap-1.5 bg-green-50 text-green-700 text-[11px] font-bold tracking-wider py-1.5 rounded">
              <Check className="w-3.5 h-3.5" />
              COMPLETE
            </div>
            <button
              type="button"
              onClick={handleDetails}
              className="w-full border border-slate-300 text-slate-700 text-sm font-semibold py-2.5 rounded-xl"
            >
              Job details
            </button>
          </div>
        )}
        {state === 'upcoming' && (
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={handleNavigate}
              disabled={!fullAddress}
              className="bg-slate-900 text-white text-sm font-semibold py-2.5 rounded-xl flex items-center justify-center gap-1.5 disabled:opacity-50"
            >
              <Navigation className="w-4 h-4" />
              Navigate
            </button>
            <button
              type="button"
              onClick={handleDetails}
              className="border border-slate-300 text-slate-700 text-sm font-semibold py-2.5 rounded-xl"
            >
              Job details
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function formatSystemType(systemType: string): string {
  const cleaned = systemType.replace(/_/g, ' ').toLowerCase();
  return cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
}
