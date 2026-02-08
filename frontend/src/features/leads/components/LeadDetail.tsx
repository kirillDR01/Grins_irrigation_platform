/**
 * LeadDetail page component.
 *
 * Displays full lead details with action buttons for managing the lead
 * through the pipeline: mark as contacted, convert to customer, mark as lost/spam.
 * When converted, shows links to the created customer and job.
 *
 * Validates: Requirement 10.1-10.10
 */

import { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  ArrowLeft,
  Phone,
  Mail,
  MapPin,
  Globe,
  Clock,
  FileText,
  Trash2,
  UserPlus,
  PhoneCall,
  XCircle,
  ShieldAlert,
  ExternalLink,
  Loader2,
  User,
  Briefcase,
} from 'lucide-react';
import { format } from 'date-fns';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { LoadingPage, ErrorMessage, PageHeader } from '@/shared/components';

import { useLead, useUpdateLead, useDeleteLead } from '../hooks';
import { LeadStatusBadge } from './LeadStatusBadge';
import { LeadSituationBadge } from './LeadSituationBadge';
import { ConvertLeadDialog } from './ConvertLeadDialog';
import type { LeadStatus } from '../types';
import { LEAD_STATUS_LABELS } from '../types';
import { useStaff } from '@/features/staff/hooks/useStaff';

/** Valid status transitions for the dropdown */
const VALID_TRANSITIONS: Record<LeadStatus, LeadStatus[]> = {
  new: ['contacted', 'qualified', 'lost', 'spam'],
  contacted: ['qualified', 'lost', 'spam'],
  qualified: ['converted', 'lost'],
  converted: [],
  lost: ['new'],
  spam: [],
};

