/**
 * StaffHomeMarker component - Marker for staff starting location showing "0".
 */

import { Marker, InfoWindow } from '@react-google-maps/api';
import { useMemo, useState } from 'react';
import { getStaffColor } from '../../utils/staffColors';

interface StaffHomeMarkerProps {
  staffId: string;
  staffName: string;
  lat: number;
  lng: number;
}

/**
 * Create a home marker icon with staff color border.
 * Task 88.1: w-10 h-10 rounded-full bg-white shadow-lg border-2 with staff color
 * Task 88.2: Home icon in staff color
 */
function createHomeIcon(color: string): google.maps.Icon {
  const size = 40; // w-10 h-10 = 40px

  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
      <!-- Shadow effect -->
      <defs>
        <filter id="shadow" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur in="SourceAlpha" stdDeviation="2"/>
          <feOffset dx="0" dy="2" result="offsetblur"/>
          <feComponentTransfer>
            <feFuncA type="linear" slope="0.3"/>
          </feComponentTransfer>
          <feMerge>
            <feMergeNode/>
            <feMergeNode in="SourceGraphic"/>
          </feMerge>
        </filter>
      </defs>
      <!-- Outer circle with border -->
      <circle cx="${size / 2}" cy="${size / 2}" r="${size / 2 - 2}" fill="white" stroke="${color}" stroke-width="2" filter="url(#shadow)"/>
      <!-- Home icon -->
      <path d="M ${size / 2} ${size / 2 - 6} L ${size / 2 + 6} ${size / 2} L ${size / 2 + 4} ${size / 2} L ${size / 2 + 4} ${size / 2 + 6} L ${size / 2 - 4} ${size / 2 + 6} L ${size / 2 - 4} ${size / 2} L ${size / 2 - 6} ${size / 2} Z" fill="${color}"/>
    </svg>
  `;

  return {
    url: `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`,
    scaledSize: new google.maps.Size(size, size),
    anchor: new google.maps.Point(size / 2, size / 2),
  };
}

export function StaffHomeMarker({
  staffId: _staffId,
  staffName,
  lat,
  lng,
}: StaffHomeMarkerProps) {
  const [showInfo, setShowInfo] = useState(false);
  const color = getStaffColor(staffName);
  const icon = useMemo(() => createHomeIcon(color), [color]);

  return (
    <>
      <Marker
        position={{ lat, lng }}
        icon={icon}
        title={`${staffName}'s starting point`}
        onClick={() => setShowInfo(true)}
        zIndex={1000} // Ensure start marker is always on top
        data-testid="staff-home-marker"
      />
      {showInfo && (
        <InfoWindow
          position={{ lat, lng }}
          onCloseClick={() => setShowInfo(false)}
        >
          {/* Task 88.3: Label with text-xs font-medium text-slate-600 bg-white px-2 py-1 rounded shadow-sm */}
          <div className="bg-white px-2 py-1 rounded shadow-sm">
            <div className="text-xs font-medium text-slate-600">{staffName}</div>
            <div className="text-xs text-slate-400">Starting Point</div>
          </div>
        </InfoWindow>
      )}
    </>
  );
}
