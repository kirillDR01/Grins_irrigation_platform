import { Link, useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Calendar,
  Clock,
  DollarSign,
  MapPin,
  User,
  Wrench,
  AlertTriangle,
  Cloud,
  Users,
  FileText,
  CreditCard,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { LoadingPage, ErrorMessage } from '@/shared/components';
import { useJob, useUpdateJobStatus, useUpdateJob } from '../hooks';
import { JobStatusBadge } from './JobStatusBadge';
import type { JobStatus } from '../types';
import {
  formatJobType,
  formatDuration,
  formatAmount,
  getJobCategoryConfig,
  getJobPriorityConfig,
  JOB_SOURCE_CONFIG,
} from '../types';
import { AICommunicationDrafts } from '@/features/ai/components/AICommunicationDrafts';
import { AIEstimateGenerator } from '@/features/ai/components/AIEstimateGenerator';
import { useAICommunication } from '@/features/ai/hooks/useAICommunication';
import { useAIEstimate } from '@/features/ai/hooks/useAIEstimate';
import { GenerateInvoiceButton, InvoiceStatusBadge, useInvoicesByJob } from '@/features/invoices';

interface JobDetailProps {
  jobId?: string;
  onEdit?: () => void;
}

export function JobDetail({ jobId: propJobId, onEdit }: JobDetailProps) {
  const { id: paramId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const id = propJobId || paramId || '';

  const { data: job, isLoading, error, refetch } = useJob(id);
  const updateStatusMutation = useUpdateJobStatus();
  const updateJobMutation = useUpdateJob();
  
  // Get invoices for this job
  const { data: invoices } = useInvoicesByJob(id);
  const linkedInvoice = invoices?.[0]; // Get the first invoice if exists
  
  // AI Communication hook
  const {
    draft,
    isLoading: isDraftLoading,
    error: draftError,
    sendNow,
    scheduleLater,
  } = useAICommunication();

  // AI Estimate hook - only for jobs needing estimates
  const needsEstimate = job?.status === 'requested' && !job?.quoted_amount;
  const {
    estimate,
    isLoading: isEstimateLoading,
    error: estimateError,
    generatePDF,
    scheduleSiteVisit,
    adjustQuote,
  } = useAIEstimate(needsEstimate ? id : undefined);

  const handleStatusChange = async (newStatus: JobStatus) => {
    if (!job) return;
    try {
      await updateStatusMutation.mutateAsync({
        id: job.id,
        data: { status: newStatus },
      });
    } catch (err) {
      console.error('Failed to update status:', err);
    }
  };

  const handlePaymentCollectedChange = async (checked: boolean) => {
    if (!job) return;
    try {
      await updateJobMutation.mutateAsync({
        id: job.id,
        data: { payment_collected_on_site: checked },
      });
    } catch (err) {
      console.error('Failed to update payment collected status:', err);
    }
  };

  if (isLoading) {
    return <LoadingPage message="Loading job details..." />;
  }

  if (error) {
    return <ErrorMessage error={error} onRetry={() => refetch()} />;
  }

  if (!job) {
    return <ErrorMessage error={new Error('Job not found')} />;
  }

  const categoryConfig = getJobCategoryConfig(job.category);
  const priorityConfig = getJobPriorityConfig(job.priority_level);

  return (
    <div data-testid="job-detail" className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate(-1)} aria-label="Go back" className="hover:bg-slate-100">
            <ArrowLeft className="h-4 w-4 text-slate-600" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold text-slate-800" data-testid="job-title">
              {formatJobType(job.job_type)}
            </h1>
            <p className="text-slate-500 text-sm">Job #{job.id.slice(0, 8)}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <JobStatusBadge status={job.status} data-testid="job-status-badge" />
          {onEdit && (
            <Button variant="outline" onClick={onEdit} data-testid="edit-job-btn" className="border-slate-200 hover:bg-slate-50">
              Edit Job
            </Button>
          )}
        </div>
      </div>

      <div className="grid gap-8 grid-cols-1 lg:grid-cols-3">
        {/* Main Info Card - spans 2 columns on large screens */}
        <Card className="lg:col-span-2 bg-white rounded-2xl shadow-sm border border-slate-100 hover:shadow-md transition-shadow">
          <CardHeader className="p-6 border-b border-slate-100">
            <div className="flex items-start justify-between">
              <div className="space-y-3">
                <CardTitle className="flex items-center gap-3 text-lg font-bold text-slate-800">
                  <div className="p-2 rounded-lg bg-teal-50">
                    <Wrench className="h-5 w-5 text-teal-600" />
                  </div>
                  Job Information
                </CardTitle>
                <div className="flex flex-wrap items-center gap-2">
                  <span
                    className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-medium ${categoryConfig.bgColor} ${categoryConfig.color} border ${categoryConfig.bgColor.replace('bg-', 'border-').replace('-50', '-100')}`}
                    data-testid="job-category-badge"
                  >
                    {categoryConfig.label}
                  </span>
                  <span
                    className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-medium ${priorityConfig.bgColor} ${priorityConfig.color}`}
                    data-testid="job-priority-badge"
                  >
                    {priorityConfig.label}
                  </span>
                </div>
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-6 space-y-6">
            {/* Description */}
            {job.description && (
              <div>
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Description</p>
                <p className="text-slate-700">{job.description}</p>
              </div>
            )}

            {/* Duration & Staff */}
            <div className="grid grid-cols-2 gap-6">
              <div className="flex items-center gap-3 p-3 bg-slate-50 rounded-xl">
                <div className="p-2 rounded-lg bg-white shadow-sm">
                  <Clock className="h-4 w-4 text-slate-500" />
                </div>
                <div>
                  <p className="text-xs text-slate-400 uppercase tracking-wider">Duration</p>
                  <p className="font-medium text-slate-700">{formatDuration(job.estimated_duration_minutes)}</p>
                </div>
              </div>
              <div className="flex items-center gap-3 p-3 bg-slate-50 rounded-xl">
                <div className="p-2 rounded-lg bg-white shadow-sm">
                  <Users className="h-4 w-4 text-slate-500" />
                </div>
                <div>
                  <p className="text-xs text-slate-400 uppercase tracking-wider">Staff Required</p>
                  <p className="font-medium text-slate-700">{job.staffing_required}</p>
                </div>
              </div>
            </div>

            {/* Weather Sensitive */}
            {job.weather_sensitive && (
              <div className="flex items-center gap-2 p-3 bg-amber-50 rounded-xl border border-amber-100">
                <Cloud className="h-4 w-4 text-amber-600" />
                <span className="text-sm font-medium text-amber-700">Weather Sensitive</span>
              </div>
            )}

            {/* Equipment Required */}
            {job.equipment_required && job.equipment_required.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Equipment Required</p>
                <div className="flex flex-wrap gap-2">
                  {job.equipment_required.map((item, index) => (
                    <span
                      key={index}
                      className="inline-flex items-center rounded-lg bg-slate-100 px-3 py-1.5 text-xs font-medium text-slate-600"
                    >
                      {item}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Materials Required */}
            {job.materials_required && job.materials_required.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Materials Required</p>
                <div className="flex flex-wrap gap-2">
                  {job.materials_required.map((item, index) => (
                    <span
                      key={index}
                      className="inline-flex items-center rounded-lg bg-slate-100 px-3 py-1.5 text-xs font-medium text-slate-600"
                    >
                      {item}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Sidebar - Customer, Pricing & Actions */}
        <div className="space-y-6">
          {/* Customer Info Card */}
          <Card className="bg-white rounded-2xl shadow-sm border border-slate-100 hover:shadow-md transition-shadow">
            <CardHeader className="p-6 border-b border-slate-100">
              <CardTitle className="flex items-center gap-3 text-lg font-bold text-slate-800">
                <div className="p-2 rounded-lg bg-blue-50">
                  <User className="h-5 w-5 text-blue-600" />
                </div>
                Customer
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-4">
              {job.customer_id && (
                <Link
                  to={`/customers/${job.customer_id}`}
                  className="flex items-center gap-3 p-3 bg-slate-50 rounded-xl hover:bg-slate-100 transition-colors group"
                  data-testid="customer-link"
                >
                  <div className="w-10 h-10 rounded-full bg-teal-100 flex items-center justify-center">
                    <User className="h-5 w-5 text-teal-600" />
                  </div>
                  <div className="flex-1">
                    <p className="font-medium text-slate-700 group-hover:text-teal-600 transition-colors">View Customer</p>
                    <p className="text-xs text-slate-400">#{job.customer_id.slice(0, 8)}</p>
                  </div>
                </Link>
              )}

              {job.property_id && (
                <div className="flex items-center gap-3 p-3 bg-slate-50 rounded-xl" data-testid="property-info">
                  <div className="p-2 rounded-lg bg-white shadow-sm">
                    <MapPin className="h-4 w-4 text-slate-500" />
                  </div>
                  <div>
                    <p className="text-xs text-slate-400 uppercase tracking-wider">Property</p>
                    <p className="font-medium text-slate-700">#{job.property_id.slice(0, 8)}</p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Pricing Card */}
          <Card className="bg-white rounded-2xl shadow-sm border border-slate-100 hover:shadow-md transition-shadow">
            <CardHeader className="p-6 border-b border-slate-100">
              <CardTitle className="flex items-center gap-3 text-lg font-bold text-slate-800">
                <div className="p-2 rounded-lg bg-emerald-50">
                  <DollarSign className="h-5 w-5 text-emerald-600" />
                </div>
                Pricing
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="p-3 bg-slate-50 rounded-xl">
                  <p className="text-xs text-slate-400 uppercase tracking-wider">Quoted</p>
                  <p className="text-lg font-bold text-slate-800">
                    {formatAmount(job.quoted_amount)}
                  </p>
                </div>
                <div className="p-3 bg-emerald-50 rounded-xl">
                  <p className="text-xs text-emerald-600 uppercase tracking-wider">Final</p>
                  <p className="text-lg font-bold text-emerald-700">
                    {formatAmount(job.final_amount)}
                  </p>
                </div>
              </div>

              <div className="p-3 bg-slate-50 rounded-xl">
                <p className="text-xs text-slate-400 uppercase tracking-wider">Lead Source</p>
                <p className="font-medium text-slate-700">
                  {job.source
                    ? JOB_SOURCE_CONFIG[job.source]?.label || job.source
                    : 'Not specified'}
                </p>
              </div>

              {/* Payment Collection Status */}
              <div className="flex items-center space-x-3 p-3 bg-slate-50 rounded-xl" data-testid="payment-collected-section">
                <Checkbox
                  id="payment-collected"
                  checked={job.payment_collected_on_site}
                  onCheckedChange={handlePaymentCollectedChange}
                  disabled={updateJobMutation.isPending}
                  data-testid="payment-collected-checkbox"
                  className="data-[state=checked]:bg-teal-500 data-[state=checked]:border-teal-500"
                />
                <Label
                  htmlFor="payment-collected"
                  className="text-sm font-medium text-slate-700 leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                >
                  <div className="flex items-center gap-2">
                    <CreditCard className="h-4 w-4 text-slate-500" />
                    Payment collected on site
                  </div>
                </Label>
              </div>

              {/* Linked Invoice */}
              {linkedInvoice && (
                <div data-testid="linked-invoice-section" className="p-3 bg-blue-50 rounded-xl border border-blue-100">
                  <p className="text-xs text-blue-600 uppercase tracking-wider mb-2">Invoice</p>
                  <Link
                    to={`/invoices/${linkedInvoice.id}`}
                    className="flex items-center gap-2 text-blue-700 hover:text-blue-800 font-medium"
                    data-testid="linked-invoice-link"
                  >
                    <FileText className="h-4 w-4" />
                    <span>{linkedInvoice.invoice_number}</span>
                    <InvoiceStatusBadge status={linkedInvoice.status} />
                  </Link>
                </div>
              )}

              {/* Generate Invoice Button */}
              {!linkedInvoice && ['completed', 'closed'].includes(job.status) && (
                <div data-testid="generate-invoice-section">
                  <GenerateInvoiceButton job={job} />
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Timeline Card */}
        <Card className="bg-white rounded-2xl shadow-sm border border-slate-100 hover:shadow-md transition-shadow">
          <CardHeader className="p-6 border-b border-slate-100">
            <CardTitle className="flex items-center gap-3 text-lg font-bold text-slate-800">
              <div className="p-2 rounded-lg bg-violet-50">
                <Calendar className="h-5 w-5 text-violet-600" />
              </div>
              Timeline
            </CardTitle>
          </CardHeader>
          <CardContent className="p-6">
            <div className="space-y-4">
              <TimelineItem
                label="Created"
                date={job.created_at}
                isActive={true}
              />
              <TimelineItem
                label="Requested"
                date={job.requested_at}
                isActive={!!job.requested_at}
              />
              <TimelineItem
                label="Approved"
                date={job.approved_at}
                isActive={!!job.approved_at}
              />
              <TimelineItem
                label="Scheduled"
                date={job.scheduled_at}
                isActive={!!job.scheduled_at}
              />
              <TimelineItem
                label="Started"
                date={job.started_at}
                isActive={!!job.started_at}
              />
              <TimelineItem
                label="Completed"
                date={job.completed_at}
                isActive={!!job.completed_at}
              />
              <TimelineItem
                label="Closed"
                date={job.closed_at}
                isActive={!!job.closed_at}
              />
            </div>
          </CardContent>
        </Card>

        {/* Actions Card */}
        <Card className="bg-white rounded-2xl shadow-sm border border-slate-100 hover:shadow-md transition-shadow">
          <CardHeader className="p-6 border-b border-slate-100">
            <CardTitle className="flex items-center gap-3 text-lg font-bold text-slate-800">
              <div className="p-2 rounded-lg bg-amber-50">
                <AlertTriangle className="h-5 w-5 text-amber-600" />
              </div>
              Actions
            </CardTitle>
          </CardHeader>
          <CardContent className="p-6 space-y-3">
            {job.status === 'requested' && (
              <Button
                className="w-full bg-teal-500 hover:bg-teal-600 text-white shadow-sm shadow-teal-200"
                onClick={() => handleStatusChange('approved')}
                disabled={updateStatusMutation.isPending}
                data-testid="approve-job-btn"
              >
                Approve Job
              </Button>
            )}
            {job.status === 'approved' && (
              <Button
                className="w-full bg-violet-500 hover:bg-violet-600 text-white shadow-sm shadow-violet-200"
                onClick={() => handleStatusChange('scheduled')}
                disabled={updateStatusMutation.isPending}
                data-testid="schedule-job-btn"
              >
                Mark as Scheduled
              </Button>
            )}
            {job.status === 'scheduled' && (
              <Button
                className="w-full bg-orange-500 hover:bg-orange-600 text-white shadow-sm shadow-orange-200"
                onClick={() => handleStatusChange('in_progress')}
                disabled={updateStatusMutation.isPending}
                data-testid="start-job-btn"
              >
                Start Job
              </Button>
            )}
            {job.status === 'in_progress' && (
              <Button
                className="w-full bg-emerald-500 hover:bg-emerald-600 text-white shadow-sm shadow-emerald-200"
                onClick={() => handleStatusChange('completed')}
                disabled={updateStatusMutation.isPending}
                data-testid="complete-job-btn"
              >
                Mark Complete
              </Button>
            )}
            {job.status === 'completed' && (
              <Button
                className="w-full border border-slate-200 bg-white hover:bg-slate-50 text-slate-700"
                variant="outline"
                onClick={() => handleStatusChange('closed')}
                disabled={updateStatusMutation.isPending}
                data-testid="close-job-btn"
              >
                Close Job
              </Button>
            )}
            {!['cancelled', 'closed'].includes(job.status) && (
              <Button
                className="w-full bg-red-500 hover:bg-red-600 text-white"
                variant="destructive"
                onClick={() => handleStatusChange('cancelled')}
                disabled={updateStatusMutation.isPending}
                data-testid="cancel-job-btn"
              >
                Cancel Job
              </Button>
            )}
          </CardContent>
        </Card>

        {/* AI Communication Drafts */}
        <div className="lg:col-span-3">
          <AICommunicationDrafts
            draft={draft}
            isLoading={isDraftLoading}
            error={draftError}
            onSendNow={sendNow}
            onEdit={(draftId) => console.log('Edit draft:', draftId)}
            onScheduleLater={scheduleLater}
          />
        </div>

        {/* AI Estimate Generator - Show for jobs needing estimates */}
        {needsEstimate && (
          <div className="lg:col-span-3">
            <AIEstimateGenerator
              estimate={estimate}
              isLoading={isEstimateLoading}
              error={estimateError}
              onGeneratePDF={generatePDF}
              onScheduleSiteVisit={scheduleSiteVisit}
              onAdjustQuote={adjustQuote}
            />
          </div>
        )}
      </div>
    </div>
  );
}

interface TimelineItemProps {
  label: string;
  date: string | null;
  isActive: boolean;
}

function TimelineItem({ label, date, isActive }: TimelineItemProps) {
  return (
    <div className="flex items-center gap-3">
      <div
        className={`h-3 w-3 rounded-full ${
          isActive ? 'bg-teal-500 ring-4 ring-teal-100' : 'bg-slate-200'
        }`}
      />
      <div className="flex-1">
        <p className={`text-sm ${isActive ? 'font-medium text-slate-700' : 'text-slate-400'}`}>
          {label}
        </p>
      </div>
      <p className={`text-sm ${isActive ? 'text-slate-600' : 'text-slate-300'}`}>
        {date ? new Date(date).toLocaleDateString() : '-'}
      </p>
    </div>
  );
}