export function LeadDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: lead, isLoading, error, refetch } = useLead(id!);
  const updateMutation = useUpdateLead();
  const deleteMutation = useDeleteLead();
  const { data: staffData } = useStaff({ page_size: 100, is_active: true });

  const [showConvertDialog, setShowConvertDialog] = useState(false);

  // Handle status change via dropdown
  const handleStatusChange = async (newStatus: string) => {
    if (!lead) return;
    try {
      await updateMutation.mutateAsync({
        id: lead.id,
        data: { status: newStatus as LeadStatus },
      });
      toast.success('Status Updated', {
        description: `Lead status changed to ${LEAD_STATUS_LABELS[newStatus as LeadStatus]}.`,
      });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to update status';
      toast.error('Update Failed', { description: message });
    }
  };

  // Handle staff assignment change
  const handleStaffChange = async (staffId: string) => {
    if (!lead) return;
    const assignedTo = staffId === 'unassigned' ? null : staffId;
    try {
      await updateMutation.mutateAsync({
        id: lead.id,
        data: { assigned_to: assignedTo },
      });
      toast.success('Staff Assigned', {
        description: assignedTo
          ? 'Lead assigned to staff member.'
          : 'Staff assignment removed.',
      });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to assign staff';
      toast.error('Assignment Failed', { description: message });
    }
  };

  // Quick action: Mark as Contacted
  const handleMarkContacted = async () => {
    if (!lead) return;
    try {
      await updateMutation.mutateAsync({
        id: lead.id,
        data: { status: 'contacted' },
      });
      toast.success('Lead Contacted', {
        description: 'Lead marked as contacted.',
      });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to update status';
      toast.error('Update Failed', { description: message });
    }
  };

  // Quick action: Mark as Lost
  const handleMarkLost = async () => {
    if (!lead) return;
    try {
      await updateMutation.mutateAsync({
        id: lead.id,
        data: { status: 'lost' },
      });
      toast.success('Lead Marked as Lost', {
        description: 'Lead has been marked as lost.',
      });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to update status';
      toast.error('Update Failed', { description: message });
    }
  };

  // Quick action: Mark as Spam
  const handleMarkSpam = async () => {
    if (!lead) return;
    try {
      await updateMutation.mutateAsync({
        id: lead.id,
        data: { status: 'spam' },
      });
      toast.success('Lead Marked as Spam', {
        description: 'Lead has been marked as spam.',
      });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to update status';
      toast.error('Update Failed', { description: message });
    }
  };

  // Delete lead
  const handleDelete = async () => {
    if (!lead) return;
    if (!window.confirm(`Are you sure you want to delete this lead (${lead.name})?`)) {
      return;
    }
    try {
      await deleteMutation.mutateAsync(lead.id);
      toast.success('Lead Deleted', {
        description: 'Lead has been permanently deleted.',
      });
      navigate('/leads');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to delete lead';
      toast.error('Delete Failed', { description: message });
    }
  };

  if (isLoading) {
    return <LoadingPage message="Loading lead..." />;
  }

  if (error) {
    return <ErrorMessage error={error} onRetry={() => refetch()} />;
  }

  if (!lead) {
    return <ErrorMessage error={new Error('Lead not found')} />;
  }

  const isTerminal = lead.status === 'converted' || lead.status === 'spam';
  const canMarkContacted = lead.status === 'new';
  const canConvert = lead.status === 'qualified';
  const canMarkLost = !isTerminal && lead.status !== 'lost';
  const canMarkSpam = !isTerminal;
  const availableTransitions = VALID_TRANSITIONS[lead.status] ?? [];

  // Find assigned staff name
  const assignedStaff = staffData?.items?.find(
    (s) => s.id === lead.assigned_to
  );

  return (
    <div data-testid="lead-detail" className="animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* Back Button */}
      <div className="mb-6">
        <Button variant="ghost" size="sm" asChild className="text-slate-600 hover:text-slate-800">
          <Link to="/leads">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Leads
          </Link>
        </Button>
      </div>

      {/* Page Header */}
      <PageHeader
        title={lead.name}
        description={`Lead submitted ${format(new Date(lead.created_at), 'MMM d, yyyy \'at\' h:mm a')}`}
        action={
          <div className="flex gap-2 flex-wrap">
            {canMarkContacted && (
              <Button
                variant="outline"
                onClick={handleMarkContacted}
                disabled={updateMutation.isPending}
                data-testid="mark-contacted-btn"
                className="text-yellow-700 border-yellow-200 hover:bg-yellow-50"
              >
                {updateMutation.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <PhoneCall className="mr-2 h-4 w-4" />
                )}
                Mark as Contacted
              </Button>
            )}
            {canConvert && (
              <Button
                onClick={() => setShowConvertDialog(true)}
                data-testid="convert-lead-btn"
                className="bg-teal-500 hover:bg-teal-600 text-white shadow-sm shadow-teal-200"
              >
                <UserPlus className="mr-2 h-4 w-4" />
                Convert to Customer
              </Button>
            )}
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleteMutation.isPending}
              data-testid="delete-lead-btn"
            >
              {deleteMutation.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Trash2 className="mr-2 h-4 w-4" />
              )}
              Delete
            </Button>
          </div>
        }
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Main Info Card - spans 2 columns */}
        <Card className="lg:col-span-2 bg-white rounded-2xl shadow-sm border border-slate-100">
          <CardHeader className="border-b border-slate-100">
            <CardTitle className="text-2xl font-bold text-slate-800">{lead.name}</CardTitle>
          </CardHeader>
          <CardContent className="p-6 space-y-6">
            {/* Contact Information */}
            <div>
              <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-4">
                Contact Information
              </h3>
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-slate-100 rounded-lg">
                    <Phone className="h-5 w-5 text-slate-600" />
                  </div>
                  <div>
                    <p className="text-xs text-slate-400">Phone</p>
                    <a
                      href={`tel:${lead.phone}`}
                      className="font-medium text-slate-700 hover:text-teal-600 transition-colors"
                    >
                      {lead.phone}
                    </a>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-slate-100 rounded-lg">
                    <Mail className="h-5 w-5 text-slate-600" />
                  </div>
                  <div>
                    <p className="text-xs text-slate-400">Email</p>
                    {lead.email ? (
                      <a
                        href={`mailto:${lead.email}`}
                        className="font-medium text-slate-700 hover:text-teal-600 transition-colors"
                      >
                        {lead.email}
                      </a>
                    ) : (
                      <span className="text-slate-400 italic">Not provided</span>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-slate-100 rounded-lg">
                    <MapPin className="h-5 w-5 text-slate-600" />
                  </div>
                  <div>
                    <p className="text-xs text-slate-400">Zip Code</p>
                    <p className="font-medium text-slate-700">{lead.zip_code}</p>
                  </div>
                </div>
              </div>
            </div>

            <Separator className="bg-slate-100" />

            {/* Service Details */}
            <div>
              <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-4">
                Service Details
              </h3>
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-slate-100 rounded-lg">
                    <Briefcase className="h-5 w-5 text-slate-600" />
                  </div>
                  <div>
                    <p className="text-xs text-slate-400">Situation</p>
                    <LeadSituationBadge situation={lead.situation} />
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-slate-100 rounded-lg">
                    <Globe className="h-5 w-5 text-slate-600" />
                  </div>
                  <div>
                    <p className="text-xs text-slate-400">Source Site</p>
                    <p className="font-medium text-slate-700">{lead.source_site}</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Notes */}
            {lead.notes && (
              <>
                <Separator className="bg-slate-100" />
                <div>
                  <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-4">
                    Notes
                  </h3>
                  <div className="flex items-start gap-3">
                    <div className="p-2 bg-slate-100 rounded-lg">
                      <FileText className="h-5 w-5 text-slate-600" />
                    </div>
                    <p className="text-slate-700 whitespace-pre-wrap">{lead.notes}</p>
                  </div>
                </div>
              </>
            )}

            {/* Converted Links */}
            {lead.status === 'converted' && (
              <>
                <Separator className="bg-slate-100" />
                <div>
                  <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-4">
                    Conversion Details
                  </h3>
                  <div className="space-y-3">
                    {lead.customer_id && (
                      <Link
                        to={`/customers/${lead.customer_id}`}
                        data-testid="customer-link"
                        className="flex items-center gap-3 p-3 bg-green-50 rounded-xl hover:bg-green-100 transition-colors group"
                      >
                        <div className="p-2 bg-green-100 rounded-lg group-hover:bg-green-200 transition-colors">
                          <User className="h-5 w-5 text-green-700" />
                        </div>
                        <div className="flex-1">
                          <p className="text-sm font-medium text-green-800">View Customer</p>
                          <p className="text-xs text-green-600">Navigate to the converted customer record</p>
                        </div>
                        <ExternalLink className="h-4 w-4 text-green-600" />
                      </Link>
                    )}
                    {/* Job link - shown if a job was created during conversion */}
                    <Link
                      to={`/jobs?customer_id=${lead.customer_id}`}
                      data-testid="job-link"
                      className="flex items-center gap-3 p-3 bg-blue-50 rounded-xl hover:bg-blue-100 transition-colors group"
                    >
                      <div className="p-2 bg-blue-100 rounded-lg group-hover:bg-blue-200 transition-colors">
                        <Briefcase className="h-5 w-5 text-blue-700" />
                      </div>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-blue-800">View Jobs</p>
                        <p className="text-xs text-blue-600">View jobs for this customer</p>
                      </div>
                      <ExternalLink className="h-4 w-4 text-blue-600" />
                    </Link>
                  </div>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        {/* Right Column - Status & Actions */}
        <div className="space-y-6">
          {/* Status Card */}
          <Card className="bg-white rounded-2xl shadow-sm border border-slate-100">
            <CardHeader className="border-b border-slate-100">
              <CardTitle className="font-bold text-slate-800">Status & Assignment</CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-5">
              {/* Current Status */}
              <div>
                <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">Current Status</p>
                <LeadStatusBadge status={lead.status} className="text-sm" />
              </div>

              {/* Status Dropdown */}
              {availableTransitions.length > 0 && (
                <div>
                  <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">Change Status</p>
                  <Select
                    value=""
                    onValueChange={handleStatusChange}
                    disabled={updateMutation.isPending}
                  >
                    <SelectTrigger
                      className="w-full bg-slate-50 border-slate-200 rounded-lg"
                      data-testid="lead-status-dropdown"
                    >
                      <SelectValue placeholder="Select new status..." />
                    </SelectTrigger>
                    <SelectContent>
                      {availableTransitions.map((status) => (
                        <SelectItem key={status} value={status}>
                          {LEAD_STATUS_LABELS[status]}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}

              <Separator className="bg-slate-100" />

              {/* Staff Assignment */}
              <div>
                <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">Assigned To</p>
                <Select
                  value={lead.assigned_to ?? 'unassigned'}
                  onValueChange={handleStaffChange}
                  disabled={updateMutation.isPending}
                >
                  <SelectTrigger
                    className="w-full bg-slate-50 border-slate-200 rounded-lg"
                    data-testid="lead-staff-select"
                  >
                    <SelectValue placeholder="Unassigned">
                      {assignedStaff ? assignedStaff.name : 'Unassigned'}
                    </SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="unassigned">Unassigned</SelectItem>
                    {staffData?.items?.map((staff) => (
                      <SelectItem key={staff.id} value={staff.id}>
                        {staff.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <Separator className="bg-slate-100" />

              {/* Timestamps */}
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <Clock className="h-4 w-4 text-slate-400" />
                  <div>
                    <p className="text-xs text-slate-400">Submitted</p>
                    <p className="text-sm font-medium text-slate-700">
                      {format(new Date(lead.created_at), 'MMM d, yyyy \'at\' h:mm a')}
                    </p>
                  </div>
                </div>
                {lead.contacted_at && (
                  <div className="flex items-center gap-2">
                    <PhoneCall className="h-4 w-4 text-yellow-500" />
                    <div>
                      <p className="text-xs text-slate-400">Contacted</p>
                      <p className="text-sm font-medium text-slate-700">
                        {format(new Date(lead.contacted_at), 'MMM d, yyyy \'at\' h:mm a')}
                      </p>
                    </div>
                  </div>
                )}
                {lead.converted_at && (
                  <div className="flex items-center gap-2">
                    <UserPlus className="h-4 w-4 text-green-500" />
                    <div>
                      <p className="text-xs text-slate-400">Converted</p>
                      <p className="text-sm font-medium text-slate-700">
                        {format(new Date(lead.converted_at), 'MMM d, yyyy \'at\' h:mm a')}
                      </p>
                    </div>
                  </div>
                )}
                <div className="flex items-center gap-2">
                  <Clock className="h-4 w-4 text-slate-400" />
                  <div>
                    <p className="text-xs text-slate-400">Last Updated</p>
                    <p className="text-sm font-medium text-slate-700">
                      {format(new Date(lead.updated_at), 'MMM d, yyyy \'at\' h:mm a')}
                    </p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Quick Actions Card */}
          {!isTerminal && (
            <Card className="bg-white rounded-2xl shadow-sm border border-slate-100">
              <CardHeader className="border-b border-slate-100">
                <CardTitle className="font-bold text-slate-800">Quick Actions</CardTitle>
              </CardHeader>
              <CardContent className="p-6 space-y-3">
                {canMarkContacted && (
                  <Button
                    variant="outline"
                    className="w-full justify-start text-yellow-700 border-yellow-200 hover:bg-yellow-50"
                    onClick={handleMarkContacted}
                    disabled={updateMutation.isPending}
                  >
                    <PhoneCall className="mr-2 h-4 w-4" />
                    Mark as Contacted
                  </Button>
                )}
                {canConvert && (
                  <Button
                    className="w-full justify-start bg-teal-500 hover:bg-teal-600 text-white"
                    onClick={() => setShowConvertDialog(true)}
                  >
                    <UserPlus className="mr-2 h-4 w-4" />
                    Convert to Customer
                  </Button>
                )}
                {canMarkLost && (
                  <Button
                    variant="outline"
                    className="w-full justify-start text-gray-700 border-gray-200 hover:bg-gray-50"
                    onClick={handleMarkLost}
                    disabled={updateMutation.isPending}
                    data-testid="mark-lost-btn"
                  >
                    <XCircle className="mr-2 h-4 w-4" />
                    Mark as Lost
                  </Button>
                )}
                {canMarkSpam && (
                  <Button
                    variant="outline"
                    className="w-full justify-start text-red-700 border-red-200 hover:bg-red-50"
                    onClick={handleMarkSpam}
                    disabled={updateMutation.isPending}
                    data-testid="mark-spam-btn"
                  >
                    <ShieldAlert className="mr-2 h-4 w-4" />
                    Mark as Spam
                  </Button>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* Convert Lead Dialog */}
      {lead && (
        <ConvertLeadDialog
          lead={lead}
          open={showConvertDialog}
          onOpenChange={setShowConvertDialog}
        />
      )}
    </div>
  );
}

export default LeadDetail;
