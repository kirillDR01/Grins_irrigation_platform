/**
 * MapMarker component - Individual job marker with sequence number.
 */

import { Marker } from '@react-google-maps/api';
import type { Clusterer } from '@googlemaps/markerclusterer';
import { useMemo } from 'react';
import type { ScheduleJobAssignment } from '../../types';
import { getStaffColor, DEFAULT_COLOR } from '../../utils/staffColors';

interface MapMarkerProps {
  job: ScheduleJobAssignment;
  staffName: string | null;
  isSelected: boolean;
  onClick: () => void;
  displaySequence: number; // 1-indexed sequence to display
  clusterer?: Clusterer;
}

/**
 * Create an SVG marker icon with staff color and sequence number.
 */
function createMarkerIcon(
  color: string,
  sequenceIndex: number,
  isSelected: boolean
): google.maps.Icon {
  const size = isSelected ? 36 : 30;
  const fontSize = isSelected ? 14 : 12;
  const strokeWidth = isSelected ? 3 : 2;

  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
      <circle cx="${size / 2}" cy="${size / 2}" r="${size / 2 - strokeWidth}" 
        fill="${color}" 
        stroke="white" 
        stroke-width="${strokeWidth}"/>
      <text x="${size / 2}" y="${size / 2 + fontSize / 3}" 
        text-anchor="middle" 
        fill="white" 
        font-size="${fontSize}" 
        font-weight="bold" 
        font-family="Arial, sans-serif">
        ${sequenceIndex}
      </text>
    </svg>
  `;

  return {
    url: `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`,
    scaledSize: new google.maps.Size(size, size),
    anchor: new google.maps.Point(size / 2, size / 2),
  };
}

export function MapMarker({
  job,
  staffName,
  isSelected,
  onClick,
  displaySequence,
  clusterer,
}: MapMarkerProps) {
  const color = staffName ? getStaffColor(staffName) : DEFAULT_COLOR;

  const icon = useMemo(
    () => createMarkerIcon(color, displaySequence, isSelected),
    [color, displaySequence, isSelected]
  );

  // Skip markers without coordinates
  if (job.latitude === null || job.longitude === null) {
    return null;
  }

  return (
    <Marker
      position={{ lat: job.latitude, lng: job.longitude }}
      icon={icon}
      onClick={onClick}
      title={`${job.customer_name} - ${job.service_type}`}
      clusterer={clusterer}
    />
  );
}
