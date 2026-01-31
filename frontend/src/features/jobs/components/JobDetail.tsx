import { Link, useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Calendar,
  Clock,
  DollarSign,
  User,
  Wrench,
  Users,
  FileText,
  CreditCard,
  ChevronRight,
  MessageSquare,
  Sparkles,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
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
import { GenerateInvoiceButton, InvoiceStatusBadge, useInvoicesByJob } from '@/features/invoices';

interface JobDetailProps {
  jobId?: string;
  onEdit?: () => void;
  onClose?: () => void;
}

export function JobDetail({ jobId: propJobId, onClose }: JobDetailProps) {
  const { id: paramId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const id = propJobId || paramId || '';

  const { data: job, isLoading, error, refetch } = useJob(id);
  const updateStatusMutation = useUpdateJobStatus();
  const updateJobMutation = useUpdateJob();
  
  // Get invoices for this job
  const { data: invoices } = useInvoicesByJob(id);
  const linkedInvoice = invoices?.[0]; // Get the first invoice if exists

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

  const handleGoBack = () => {
    if (onClose) {
      onClose();
    } else {
      navigate(-1);
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
    <div data-testid="job-detail" className="space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <Button 
            variant="ghost" 
            size="icon" 
            onClick={handleGoBack} 
            aria-label="Go back" 
            className="h-8 w-8 hover:bg-slate-100 shrink-0"
          >
            <ArrowLeft className="h-4 w-4 text-slate-600" />
          </Button>
          <div className="min-w-0">
            <h1 className="text-xl font-bold text-slate-800 truncate" data-testid="job-title">
              {formatJobType(job.job_type)}
            </h1>
            <p className="text-slate-500 text-sm">Job #{job.id.slice(0, 8)}</p>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <JobStatusBadge status={job.status} data-testid="job-status-badge" />
        </div>
      </div>

      {/* Badges Row */}
      <div className="flex flex-wrap items-center gap-2">
        <span
          className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${categoryConfig.bgColor} ${categoryConfig.color}`}
          data-testid="job-category-badge"
        >
          {categoryConfig.label}
        </span>
        <span
          className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${priorityConfig.bgColor} ${priorityConfig.color}`}
          data-testid="job-priority-badge"
        >
          {priorityConfig.label}
        </span>
      </div>

      {/* Description */}
      {job.description && (
        <div className="bg-slate-50 rounded-lg p-3">
          <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">Description</p>
          <p className="text-sm text-slate-700">{job.description}</p>
        </div>
      )}

      {/* Quick Info Grid */}
      <div className="grid grid-cols-2 gap-3">
        <div className="flex items-center gap-2 p-2.5 bg-slate-50 rounded-lg">
          <Clock className="h-4 w-4 text-slate-400 shrink-0" />
          <div className="min-w-0">
            <p className="text-xs text-slate-400">Duration</p>
            <p className="text-sm font-medium text-slate-700 truncate">{formatDuration(job.estimated_duration_minutes)}</p>
          </div>
        </div>
        <div className="flex items-center gap-2 p-2.5 bg-slate-50 rounded-lg">
          <Users className="h-4 w-4 text-slate-400 shrink-0" />
          <div className="min-w-0">
            <p className="text-xs text-slate-400">Staff Required</p>
            <p className="text-sm font-medium text-slate-700">{job.staffing_required}</p>
          </div>
        </div>
      </div>

      {/* Customer Link */}
      {job.customer_id && (
        <Link
          to={`/customers/${job.customer_id}`}
          className="flex items-center justify-between p-3 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors group"
          data-testid="customer-link"
        >
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center">
              <User className="h-4 w-4 text-blue-600" />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-700 group-hover:text-blue-600">View Customer</p>
              <p className="text-xs text-slate-400">#{job.customer_id.slice(0, 8)}</p>
            </div>
          </div>
          <ChevronRight className="h-4 w-4 text-slate-400 group-hover:text-blue-600" />
        </Link>
      )}

      <Separator />

      {/* Pricing Section */}
      <div>
        <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
          <DollarSign className="h-3.5 w-3.5" />
          Pricing
        </p>
        <div className="grid grid-cols-2 gap-3">
          <div className="p-2.5 bg-slate-50 rounded-lg">
            <p className="text-xs text-slate-400">Quoted</p>
            <p className="text-sm font-semibold text-slate-700">{formatAmount(job.quoted_amount)}</p>
          </div>
          <div className="p-2.5 bg-emerald-50 rounded-lg">
            <p className="text-xs text-emerald-600">Final</p>
            <p className="text-sm font-semibold text-emerald-700">{formatAmount(job.final_amount)}</p>
          </div>
        </div>
        
        <div className="mt-3 p-2.5 bg-slate-50 rounded-lg">
          <p className="text-xs text-slate-400">Lead Source</p>
          <p className="text-sm font-medium text-slate-700">
            {job.source ? JOB_SOURCE_CONFIG[job.source]?.label || job.source : 'Not specified'}
          </p>
        </div>

        {/* Payment Collection */}
        <div className="mt-3 flex items-center space-x-2" data-testid="payment-collected-section">
          <Checkbox
            id="payment-collected"
            checked={job.payment_collected_on_site}
            onCheckedChange={handlePaymentCollectedChange}
            disabled={updateJobMutation.isPending}
            data-testid="payment-collected-checkbox"
            className="data-[state=checked]:bg-teal-500 data-[state=checked]:border-teal-500"
          />
          <Label htmlFor="payment-collected" className="text-sm text-slate-600 flex items-center gap-1.5">
            <CreditCard className="h-3.5 w-3.5" />
            Payment collected on site
          </Label>
        </div>

        {/* Linked Invoice */}
        {linkedInvoice && (
          <Link
            to={`/invoices/${linkedInvoice.id}`}
            className="mt-3 flex items-center justify-between p-2.5 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors"
            data-testid="linked-invoice-link"
          >
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-blue-600" />
              <span className="text-sm font-medium text-blue-700">{linkedInvoice.invoice_number}</span>
            </div>
            <InvoiceStatusBadge status={linkedInvoice.status} />
          </Link>
        )}

        {/* Generate Invoice Button */}
        {!linkedInvoice && ['completed', 'closed'].includes(job.status) && (
          <div className="mt-3" data-testid="generate-invoice-section">
            <GenerateInvoiceButton job={job} />
          </div>
        )}
      </div>

      <Separator />

      {/* Timeline Section */}
      <div>
        <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-3 flex items-center gap-1.5">
          <Calendar className="h-3.5 w-3.5" />
          Timeline
        </p>
        <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
          <TimelineRow label="Created" date={job.created_at} isActive={true} />
          <TimelineRow label="Requested" date={job.requested_at} isActive={!!job.requested_at} />
          <TimelineRow label="Approved" date={job.approved_at} isActive={!!job.approved_at} />
          <TimelineRow label="Scheduled" date={job.scheduled_at} isActive={!!job.scheduled_at} />
          <TimelineRow label="Started" date={job.started_at} isActive={!!job.started_at} />
          <TimelineRow label="Completed" date={job.completed_at} isActive={!!job.completed_at} />
          <TimelineRow label="Closed" date={job.closed_at} isActive={!!job.closed_at} />
        </div>
      </div>

      <Separator />

      {/* Actions Section */}
      <div>
        <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-3 flex items-center gap-1.5">
          <Wrench className="h-3.5 w-3.5" />
          Actions
        </p>
        <div className="flex flex-wrap gap-2">
          {job.status === 'requested' && (
            <Button
              size="sm"
              className="bg-teal-500 hover:bg-teal-600 text-white"
              onClick={() => handleStatusChange('approved')}
              disabled={updateStatusMutation.isPending}
              data-testid="approve-job-btn"
            >
              Approve Job
            </Button>
          )}
          {job.status === 'approved' && (
            <Button
              size="sm"
              className="bg-violet-500 hover:bg-violet-600 text-white"
              onClick={() => handleStatusChange('scheduled')}
              disabled={updateStatusMutation.isPending}
              data-testid="schedule-job-btn"
            >
              Mark as Scheduled
            </Button>
          )}
          {job.status === 'scheduled' && (
            <Button
              size="sm"
              className="bg-orange-500 hover:bg-orange-600 text-white"
              onClick={() => handleStatusChange('in_progress')}
              disabled={updateStatusMutation.isPending}
              data-testid="start-job-btn"
            >
              Start Job
            </Button>
          )}
          {job.status === 'in_progress' && (
            <Button
              size="sm"
              className="bg-emerald-500 hover:bg-emerald-600 text-white"
              onClick={() => handleStatusChange('completed')}
              disabled={updateStatusMutation.isPending}
              data-testid="complete-job-btn"
            >
              Mark Complete
            </Button>
          )}
          {job.status === 'completed' && (
            <Button
              size="sm"
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
              size="sm"
              variant="destructive"
              onClick={() => handleStatusChange('cancelled')}
              disabled={updateStatusMutation.isPending}
              data-testid="cancel-job-btn"
            >
              Cancel Job
            </Button>
          )}
        </div>
      </div>

      {/* AI Communication Section - Simplified */}
      <Card className="bg-slate-50 border-slate-100">
        <CardHeader className="p-4 pb-2">
          <CardTitle className="flex items-center gap-2 text-sm font-medium text-slate-700">
            <MessageSquare className="h-4 w-4 text-teal-500" />
            AI Communication Drafts
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4 pt-0">
          <Button
            size="sm"
            variant="outline"
            className="w-full"
            data-testid="generate-draft-btn"
          >
            <Sparkles className="mr-2 h-3.5 w-3.5" />
            Generate New
          </Button>
          <p className="text-xs text-slate-400 mt-2 text-center">
            No draft available. Generate a communication draft to get started.
          </p>
        </CardContent>
      </Card>

      {/* Close Button at Bottom */}
      {onClose && (
        <div className="pt-4 border-t border-slate-100">
          <Button 
            variant="outline" 
            onClick={onClose} 
            className="w-full"
            data-testid="close-detail-btn"
          >
            Close
          </Button>
        </div>
      )}
    </div>
  );
}

interface TimelineRowProps {
  label: string;
  date: string | null;
  isActive: boolean;
}

function TimelineRow({ label, date, isActive }: TimelineRowProps) {
  return (
    <>
      <p className={`${isActive ? 'text-slate-700' : 'text-slate-400'}`}>{label}</p>
      <p className={`text-right ${isActive ? 'text-slate-600' : 'text-slate-300'}`}>
        {date ? new Date(date).toLocaleDateString() : '-'}
      </p>
    </>
  );
}
