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
    <div data-testid="job-detail" className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate(-1)} aria-label="Go back">
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold" data-testid="job-title">
              {formatJobType(job.job_type)}
            </h1>
            <p className="text-muted-foreground">Job #{job.id.slice(0, 8)}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <JobStatusBadge status={job.status} />
          {onEdit && (
            <Button variant="outline" onClick={onEdit} data-testid="edit-job-btn">
              Edit Job
            </Button>
          )}
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Job Information */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Wrench className="h-5 w-5" />
              Job Information
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-muted-foreground">Category</p>
                <span
                  className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ${categoryConfig.bgColor} ${categoryConfig.color}`}
                >
                  {categoryConfig.label}
                </span>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Priority</p>
                <span
                  className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ${priorityConfig.bgColor} ${priorityConfig.color}`}
                >
                  {priorityConfig.label}
                </span>
              </div>
            </div>

            {job.description && (
              <div>
                <p className="text-sm text-muted-foreground">Description</p>
                <p className="mt-1">{job.description}</p>
              </div>
            )}

            <Separator />

            <div className="grid grid-cols-2 gap-4">
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-muted-foreground" />
                <div>
                  <p className="text-sm text-muted-foreground">Duration</p>
                  <p>{formatDuration(job.estimated_duration_minutes)}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Users className="h-4 w-4 text-muted-foreground" />
                <div>
                  <p className="text-sm text-muted-foreground">Staff Required</p>
                  <p>{job.staffing_required}</p>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-4">
              {job.weather_sensitive && (
                <div className="flex items-center gap-1 text-amber-600">
                  <Cloud className="h-4 w-4" />
                  <span className="text-sm">Weather Sensitive</span>
                </div>
              )}
            </div>

            {job.equipment_required && job.equipment_required.length > 0 && (
              <div>
                <p className="text-sm text-muted-foreground">Equipment Required</p>
                <div className="flex flex-wrap gap-1 mt-1">
                  {job.equipment_required.map((item, index) => (
                    <span
                      key={index}
                      className="inline-flex items-center rounded-full bg-gray-100 px-2 py-1 text-xs"
                    >
                      {item}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {job.materials_required && job.materials_required.length > 0 && (
              <div>
                <p className="text-sm text-muted-foreground">Materials Required</p>
                <div className="flex flex-wrap gap-1 mt-1">
                  {job.materials_required.map((item, index) => (
                    <span
                      key={index}
                      className="inline-flex items-center rounded-full bg-gray-100 px-2 py-1 text-xs"
                    >
                      {item}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Pricing & Source */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <DollarSign className="h-5 w-5" />
              Pricing & Source
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-muted-foreground">Quoted Amount</p>
                <p className="text-lg font-semibold">
                  {formatAmount(job.quoted_amount)}
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Final Amount</p>
                <p className="text-lg font-semibold">
                  {formatAmount(job.final_amount)}
                </p>
              </div>
            </div>

            <Separator />

            <div>
              <p className="text-sm text-muted-foreground">Lead Source</p>
              <p>
                {job.source
                  ? JOB_SOURCE_CONFIG[job.source]?.label || job.source
                  : 'Not specified'}
              </p>
            </div>

            {job.customer_id && (
              <div>
                <p className="text-sm text-muted-foreground">Customer</p>
                <Link
                  to={`/customers/${job.customer_id}`}
                  className="flex items-center gap-2 text-primary hover:underline"
                >
                  <User className="h-4 w-4" />
                  View Customer
                </Link>
              </div>
            )}

            {job.property_id && (
              <div>
                <p className="text-sm text-muted-foreground">Property</p>
                <div className="flex items-center gap-2 text-muted-foreground">
                  <MapPin className="h-4 w-4" />
                  Property #{job.property_id.slice(0, 8)}
                </div>
              </div>
            )}

            <Separator />

            {/* Payment Collection Status */}
            <div className="flex items-center space-x-2" data-testid="payment-collected-section">
              <Checkbox
                id="payment-collected"
                checked={job.payment_collected_on_site}
                onCheckedChange={handlePaymentCollectedChange}
                disabled={updateJobMutation.isPending}
                data-testid="payment-collected-checkbox"
              />
              <Label
                htmlFor="payment-collected"
                className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
              >
                <div className="flex items-center gap-2">
                  <CreditCard className="h-4 w-4" />
                  Payment collected on site
                </div>
              </Label>
            </div>

            {/* Linked Invoice */}
            {linkedInvoice && (
              <div data-testid="linked-invoice-section">
                <p className="text-sm text-muted-foreground">Invoice</p>
                <Link
                  to={`/invoices/${linkedInvoice.id}`}
                  className="flex items-center gap-2 text-primary hover:underline"
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

        {/* Timeline */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Calendar className="h-5 w-5" />
              Timeline
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
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

        {/* Actions */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5" />
              Actions
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {job.status === 'requested' && (
              <Button
                className="w-full"
                onClick={() => handleStatusChange('approved')}
                disabled={updateStatusMutation.isPending}
                data-testid="approve-job-btn"
              >
                Approve Job
              </Button>
            )}
            {job.status === 'approved' && (
              <Button
                className="w-full"
                variant="outline"
                onClick={() => handleStatusChange('scheduled')}
                disabled={updateStatusMutation.isPending}
                data-testid="schedule-job-btn"
              >
                Mark as Scheduled
              </Button>
            )}
            {job.status === 'scheduled' && (
              <Button
                className="w-full"
                onClick={() => handleStatusChange('in_progress')}
                disabled={updateStatusMutation.isPending}
                data-testid="start-job-btn"
              >
                Start Job
              </Button>
            )}
            {job.status === 'in_progress' && (
              <Button
                className="w-full"
                onClick={() => handleStatusChange('completed')}
                disabled={updateStatusMutation.isPending}
                data-testid="complete-job-btn"
              >
                Mark Complete
              </Button>
            )}
            {job.status === 'completed' && (
              <Button
                className="w-full"
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
                className="w-full"
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
        <div className="md:col-span-2">
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
          <div className="md:col-span-2">
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
        className={`h-2 w-2 rounded-full ${
          isActive ? 'bg-primary' : 'bg-gray-300'
        }`}
      />
      <div className="flex-1">
        <p className={`text-sm ${isActive ? 'font-medium' : 'text-muted-foreground'}`}>
          {label}
        </p>
      </div>
      <p className="text-sm text-muted-foreground">
        {date ? new Date(date).toLocaleDateString() : '-'}
      </p>
    </div>
  );
}
