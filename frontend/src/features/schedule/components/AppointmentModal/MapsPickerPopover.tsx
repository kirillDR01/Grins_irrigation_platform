/**
 * MapsPickerPopover — popover with Apple Maps and Google Maps options.
 * Requirements: 8.4, 8.5, 8.6, 8.7, 8.8, 18.3
 */

import { useEffect, useRef } from 'react';

interface MapsPickerPopoverProps {
  address: string;
  latitude?: number | null;
  longitude?: number | null;
  onClose: () => void;
}

export function MapsPickerPopover({
  address,
  latitude,
  longitude,
  onClose,
}: MapsPickerPopoverProps) {
  const ref = useRef<HTMLDivElement>(null);
  const encoded = encodeURIComponent(address);

  const appleMapsUrl = `maps://?daddr=${encoded}`;
  const appleMapsWebUrl = `https://maps.apple.com/?daddr=${encoded}`;
  const googleMapsUrl =
    latitude != null && longitude != null
      ? `https://www.google.com/maps/dir/?api=1&destination=${latitude},${longitude}`
      : `https://www.google.com/maps/dir/?api=1&destination=${encoded}`;

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [onClose]);

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [onClose]);

  // Focus first item on mount
  useEffect(() => {
    const first = ref.current?.querySelector<HTMLElement>('[role="menuitem"]');
    first?.focus();
  }, []);

  return (
    <div
      ref={ref}
      role="menu"
      aria-label="Open in maps"
      className="absolute left-0 right-0 bottom-full mb-2 bg-white rounded-[14px] border border-[#E5E7EB] shadow-[0_4px_20px_rgba(0,0,0,0.12)] overflow-hidden z-50"
    >
      <p className="px-4 pt-3 pb-1 text-[10px] font-extrabold tracking-[0.6px] text-[#9CA3AF] uppercase">
        Open in
      </p>
      <a
        href={appleMapsUrl}
        role="menuitem"
        onClick={onClose}
        onKeyDown={(e) => e.key === 'Enter' && onClose()}
        className="flex items-center gap-3 px-4 py-3 hover:bg-teal-50 focus:bg-teal-50 outline-none"
        // Fallback for non-iOS
        onError={() => {
          window.location.href = appleMapsWebUrl;
        }}
      >
        <div className="w-8 h-8 rounded-[8px] bg-teal-500 flex items-center justify-center flex-shrink-0">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path
              d="M8 1.5C5.51 1.5 3.5 3.51 3.5 6c0 3.75 4.5 8.5 4.5 8.5s4.5-4.75 4.5-8.5c0-2.49-2.01-4.5-4.5-4.5zm0 6.25a1.75 1.75 0 110-3.5 1.75 1.75 0 010 3.5z"
              fill="white"
            />
          </svg>
        </div>
        <span className="text-[15px] font-bold text-[#0B1220]">Apple Maps</span>
      </a>
      <a
        href={googleMapsUrl}
        target="_blank"
        rel="noopener noreferrer"
        role="menuitem"
        onClick={onClose}
        className="flex items-center gap-3 px-4 py-3 hover:bg-blue-50 focus:bg-blue-50 outline-none"
      >
        <div className="w-8 h-8 rounded-[8px] bg-blue-600 flex items-center justify-center flex-shrink-0">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path
              d="M8 1.5C5.51 1.5 3.5 3.51 3.5 6c0 3.75 4.5 8.5 4.5 8.5s4.5-4.75 4.5-8.5c0-2.49-2.01-4.5-4.5-4.5zm0 6.25a1.75 1.75 0 110-3.5 1.75 1.75 0 010 3.5z"
              fill="white"
            />
          </svg>
        </div>
        <span className="text-[15px] font-bold text-[#0B1220]">Google Maps</span>
      </a>
    </div>
  );
}
