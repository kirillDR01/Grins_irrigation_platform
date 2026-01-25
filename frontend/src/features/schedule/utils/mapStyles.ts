/**
 * Google Maps styling configuration.
 * Clean, minimal styling focused on route visualization.
 */

// Map styles to reduce visual clutter
export const MAP_STYLES: google.maps.MapTypeStyle[] = [
  // Hide POIs (points of interest)
  { featureType: 'poi', elementType: 'all', stylers: [{ visibility: 'off' }] },
  // Muted roads
  {
    featureType: 'road',
    elementType: 'geometry',
    stylers: [{ color: '#E5E7EB' }],
  },
  // Soft water
  {
    featureType: 'water',
    elementType: 'geometry',
    stylers: [{ color: '#DBEAFE' }],
  },
  // Light parks
  {
    featureType: 'landscape.natural',
    elementType: 'geometry',
    stylers: [{ color: '#DCFCE7' }],
  },
];

// Default center: Twin Cities area (Eden Prairie)
export const DEFAULT_CENTER = { lat: 44.8547, lng: -93.4708 };

// Default zoom level to show metro area
export const DEFAULT_ZOOM = 10;

// Map options for clean UI
export const MAP_OPTIONS: google.maps.MapOptions = {
  styles: MAP_STYLES,
  disableDefaultUI: true,
  zoomControl: true,
  mapTypeControl: false,
  streetViewControl: false,
  fullscreenControl: false,
};

// Bounds padding for auto-fit
export const BOUNDS_PADDING = {
  top: 50,
  right: 50,
  bottom: 50,
  left: 50,
};
