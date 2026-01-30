/**
 * MobileJobSheet component - Bottom sheet for job details on mobile.
 */

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
      {/* Task 86.1: Update sheet container - bg-white rounded-t-2xl shadow-xl */}
      <div className="bg-white rounded-t-2xl shadow-xl">
        {/* Task 86.2: Update sheet handle - w-12 h-1.5 bg-slate-300 rounded-full mx-auto mt-3 */}
        <div className="w-12 h-1.5 bg-slate-300 rounded-full mx-auto mt-3" />
        
        {/* Task 86.3: Update sheet header - p-4 border-b border-slate-100 */}
        <div className="p-4 border-b border-slate-100">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: color }}
              />
              <h3 className="text-base font-bold text-slate-800">{job.customer_name}</h3>
            </div>
            <Button variant="ghost" size="icon" onClick={onClose}>
              <X className="h-4 w-4" />
            </Button>
          </div>
          <Badge variant="secondary" className="mt-2">{job.service_type}</Badge>
        </div>

        {/* Task 86.4: Update sheet content - p-4 space-y-4 */}
        <div className="p-4 space-y-4">
          {job.address && (
            <div className="flex items-start gap-2 text-sm">
              <MapPin className="h-4 w-4 mt-0.5 flex-shrink-0 text-slate-400" />
              <span className="text-slate-600">
                {job.address}
                {job.city && `, ${job.city}`}
              </span>
            </div>
          )}

          <div className="flex items-center gap-2 text-sm">
            <Clock className="h-4 w-4 text-slate-400" />
            <span className="text-slate-600">
              {job.start_time} - {job.end_time}
            </span>
          </div>

          <div className="flex items-center gap-2 text-sm">
            <User className="h-4 w-4 text-slate-400" />
            <span className="text-slate-600">
              {staffName} (Stop #{job.sequence_index})
            </span>
          </div>

          {/* Task 86.5: Update action buttons - flex gap-2 */}
          <div className="flex gap-2 pt-2">
            <Button variant="secondary" className="flex-1">
              Navigate
            </Button>
            <Button className="flex-1">
              Complete
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
