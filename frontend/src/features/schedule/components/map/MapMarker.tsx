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
 * Updated styling: w-8 h-8 rounded-full shadow-md border-2 border-white
 */
function createMarkerIcon(
  color: string,
  sequenceIndex: number,
  isSelected: boolean,
  isActive: boolean = false
): google.maps.Icon {
  // Base size: 32px (w-8 h-8)
  const baseSize = 32;
  // Selected: scale-125 = 40px
  const size = isSelected ? 40 : baseSize;
  const fontSize = isSelected ? 14 : 12;
  // Border: 2px white border
  const strokeWidth = 2;
  
  // Ring for selected state: ring-4 ring-teal-200
  const ringSize = isSelected ? size + 16 : size;
  const ringStrokeWidth = isSelected ? 4 : 0;
  
  // Pulse animation ring for active jobs: ring-2 ring-teal-400
  const pulseRingSize = isActive ? size + 8 : size;
  const pulseRingStrokeWidth = isActive ? 2 : 0;

  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="${ringSize}" height="${ringSize}" viewBox="0 0 ${ringSize} ${ringSize}">
      ${isSelected ? `
        <circle cx="${ringSize / 2}" cy="${ringSize / 2}" r="${(ringSize - ringStrokeWidth) / 2}" 
          fill="none" 
          stroke="rgb(153, 246, 228)" 
          stroke-width="${ringStrokeWidth}"
          opacity="0.5"/>
      ` : ''}
      ${isActive ? `
        <circle cx="${ringSize / 2}" cy="${ringSize / 2}" r="${(pulseRingSize - pulseRingStrokeWidth) / 2}" 
          fill="none" 
          stroke="rgb(45, 212, 191)" 
          stroke-width="${pulseRingStrokeWidth}"
          opacity="0.6">
          <animate attributeName="r" from="${(pulseRingSize - pulseRingStrokeWidth) / 2}" to="${(ringSize - 4) / 2}" dur="1.5s" repeatCount="indefinite"/>
          <animate attributeName="opacity" from="0.6" to="0" dur="1.5s" repeatCount="indefinite"/>
        </circle>
      ` : ''}
      <circle cx="${ringSize / 2}" cy="${ringSize / 2}" r="${size / 2 - strokeWidth}" 
        fill="${color}" 
        stroke="white" 
        stroke-width="${strokeWidth}"
        filter="drop-shadow(0 4px 6px rgba(0, 0, 0, 0.1))"/>
      <text x="${ringSize / 2}" y="${ringSize / 2 + fontSize / 3}" 
        text-anchor="middle" 
        fill="white" 
        font-size="${fontSize}" 
        font-weight="bold" 
        font-family="Inter, Arial, sans-serif">
        ${sequenceIndex}
      </text>
    </svg>
  `;

  return {
    url: `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`,
    scaledSize: new google.maps.Size(ringSize, ringSize),
    anchor: new google.maps.Point(ringSize / 2, ringSize / 2),
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
  
  // Determine if job is active (in progress)
  const isActive = job.status === 'in_progress';

  const icon = useMemo(
    () => createMarkerIcon(color, displaySequence, isSelected, isActive),
    [color, displaySequence, isSelected, isActive]
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
      options={{
        // Add cursor pointer for hover state
        cursor: 'pointer',
      }}
      data-testid="map-marker"
    />
  );
}
