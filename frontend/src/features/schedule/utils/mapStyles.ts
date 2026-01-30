/**
 * Google Maps styling configuration.
 * Clean, minimal styling focused on route visualization with teal accent colors.
 */

// Map styles to reduce visual clutter
export const MAP_STYLES: google.maps.MapTypeStyle[] = [
  // Hide POIs (points of interest)
  { featureType: 'poi', elementType: 'all', stylers: [{ visibility: 'off' }] },
  // Muted roads
  {
    featureType: 'road',
    elementType: 'geometry',
    stylers: [{ color: '#E5E7EB' }], // slate-200
  },
  // Soft water
  {
    featureType: 'water',
    elementType: 'geometry',
    stylers: [{ color: '#CCFBF1' }], // teal-100
  },
  // Light parks
  {
    featureType: 'landscape.natural',
    elementType: 'geometry',
    stylers: [{ color: '#DCFCE7' }], // green-100
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

// Marker colors (teal-based design system)
export const MARKER_COLORS = {
  primary: '#14B8A6', // teal-500
  secondary: '#94A3B8', // slate-400
  selected: '#0D9488', // teal-600
  hover: '#2DD4BF', // teal-400
};

// Route line styling
export const ROUTE_LINE_OPTIONS = {
  strokeColor: '#2DD4BF', // teal-400
  strokeOpacity: 0.6,
  strokeWeight: 4,
};

// Info window styling
export const INFO_WINDOW_STYLE = {
  background: '#FFFFFF',
  borderRadius: '1rem', // rounded-xl
  border: '1px solid #F1F5F9', // slate-100
  boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)', // shadow-lg
  padding: '1rem',
};

// Map control button styling
export const CONTROL_BUTTON_STYLE = {
  background: '#FFFFFF',
  borderRadius: '0.5rem', // rounded-lg
  boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)', // shadow-md
  padding: '0.5rem',
  border: '1px solid #F1F5F9', // slate-100
  hoverBackground: '#F8FAFC', // slate-50
};
