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
 * Create a circular marker with "0" for starting point.
 */
function createStartIcon(color: string): google.maps.Icon {
  const size = 32;

  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
      <circle cx="${size / 2}" cy="${size / 2}" r="${size / 2 - 2}" fill="${color}" stroke="white" stroke-width="2"/>
      <text x="${size / 2}" y="${size / 2 + 5}" text-anchor="middle" fill="white" font-family="Arial, sans-serif" font-size="14" font-weight="bold">0</text>
    </svg>
  `;

  return {
    url: `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`,
    scaledSize: new google.maps.Size(size, size),
    anchor: new google.maps.Point(size / 2, size / 2),
  };
}

export function StaffHomeMarker({
  staffId,
  staffName,
  lat,
  lng,
}: StaffHomeMarkerProps) {
  const [showInfo, setShowInfo] = useState(false);
  const color = getStaffColor(staffName);
  const icon = useMemo(() => createStartIcon(color), [color]);

  return (
    <>
      <Marker
        position={{ lat, lng }}
        icon={icon}
        title={`${staffName}'s starting point`}
        onClick={() => setShowInfo(true)}
        zIndex={1000} // Ensure start marker is always on top
      />
      {showInfo && (
        <InfoWindow
          position={{ lat, lng }}
          onCloseClick={() => setShowInfo(false)}
        >
          <div className="p-2">
            <div className="font-semibold">{staffName}</div>
            <div className="text-sm text-gray-600">Starting Point</div>
          </div>
        </InfoWindow>
      )}
    </>
  );
}
