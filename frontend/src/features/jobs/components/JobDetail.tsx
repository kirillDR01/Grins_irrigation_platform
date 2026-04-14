import { useState } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Calendar,
  Clock,
  DollarSign,
  User,
  Users,
  FileText,
  ChevronRight,
  MessageSquare,
  Sparkles,
  Save,
  TrendingUp,
  Pencil,
  MapPin,
  AlertTriangle,
  ShieldCheck,
  Phone,
} from 'lucide-react';
import { parseLocalDate } from '@/shared/utils/dateUtils';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { LoadingPage, ErrorMessage, PropertyTags } from '@/shared/components';
import { useJob, useUpdateJob, useJobFinancials } from '../hooks';
import { JobStatusBadge } from './JobStatusBadge';
import { OnSiteOperations } from './OnSiteOperations';
import type { Job } from '../types';
import {
  formatJobType,
  formatDuration,
  formatAmount,
  getJobCategoryConfig,
  getJobPriorityConfig,
  JOB_SOURCE_CONFIG,
} from '../types';
import { PaymentSection } from './PaymentSection';

interface JobDetailProps {
  jobId?: string;
  onEdit?: (job: Job) => void;
  onClose?: () => void;
}

export function JobDetail({ jobId: propJobId, onEdit, onClose }: JobDetailProps) {
  const { id: paramId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const id = propJobId || paramId || '';

  const { data: job, isLoading, error, refetch } = useJob(id);
  const updateJobMutation = useUpdateJob();
  const { data: financials, isLoading: financialsLoading } = useJobFinancials(id);

  // Notes editing state (Req 20)
  const [notesValue, setNotesValue] = useState<string | null>(null);
  const [notesSaving, setNotesSaving] = useState(false);

  // Initialize notes from job data
  const currentNotes = notesValue !== null ? notesValue : (job?.notes ?? '');

  const handleSaveNotes = async () => {
    if (!job) return;
    setNotesSaving(true);
    try {
      await updateJobMutation.mutateAsync({
        id: job.id,
        data: { notes: currentNotes || null },
      });
      setNotesValue(null); // Reset to track from server
    } catch (err) {
      console.error('Failed to save notes:', err);
    } finally {
      setNotesSaving(false);
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
    <div data-testid="job-detail" className="flex flex-col space-y-5">
      {/* On-Site Operations — positioned first on mobile via order (Req 12.1, 12.6) */}
      <div className="order-first md:order-none md:hidden">
        <OnSiteOperations job={job} />
        <Separator className="mt-3" />
      </div>

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
          {onEdit && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => onEdit(job)}
              data-testid="edit-job-btn"
              className="h-8"
            >
              <Pencil className="mr-1.5 h-3.5 w-3.5" />
              Edit
            </Button>
          )}
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
        {job.category === 'requires_estimate' && (
          <span
            className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-700 border border-amber-200"
            data-testid="estimate-needed-badge"
          >
            <AlertTriangle className="h-3 w-3" />
            Estimate Needed
          </span>
        )}
        {job.service_agreement_id && job.service_agreement_active && (
          <span
            className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700 border border-emerald-200"
            data-testid="prepaid-badge"
          >
            <ShieldCheck className="h-3 w-3" />
            Prepaid
          </span>
        )}
        <span
          className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${priorityConfig.bgColor} ${priorityConfig.color}`}
          data-testid="job-priority-badge"
        >
          {priorityConfig.label}
        </span>
        <PropertyTags
          propertyType={job.property_type}
          isHoa={job.property_is_hoa ?? false}
          isSubscription={job.property_is_subscription ?? false}
        />
      </div>

      {/* Property Address (Req 19.1) */}
      {job.property_address && (
        <div className="flex items-center gap-2 p-2.5 bg-slate-50 rounded-lg" data-testid="job-property-address">
          <MapPin className="h-4 w-4 text-slate-400 shrink-0" />
          <p className="text-sm text-slate-700">{job.property_address}</p>
        </div>
      )}

      {/* Service Preference Notes Hint (CRM2 Req 7.3) */}
      {job.service_preference_notes && (
        <div className="flex items-start gap-2 p-2.5 bg-amber-50 border border-amber-200 rounded-lg" data-testid="service-preference-notes">
          <Clock className="h-4 w-4 text-amber-500 shrink-0 mt-0.5" />
          <div>
            <p className="text-xs font-medium text-amber-700 uppercase tracking-wider">Service Preference</p>
            <p className="text-sm text-amber-800 mt-0.5">{job.service_preference_notes}</p>
          </div>
        </div>
      )}

      {/* Description */}
      {job.description && (
        <div className="bg-slate-50 rounded-lg p-3">
          <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">Description</p>
          <p className="text-sm text-slate-700">{job.description}</p>
        </div>
      )}

      {/* Summary */}
      {job.summary && (
        <div className="bg-slate-50 rounded-lg p-3">
          <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">Summary</p>
          <p className="text-sm text-slate-700" data-testid="job-summary">{job.summary}</p>
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
              <p className="text-sm font-medium text-slate-700 group-hover:text-blue-600">
                {job.customer_name || 'View Customer'}
              </p>
              <p className="text-xs text-slate-400">#{job.customer_id.slice(0, 8)}</p>
            </div>
          </div>
          <ChevronRight className="h-4 w-4 text-slate-400 group-hover:text-blue-600" />
        </Link>
      )}

      {/* Customer Phone — tap-to-call (Req 12.4) */}
      {job.customer_phone && (
        <a
          href={`tel:${job.customer_phone}`}
          className="flex items-center gap-2 p-2.5 bg-slate-50 rounded-lg hover:bg-slate-100 transition-colors"
          data-testid="customer-phone-link"
        >
          <Phone className="h-4 w-4 text-teal-500 shrink-0" />
          <span className="text-sm font-medium text-slate-700">{job.customer_phone}</span>
        </a>
      )}

      <Separator />

      {/* Notes Section (Req 20) */}
      <div>
        <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
          <FileText className="h-3.5 w-3.5" />
          Notes
        </p>
        <Textarea
          value={currentNotes}
          onChange={(e) => setNotesValue(e.target.value)}
          placeholder="Add notes about this job..."
          className="min-h-[100px] bg-slate-50 border-slate-200 text-base md:text-sm"
          data-testid="job-notes-textarea"
        />
        <Button
          size="sm"
          className="mt-2 bg-teal-500 hover:bg-teal-600 text-white"
          onClick={handleSaveNotes}
          disabled={notesSaving || (notesValue === null)}
          data-testid="save-notes-btn"
        >
          <Save className="mr-1.5 h-3.5 w-3.5" />
          {notesSaving ? 'Saving...' : 'Save Notes'}
        </Button>
      </div>

      <Separator />

      {/* Consolidated Payment Section (Req 17.1-17.4, 17.6) */}
      <PaymentSection job={job} />

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
      </div>

      <Separator />

      {/* Financials Section (Req 57) */}
      <div data-testid="job-financials">
        <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-3 flex items-center gap-1.5">
          <TrendingUp className="h-3.5 w-3.5" />
          Financials
        </p>
        {financialsLoading ? (
          <p className="text-sm text-slate-400">Loading financials...</p>
        ) : financials ? (
          <div className="space-y-2">
            <div className="grid grid-cols-2 gap-3">
              <div className="p-2.5 bg-slate-50 rounded-lg">
                <p className="text-xs text-slate-400">Quoted Amount</p>
                <p className="text-sm font-semibold text-slate-700" data-testid="fin-quoted">
                  {formatAmount(financials.quoted_amount)}
                </p>
              </div>
              <div className="p-2.5 bg-slate-50 rounded-lg">
                <p className="text-xs text-slate-400">Final Amount</p>
                <p className="text-sm font-semibold text-slate-700" data-testid="fin-final">
                  {formatAmount(financials.final_amount)}
                </p>
              </div>
            </div>
            <div className="p-2.5 bg-emerald-50 rounded-lg">
              <p className="text-xs text-emerald-600">Total Paid</p>
              <p className="text-sm font-semibold text-emerald-700" data-testid="fin-total-paid">
                {formatAmount(financials.total_paid)}
              </p>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="p-2.5 bg-slate-50 rounded-lg">
                <p className="text-xs text-slate-400">Material Costs</p>
                <p className="text-sm font-semibold text-slate-700" data-testid="fin-material-costs">
                  {formatAmount(financials.material_costs)}
                </p>
              </div>
              <div className="p-2.5 bg-slate-50 rounded-lg">
                <p className="text-xs text-slate-400">Labor Costs</p>
                <p className="text-sm font-semibold text-slate-700" data-testid="fin-labor-costs">
                  {formatAmount(financials.labor_costs)}
                </p>
              </div>
            </div>
            <div className="p-2.5 bg-slate-50 rounded-lg">
              <p className="text-xs text-slate-400">Total Costs</p>
              <p className="text-sm font-semibold text-slate-700" data-testid="fin-total-costs">
                {formatAmount(financials.total_costs)}
              </p>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className={`p-2.5 rounded-lg ${financials.profit >= 0 ? 'bg-emerald-50' : 'bg-red-50'}`}>
                <p className={`text-xs ${financials.profit >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>Profit</p>
                <p className={`text-sm font-semibold ${financials.profit >= 0 ? 'text-emerald-700' : 'text-red-700'}`} data-testid="fin-profit">
                  {formatAmount(financials.profit)}
                </p>
              </div>
              <div className="p-2.5 bg-slate-50 rounded-lg">
                <p className="text-xs text-slate-400">Profit Margin</p>
                <p className="text-sm font-semibold text-slate-700" data-testid="fin-profit-margin">
                  {financials.profit_margin !== null ? `${financials.profit_margin.toFixed(1)}%` : '—'}
                </p>
              </div>
            </div>
          </div>
        ) : (
          <p className="text-sm text-slate-400 italic">No financial data available.</p>
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

      {/* On-Site Operations — desktop only (mobile version is at top) (Req 12.1, 12.7) */}
      <div className="hidden md:block">
        <OnSiteOperations job={job} />
      </div>

      <Separator />
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
        {date ? parseLocalDate(date).toLocaleDateString() : '-'}
      </p>
    </>
  );
}
