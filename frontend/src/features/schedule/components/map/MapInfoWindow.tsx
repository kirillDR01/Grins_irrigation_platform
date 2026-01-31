/**
 * MapInfoWindow component - Job details popup on marker click.
 */

import { InfoWindow } from '@react-google-maps/api';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Clock, MapPin, X, Navigation } from 'lucide-react';
import type { ScheduleJobAssignment } from '../../types';
import { getStaffColor } from '../../utils/staffColors';

interface MapInfoWindowProps {
  job: ScheduleJobAssignment;
  staffName: string;
  onClose: () => void;
}

export function MapInfoWindow({ job, staffName, onClose }: MapInfoWindowProps) {
  // Don't render if no coordinates
  if (job.latitude === null || job.longitude === null) {
    return null;
  }

  const color = getStaffColor(staffName);

  const handleViewDetails = () => {
    window.location.href = `/jobs/${job.job_id}`;
  };

  const handleGetDirections = () => {
    const address = `${job.address}, ${job.city || ''}`;
    window.open(`https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(address)}`, '_blank');
  };

  return (
    <InfoWindow
      position={{ lat: job.latitude, lng: job.longitude }}
      onCloseClick={onClose}
    >
      <div data-testid="map-info-window" className="bg-white rounded-xl shadow-lg border border-slate-100 p-4 min-w-[280px] relative">
        {/* Close button */}
        <button
          onClick={onClose}
          data-testid="close-info-window-btn"
          className="absolute top-2 right-2 text-slate-400 hover:text-slate-600 transition-colors"
          aria-label="Close"
        >
          <X className="h-4 w-4" />
        </button>

        <div className="space-y-3">
          {/* Header section */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: color }}
              />
              <span className="font-bold text-slate-800">{job.customer_name}</span>
            </div>
            <Badge variant="secondary" className="text-xs">
              {job.service_type}
            </Badge>
          </div>

          {/* Address section */}
          {job.address && (
            <div className="flex items-start gap-2 text-sm text-slate-600">
              <MapPin className="h-4 w-4 mt-0.5 flex-shrink-0 text-slate-400" />
              <span>
                {job.address}
                {job.city && `, ${job.city}`}
              </span>
            </div>
          )}

          {/* Time slot section */}
          <div className="flex items-center gap-2 text-sm text-slate-600">
            <Clock className="h-4 w-4 text-slate-400" />
            <span>
              {job.start_time} - {job.end_time}
            </span>
          </div>

          {/* Staff assignment section */}
          <div className="flex items-center gap-2">
            <div
              className="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold"
              style={{ backgroundColor: color }}
            >
              {staffName.charAt(0)}
            </div>
            <div className="text-sm">
              <div className="font-medium text-slate-700">{staffName}</div>
              <div className="text-xs text-slate-500">Stop #{job.sequence_index}</div>
            </div>
          </div>

          {/* Travel time */}
          {job.travel_time_minutes > 0 && (
            <div className="text-xs text-slate-500">
              {job.travel_time_minutes} min travel from previous stop
            </div>
          )}

          {/* Action buttons */}
          <div className="flex gap-2 pt-2 border-t border-slate-100">
            <button
              onClick={handleViewDetails}
              data-testid="view-details-link"
              className="text-teal-600 hover:text-teal-700 text-sm font-medium transition-colors"
            >
              View Details
            </button>
            <Button
              variant="secondary"
              size="sm"
              onClick={handleGetDirections}
              data-testid="get-directions-btn"
              className="ml-auto"
            >
              <Navigation className="h-3 w-3 mr-1" />
              Directions
            </Button>
          </div>
        </div>
      </div>
    </InfoWindow>
  );
}
