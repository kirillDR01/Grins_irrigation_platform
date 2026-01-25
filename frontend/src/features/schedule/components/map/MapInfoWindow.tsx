/**
 * MapInfoWindow component - Job details popup on marker click.
 */

import { InfoWindow } from '@react-google-maps/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Clock, MapPin, User } from 'lucide-react';
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

  return (
    <InfoWindow
      position={{ lat: job.latitude, lng: job.longitude }}
      onCloseClick={onClose}
    >
      <div data-testid="map-info-window" className="min-w-[200px]">
        <div className="space-y-2">
          {/* Header with staff color indicator */}
          <div className="flex items-center gap-2">
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: color }}
            />
            <span className="font-semibold">{job.customer_name}</span>
          </div>

          {/* Service type badge */}
          <Badge variant="secondary" className="text-xs">
            {job.service_type}
          </Badge>

          {/* Address */}
          {job.address && (
            <div className="flex items-start gap-2 text-sm text-gray-600">
              <MapPin className="h-4 w-4 mt-0.5 flex-shrink-0" />
              <span>
                {job.address}
                {job.city && `, ${job.city}`}
              </span>
            </div>
          )}

          {/* Time window */}
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <Clock className="h-4 w-4" />
            <span>
              {job.start_time} - {job.end_time}
            </span>
          </div>

          {/* Staff assignment */}
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <User className="h-4 w-4" />
            <span>
              {staffName} (Stop #{job.sequence_index})
            </span>
          </div>

          {/* Travel time */}
          {job.travel_time_minutes > 0 && (
            <div className="text-xs text-gray-500">
              {job.travel_time_minutes} min travel from previous stop
            </div>
          )}
        </div>
      </div>
    </InfoWindow>
  );
}
