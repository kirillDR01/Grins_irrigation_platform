/**
 * PropertyDirectionsCard — address display with "Get directions" button.
 * Requirements: 8.1, 8.2, 8.3
 */

import { useState } from 'react';
import { MapsPickerPopover } from './MapsPickerPopover';

interface PropertyDirectionsCardProps {
  street: string;
  city: string;
  state: string;
  zip?: string | null;
  latitude?: number | null;
  longitude?: number | null;
}

export function PropertyDirectionsCard({
  street,
  city,
  state,
  zip,
  latitude,
  longitude,
}: PropertyDirectionsCardProps) {
  const [popoverOpen, setPopoverOpen] = useState(false);
  const fullAddress = [street, city, state, zip].filter(Boolean).join(', ');

  return (
    <div className="rounded-[14px] border border-[#E5E7EB] bg-white px-4 py-3">
      <p className="text-[10px] font-extrabold tracking-[0.6px] text-[#9CA3AF] uppercase mb-1.5">
        Property
      </p>
      <p className="text-[19px] font-extrabold text-[#0B1220] leading-tight">{street}</p>
      <p className="text-[15px] font-semibold text-[#4B5563] mt-0.5">
        {city}, {state}
        {zip ? ` ${zip}` : ''}
      </p>

      {/* Directions button with popover */}
      <div className="relative mt-3">
        <button
          type="button"
          onClick={() => setPopoverOpen((v) => !v)}
          className="w-full py-2.5 rounded-[10px] bg-[#1D4ED8] text-white text-[14px] font-bold hover:bg-[#1e40af] transition-colors"
        >
          Get directions
        </button>
        {popoverOpen && (
          <MapsPickerPopover
            address={fullAddress}
            latitude={latitude}
            longitude={longitude}
            onClose={() => setPopoverOpen(false)}
          />
        )}
      </div>
    </div>
  );
}
