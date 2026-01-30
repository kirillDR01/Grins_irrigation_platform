/**
 * MapControls component - Map control buttons.
 */

import { Plus, Minus, Crosshair, Maximize } from 'lucide-react';

interface MapControlsProps {
  onZoomIn?: () => void;
  onZoomOut?: () => void;
  onRecenter?: () => void;
  onFullscreen?: () => void;
}

export function MapControls({ onZoomIn, onZoomOut, onRecenter, onFullscreen }: MapControlsProps) {
  return (
    <div className="flex flex-col gap-2" data-testid="map-controls">
      {onZoomIn && (
        <button
          onClick={onZoomIn}
          className="bg-white hover:bg-slate-50 p-2 rounded-lg shadow-md border border-slate-100 transition-colors"
          data-testid="zoom-in-btn"
          aria-label="Zoom in"
        >
          <Plus className="h-5 w-5 text-slate-600" />
        </button>
      )}
      {onZoomOut && (
        <button
          onClick={onZoomOut}
          className="bg-white hover:bg-slate-50 p-2 rounded-lg shadow-md border border-slate-100 transition-colors"
          data-testid="zoom-out-btn"
          aria-label="Zoom out"
        >
          <Minus className="h-5 w-5 text-slate-600" />
        </button>
      )}
      {onRecenter && (
        <button
          onClick={onRecenter}
          className="bg-white hover:bg-slate-50 p-2 rounded-lg shadow-md border border-slate-100 transition-colors"
          data-testid="recenter-btn"
          aria-label="Recenter map"
        >
          <Crosshair className="h-5 w-5 text-slate-600" />
        </button>
      )}
      {onFullscreen && (
        <button
          onClick={onFullscreen}
          className="bg-white hover:bg-slate-50 p-2 rounded-lg shadow-md border border-slate-100 transition-colors"
          data-testid="fullscreen-btn"
          aria-label="Toggle fullscreen"
        >
          <Maximize className="h-5 w-5 text-slate-600" />
        </button>
      )}
    </div>
  );
}
