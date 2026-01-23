import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  ArrowLeft,
  Phone,
  Mail,
  Edit,
  Trash2,
  CheckCircle,
  XCircle,
  Award,
  DollarSign,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { LoadingPage, ErrorMessage, PageHeader } from '@/shared/components';
import { useStaffMember, useDeleteStaff, useUpdateStaffAvailability } from '../hooks';
import type { StaffRole } from '../types';
import { toast } from 'sonner';

interface StaffDetailProps {
  onEdit?: () => void;
}

const roleColors: Record<StaffRole, string> = {
  tech: 'bg-blue-100 text-blue-800',
  sales: 'bg-green-100 text-green-800',
  admin: 'bg-purple-100 text-purple-800',
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
    <div data-testid="staff-detail">
      <div className="mb-6">
        <Button variant="ghost" size="sm" asChild>
          <Link to="/staff">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Staff
          </Link>
        </Button>
      </div>

      <PageHeader
        title={staff.name}
        description={
          <div className="flex items-center gap-2">
            <Badge className={roleColors[staff.role]}>{roleLabels[staff.role]}</Badge>
            {staff.skill_level && (
              <Badge variant="outline" className="capitalize">
                {staff.skill_level}
              </Badge>
            )}
          </div>
        }
        action={
          <div className="flex gap-2">
            {onEdit && (
              <Button variant="outline" onClick={onEdit} data-testid="edit-staff-btn">
                <Edit className="mr-2 h-4 w-4" />
                Edit
              </Button>
            )}
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleteMutation.isPending}
              data-testid="delete-staff-btn"
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Delete
            </Button>
          </div>
        }
      />

      <div className="grid gap-6 md:grid-cols-2">
        {/* Contact Information */}
        <Card>
          <CardHeader>
            <CardTitle>Contact Information</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-3">
              <Phone className="h-5 w-5 text-muted-foreground" />
              <div>
                <p className="text-sm text-muted-foreground">Phone</p>
                <a href={`tel:${staff.phone}`} className="font-medium hover:underline">
                  {staff.phone}
                </a>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Mail className="h-5 w-5 text-muted-foreground" />
              <div>
                <p className="text-sm text-muted-foreground">Email</p>
                {staff.email ? (
                  <a
                    href={`mailto:${staff.email}`}
                    className="font-medium hover:underline"
                  >
                    {staff.email}
                  </a>
                ) : (
                  <span className="text-muted-foreground">Not provided</span>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Availability */}
        <Card>
          <CardHeader>
            <CardTitle>Availability</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {staff.is_available ? (
                  <CheckCircle className="h-5 w-5 text-green-600" />
                ) : (
                  <XCircle className="h-5 w-5 text-red-600" />
                )}
                <Label htmlFor="availability-toggle">
                  {staff.is_available ? 'Available' : 'Unavailable'}
                </Label>
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
              <>
                <Separator />
                <div>
                  <p className="text-sm text-muted-foreground">Notes</p>
                  <p className="text-sm">{staff.availability_notes}</p>
                </div>
              </>
            )}
            <Separator />
            <div>
              <p className="text-sm text-muted-foreground">Status</p>
              <p className="font-medium">
                {staff.is_active ? (
                  <span className="text-green-600">Active</span>
                ) : (
                  <span className="text-red-600">Inactive</span>
                )}
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Skills & Certifications */}
        <Card>
          <CardHeader>
            <CardTitle>Skills & Certifications</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-3">
              <Award className="h-5 w-5 text-muted-foreground" />
              <div>
                <p className="text-sm text-muted-foreground">Skill Level</p>
                <p className="font-medium capitalize">
                  {staff.skill_level || 'Not specified'}
                </p>
              </div>
            </div>
            <Separator />
            <div>
              <p className="text-sm text-muted-foreground mb-2">Certifications</p>
              {staff.certifications && staff.certifications.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {staff.certifications.map((cert, index) => (
                    <Badge key={index} variant="secondary">
                      {cert}
                    </Badge>
                  ))}
                </div>
              ) : (
                <p className="text-muted-foreground">No certifications</p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Compensation */}
        <Card>
          <CardHeader>
            <CardTitle>Compensation</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-3">
              <DollarSign className="h-5 w-5 text-muted-foreground" />
              <div>
                <p className="text-sm text-muted-foreground">Hourly Rate</p>
                <p className="font-medium">
                  {staff.hourly_rate
                    ? `$${Number(staff.hourly_rate).toFixed(2)}/hr`
                    : 'Not specified'}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Daily Schedule - Placeholder */}
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle>Today&apos;s Schedule</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground">No appointments scheduled for today.</p>
            <Button variant="outline" size="sm" className="mt-4" asChild>
              <Link to="/schedule">View Full Schedule</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
