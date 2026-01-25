/**
 * MapProvider component that wraps the application with Google Maps API context.
 */

import { LoadScript } from '@react-google-maps/api';
import type { ReactNode } from 'react';

const GOOGLE_MAPS_API_KEY = import.meta.env.VITE_GOOGLE_MAPS_API_KEY || '';

// Libraries to load with the Maps API
const LIBRARIES: ('places' | 'geometry' | 'drawing' | 'visualization')[] = [];

interface MapProviderProps {
  children: ReactNode;
}

export function MapProvider({ children }: MapProviderProps) {
  if (!GOOGLE_MAPS_API_KEY) {
    return (
      <div className="flex items-center justify-center h-64 bg-gray-100 rounded-lg">
        <p className="text-gray-500">
          Google Maps API key not configured. Please set VITE_GOOGLE_MAPS_API_KEY
          in your environment.
        </p>
      </div>
    );
  }

  return (
    <LoadScript googleMapsApiKey={GOOGLE_MAPS_API_KEY} libraries={LIBRARIES}>
      {children}
    </LoadScript>
  );
}
