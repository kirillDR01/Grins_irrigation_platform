/**
 * TechnicianAvailability component for displaying staff availability status.
 * Shows a list of technicians with their current availability.
 */

import { Link } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useStaff } from '@/features/staff/hooks';

export function TechnicianAvailability() {
  const { data: staffData, isLoading } = useStaff({
    page: 1,
    page_size: 5,
    is_active: true,
    role: 'tech',
  });

  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map((n) => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  return (
    <Card data-testid="technician-availability">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="font-bold text-slate-800 text-lg">
          Technician Availability
        </CardTitle>
        <Button
          asChild
          variant="link"
          size="sm"
          className="text-teal-600 text-sm font-medium hover:text-teal-700 p-0"
          data-testid="manage-staff-link"
        >
          <Link to="/staff">Manage</Link>
        </Button>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-6">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="flex items-center gap-4 animate-pulse">
                <div className="w-10 h-10 rounded-full bg-slate-200" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 w-24 bg-slate-200 rounded" />
                  <div className="h-3 w-16 bg-slate-200 rounded" />
                </div>
                <div className="h-3 w-16 bg-slate-200 rounded" />
              </div>
            ))}
          </div>
        ) : (staffData?.items ?? []).length === 0 ? (
          <div className="text-center py-8 text-slate-400">
            <p>No technicians found</p>
          </div>
        ) : (
          <div className="space-y-6" data-testid="staff-list">
            {(staffData?.items ?? []).map((staff, index) => (
              <div
                key={staff.id}
                className={`flex items-center gap-4 ${
                  index < (staffData?.items ?? []).length - 1
                    ? 'border-b border-slate-50 pb-4'
                    : ''
                }`}
                data-testid={`staff-item-${staff.id}`}
              >
                <div className="w-10 h-10 rounded-full bg-slate-200 text-slate-600 font-semibold text-sm flex items-center justify-center">
                  {getInitials(staff.name)}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-800 truncate">
                    {staff.name}
                  </p>
                  <p className="text-xs text-slate-500">
                    {staff.availability_notes || 'No schedule info'}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <div
                    className={`w-2 h-2 rounded-full ${
                      staff.is_available ? 'bg-emerald-500' : 'bg-amber-500'
                    }`}
                    data-testid="availability-indicator"
                  />
                  <span className="text-xs font-medium text-slate-600">
                    {staff.is_available ? 'Available' : 'On Job'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
