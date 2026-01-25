/**
 * MobileJobSheet component - Bottom sheet for job details on mobile.
 */

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Clock, MapPin, User, X } from 'lucide-react';
import type { ScheduleJobAssignment } from '../../types';
import { getStaffColor } from '../../utils/staffColors';

interface MobileJobSheetProps {
  job: ScheduleJobAssignment;
  staffName: string;
  onClose: () => void;
}

export function MobileJobSheet({ job, staffName, onClose }: MobileJobSheetProps) {
  const color = getStaffColor(staffName);

  return (
    <div
      data-testid="mobile-job-sheet"
      className="fixed bottom-0 left-0 right-0 z-50 md:hidden"
    >
      <Card className="rounded-t-xl rounded-b-none shadow-lg">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: color }}
              />
              <CardTitle className="text-base">{job.customer_name}</CardTitle>
            </div>
            <Button variant="ghost" size="icon" onClick={onClose}>
              <X className="h-4 w-4" />
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-3 pb-6">
          <Badge variant="secondary">{job.service_type}</Badge>

          {job.address && (
            <div className="flex items-start gap-2 text-sm">
              <MapPin className="h-4 w-4 mt-0.5 flex-shrink-0 text-muted-foreground" />
              <span>
                {job.address}
                {job.city && `, ${job.city}`}
              </span>
            </div>
          )}

          <div className="flex items-center gap-2 text-sm">
            <Clock className="h-4 w-4 text-muted-foreground" />
            <span>
              {job.start_time} - {job.end_time}
            </span>
          </div>

          <div className="flex items-center gap-2 text-sm">
            <User className="h-4 w-4 text-muted-foreground" />
            <span>
              {staffName} (Stop #{job.sequence_index})
            </span>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
