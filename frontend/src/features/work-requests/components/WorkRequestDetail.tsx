/**
 * WorkRequestDetail component.
 *
 * Displays all 19 sheet columns plus processing metadata for a single
 * Google Sheet submission. Provides "Create Lead" action when no lead
 * is linked, or a link to the existing lead when one exists.
 *
 * Validates: Requirements 6.3, 7.1, 7.2, 7.3, 7.4, 7.5, 13.1
 */

import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, ExternalLink, Loader2, UserPlus, Clock } from 'lucide-react';
import { format } from 'date-fns';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { LoadingPage, ErrorMessage, PageHeader } from '@/shared/components';

import { useWorkRequest, useCreateLeadFromSubmission } from '../hooks/useWorkRequests';
import { ProcessingStatusBadge } from './ProcessingStatusBadge';

function formatDate(value: string | null): string {
  if (!value) return '—';
  try {
    return format(new Date(value), 'MMM d, yyyy \'at\' h:mm a');
  } catch {
    return value;
  }
}

function Field({ label, value }: { label: string; value: string | null }) {
  return (
    <div>
      <p className="text-xs text-slate-400 uppercase tracking-wider">{label}</p>
      <p className="text-sm font-medium text-slate-700 mt-1">{value || '—'}</p>
    </div>
  );
}

export function WorkRequestDetail() {
  const { id } = useParams<{ id: string }>();
  const { data: request, isLoading, error, refetch } = useWorkRequest(id!);
  const createLead = useCreateLeadFromSubmission();

  const handleCreateLead = async () => {
    if (!request) return;
    try {
      await createLead.mutateAsync(request.id);
      toast.success('Lead Created', {
        description: 'A new lead has been created from this submission.',
      });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to create lead';
      toast.error('Lead Creation Failed', { description: message });
    }
  };

  if (isLoading) return <LoadingPage message="Loading work request..." />;
  if (error) return <ErrorMessage error={error} onRetry={() => refetch()} />;
  if (!request) return <ErrorMessage error={new Error('Work request not found')} />;

  return (
    <div data-testid="work-request-detail" className="animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="mb-6">
        <Button variant="ghost" size="sm" asChild className="text-slate-600 hover:text-slate-800">
          <Link to="/work-requests">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Work Requests
          </Link>
        </Button>
      </div>

      <PageHeader
        title={request.name || 'Unnamed Submission'}
        description={`Row #${request.sheet_row_number} · Imported ${formatDate(request.imported_at)}`}
        action={
          request.lead_id ? (
            <Button asChild variant="outline" data-testid="lead-link">
              <Link to={`/leads/${request.lead_id}`}>
                <ExternalLink className="mr-2 h-4 w-4" />
                View Lead
              </Link>
            </Button>
          ) : (
            <Button
              onClick={handleCreateLead}
              disabled={createLead.isPending}
              data-testid="create-lead-btn"
              className="bg-teal-500 hover:bg-teal-600 text-white shadow-sm shadow-teal-200"
            >
              {createLead.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <UserPlus className="mr-2 h-4 w-4" />
              )}
              Create Lead
            </Button>
          )
        }
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Main content - 2 columns */}
        <Card className="lg:col-span-2 bg-white rounded-2xl shadow-sm border border-slate-100">
          <CardHeader className="border-b border-slate-100">
            <CardTitle className="text-lg font-bold text-slate-800">Submission Data</CardTitle>
          </CardHeader>
          <CardContent className="p-6 space-y-6">
            {/* Contact Info */}
            <div>
              <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-4">
                Contact Information
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Field label="Name" value={request.name} />
                <Field label="Phone" value={request.phone} />
                <Field label="Email" value={request.email} />
                <Field label="City" value={request.city} />
                <Field label="Address" value={request.address} />
              </div>
            </div>

            <Separator className="bg-slate-100" />

            {/* Services Requested */}
            <div>
              <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-4">
                Services Requested
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Field label="Spring Startup" value={request.spring_startup} />
                <Field label="Fall Blowout" value={request.fall_blowout} />
                <Field label="Summer Tuneup" value={request.summer_tuneup} />
                <Field label="Repair Existing" value={request.repair_existing} />
                <Field label="New System Install" value={request.new_system_install} />
                <Field label="Addition to System" value={request.addition_to_system} />
                <Field label="Additional Services Info" value={request.additional_services_info} />
              </div>
            </div>

            <Separator className="bg-slate-100" />

            {/* Additional Details */}
            <div>
              <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-4">
                Additional Details
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Field label="Client Type" value={request.client_type} />
                <Field label="Property Type" value={request.property_type} />
                <Field label="Date Work Needed By" value={request.date_work_needed_by} />
                <Field label="Referral Source" value={request.referral_source} />
                <Field label="Landscape / Hardscape" value={request.landscape_hardscape} />
                <Field label="Additional Info" value={request.additional_info} />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Right column - metadata */}
        <div className="space-y-6">
          <Card className="bg-white rounded-2xl shadow-sm border border-slate-100">
            <CardHeader className="border-b border-slate-100">
              <CardTitle className="font-bold text-slate-800">Processing Status</CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-5">
              <div>
                <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">Status</p>
                <ProcessingStatusBadge status={request.processing_status} />
              </div>

              {request.processing_error && (
                <div>
                  <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">Error</p>
                  <p className="text-sm text-red-600">{request.processing_error}</p>
                </div>
              )}

              <Separator className="bg-slate-100" />

              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <Clock className="h-4 w-4 text-slate-400" />
                  <div>
                    <p className="text-xs text-slate-400">Sheet Timestamp</p>
                    <p className="text-sm font-medium text-slate-700">{request.timestamp || '—'}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Clock className="h-4 w-4 text-slate-400" />
                  <div>
                    <p className="text-xs text-slate-400">Imported At</p>
                    <p className="text-sm font-medium text-slate-700">{formatDate(request.imported_at)}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Clock className="h-4 w-4 text-slate-400" />
                  <div>
                    <p className="text-xs text-slate-400">Last Updated</p>
                    <p className="text-sm font-medium text-slate-700">{formatDate(request.updated_at)}</p>
                  </div>
                </div>
              </div>

              <Separator className="bg-slate-100" />

              <div>
                <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">Row Number</p>
                <p className="text-sm font-medium text-slate-700">#{request.sheet_row_number}</p>
              </div>

              {request.lead_id && (
                <>
                  <Separator className="bg-slate-100" />
                  <div>
                    <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">Linked Lead</p>
                    <Link
                      to={`/leads/${request.lead_id}`}
                      data-testid="lead-link"
                      className="flex items-center gap-2 p-3 bg-green-50 rounded-xl hover:bg-green-100 transition-colors group"
                    >
                      <div className="flex-1">
                        <p className="text-sm font-medium text-green-800">View Lead</p>
                      </div>
                      <ExternalLink className="h-4 w-4 text-green-600" />
                    </Link>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

export default WorkRequestDetail;
