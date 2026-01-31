import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  ArrowLeft,
  Phone,
  Mail,
  Edit,
  Trash2,
  Award,
  DollarSign,
  MapPin,
  Calendar,
  Clock,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { LoadingPage, ErrorMessage } from '@/shared/components';
import { useStaffMember, useDeleteStaff, useUpdateStaffAvailability } from '../hooks';
import type { StaffRole } from '../types';
import { toast } from 'sonner';

interface StaffDetailProps {
  onEdit?: () => void;
}

const roleColors: Record<StaffRole, string> = {
  tech: 'bg-blue-100 text-blue-700',
  sales: 'bg-emerald-100 text-emerald-700',
  admin: 'bg-violet-100 text-violet-700',
};

const roleLabels: Record<StaffRole, string> = {
  tech: 'Technician',
  sales: 'Sales',
  admin: 'Admin',
};

export function StaffDetail({ onEdit }: StaffDetailProps) {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: staff, isLoading, error, refetch } = useStaffMember(id);
  const deleteMutation = useDeleteStaff();
  const availabilityMutation = useUpdateStaffAvailability();

  const handleDelete = async () => {
    if (!staff) return;

    if (window.confirm(`Are you sure you want to delete ${staff.name}?`)) {
      try {
        await deleteMutation.mutateAsync(staff.id);
        toast.success('Staff member deleted successfully');
        navigate('/staff');
      } catch {
        toast.error('Failed to delete staff member');
      }
    }
  };

  const handleAvailabilityToggle = async (checked: boolean) => {
    if (!staff) return;

    try {
      await availabilityMutation.mutateAsync({
        id: staff.id,
        data: { is_available: checked },
      });
      toast.success(`${staff.name} is now ${checked ? 'available' : 'unavailable'}`);
    } catch {
      toast.error('Failed to update availability');
    }
  };

  // Get initials for avatar
  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map((n) => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  if (isLoading) {
    return <LoadingPage message="Loading staff member..." />;
  }

  if (error) {
    return <ErrorMessage error={error} onRetry={() => refetch()} />;
  }

  if (!staff) {
    return <ErrorMessage error={new Error('Staff member not found')} />;
  }

  return (
    <div data-testid="staff-detail" className="animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="mb-6">
        <Button variant="ghost" size="sm" asChild className="text-slate-600 hover:text-slate-800">
          <Link to="/staff">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Staff
          </Link>
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Main Info Card - Left Column */}
        <Card className="lg:col-span-1 bg-white rounded-2xl shadow-sm border border-slate-100">
          <CardContent className="p-6">
            {/* Large Avatar */}
            <div className="flex flex-col items-center text-center mb-6">
              <div className="w-24 h-24 rounded-full bg-teal-100 text-teal-700 flex items-center justify-center text-2xl font-bold mb-4 shadow-sm">
                {getInitials(staff.name)}
              </div>
              <h2 className="text-2xl font-bold text-slate-800">{staff.name}</h2>
              <div className="flex items-center gap-2 mt-2">
                <Badge className={roleColors[staff.role]}>{roleLabels[staff.role]}</Badge>
                {staff.skill_level && (
                  <Badge variant="outline" className="capitalize border-slate-200 text-slate-600">
                    {staff.skill_level}
                  </Badge>
                )}
              </div>
            </div>

            <Separator className="my-4 bg-slate-100" />

            {/* Contact Info */}
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-slate-100 flex items-center justify-center">
                  <Phone className="h-5 w-5 text-slate-500" />
                </div>
                <div>
                  <p className="text-xs text-slate-400 uppercase tracking-wider">Phone</p>
                  <a href={`tel:${staff.phone}`} className="text-sm font-medium text-slate-700 hover:text-teal-600">
                    {staff.phone}
                  </a>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-slate-100 flex items-center justify-center">
                  <Mail className="h-5 w-5 text-slate-500" />
                </div>
                <div>
                  <p className="text-xs text-slate-400 uppercase tracking-wider">Email</p>
                  {staff.email ? (
                    <a
                      href={`mailto:${staff.email}`}
                      className="text-sm font-medium text-slate-700 hover:text-teal-600"
                    >
                      {staff.email}
                    </a>
                  ) : (
                    <span className="text-sm text-slate-400 italic">Not provided</span>
                  )}
                </div>
              </div>
              {staff.hourly_rate && (
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-slate-100 flex items-center justify-center">
                    <DollarSign className="h-5 w-5 text-slate-500" />
                  </div>
                  <div>
                    <p className="text-xs text-slate-400 uppercase tracking-wider">Hourly Rate</p>
                    <p className="text-sm font-medium text-slate-700">
                      ${Number(staff.hourly_rate).toFixed(2)}/hr
                    </p>
                  </div>
                </div>
              )}
            </div>

            <Separator className="my-4 bg-slate-100" />

            {/* Action Buttons */}
            <div className="flex flex-col gap-2">
              {onEdit && (
                <Button variant="outline" onClick={onEdit} data-testid="edit-staff-btn" className="w-full">
                  <Edit className="mr-2 h-4 w-4" />
                  Edit Profile
                </Button>
              )}
              <Button
                variant="outline"
                onClick={handleDelete}
                disabled={deleteMutation.isPending}
                data-testid="delete-staff-btn"
                className="w-full text-red-600 hover:text-red-700 hover:bg-red-50 border-red-200"
              >
                <Trash2 className="mr-2 h-4 w-4" />
                Delete
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Right Column - 2/3 width */}
        <div className="lg:col-span-2 space-y-8">
          {/* Availability Section */}
          <Card>
            <CardHeader className="pb-4">
              <CardTitle className="text-lg font-bold text-slate-800">Availability</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between p-4 bg-slate-50 rounded-xl">
                <div className="flex items-center gap-3">
                  <div className={`w-3 h-3 rounded-full ${staff.is_available ? 'bg-emerald-500' : 'bg-slate-300'}`} data-testid="availability-indicator" />
                  <div>
                    <p className="font-medium text-slate-800">
                      {staff.is_available ? 'Available' : 'Unavailable'}
                    </p>
                    <p className="text-xs text-slate-500">
                      {staff.is_active ? 'Active staff member' : 'Inactive'}
                    </p>
                  </div>
                </div>
                <Switch
                  id="availability-toggle"
                  checked={staff.is_available}
                  onCheckedChange={handleAvailabilityToggle}
                  disabled={availabilityMutation.isPending}
                  data-testid="availability-toggle"
                />
              </div>
              {staff.availability_notes && (
                <div className="p-4 bg-amber-50 rounded-xl border border-amber-100">
                  <p className="text-xs text-amber-600 uppercase tracking-wider mb-1">Availability Notes</p>
                  <p className="text-sm text-amber-800">{staff.availability_notes}</p>
                </div>
              )}
              
              {/* Schedule Overview */}
              <div className="grid grid-cols-2 gap-4 mt-4">
                <div className="p-4 bg-slate-50 rounded-xl">
                  <div className="flex items-center gap-2 mb-2">
                    <Calendar className="h-4 w-4 text-slate-400" />
                    <p className="text-xs text-slate-400 uppercase tracking-wider">Today</p>
                  </div>
                  <p className="text-2xl font-bold text-slate-800">0</p>
                  <p className="text-xs text-slate-500">appointments</p>
                </div>
                <div className="p-4 bg-slate-50 rounded-xl">
                  <div className="flex items-center gap-2 mb-2">
                    <Clock className="h-4 w-4 text-slate-400" />
                    <p className="text-xs text-slate-400 uppercase tracking-wider">This Week</p>
                  </div>
                  <p className="text-2xl font-bold text-slate-800">0</p>
                  <p className="text-xs text-slate-500">appointments</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Assigned Jobs Section */}
          <Card>
            <CardHeader className="pb-4">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg font-bold text-slate-800">Current Assignments</CardTitle>
                <Button variant="outline" size="sm" asChild>
                  <Link to="/schedule">View Schedule</Link>
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-center py-8">
                <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center mx-auto mb-3">
                  <MapPin className="h-6 w-6 text-slate-400" />
                </div>
                <p className="text-slate-500 text-sm">No appointments scheduled for today.</p>
                <Button variant="outline" size="sm" className="mt-4" asChild>
                  <Link to="/schedule/generate">Generate Schedule</Link>
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Skills & Certifications Section */}
          <Card>
            <CardHeader className="pb-4">
              <CardTitle className="text-lg font-bold text-slate-800">Skills & Certifications</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center gap-3 p-4 bg-slate-50 rounded-xl">
                <div className="w-10 h-10 rounded-lg bg-teal-100 flex items-center justify-center">
                  <Award className="h-5 w-5 text-teal-600" />
                </div>
                <div>
                  <p className="text-xs text-slate-400 uppercase tracking-wider">Skill Level</p>
                  <p className="font-medium text-slate-800 capitalize">
                    {staff.skill_level || 'Not specified'}
                  </p>
                </div>
              </div>
              
              <div>
                <p className="text-xs text-slate-400 uppercase tracking-wider mb-3">Certifications</p>
                {staff.certifications && staff.certifications.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {staff.certifications.map((cert, index) => (
                      <Badge 
                        key={index} 
                        variant="outline"
                        className="bg-white border-slate-200 text-slate-700 px-3 py-1"
                      >
                        {cert}
                      </Badge>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-slate-400 italic">No certifications on file</p>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
