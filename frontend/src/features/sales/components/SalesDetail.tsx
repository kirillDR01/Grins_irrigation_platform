import { useMemo, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import axios from 'axios';
import { ArrowLeft, ChevronDown, FileText, Mail, Phone, Edit, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { LoadingPage, ErrorMessage, InternalNotesCard } from '@/shared/components';
import { TagPicker } from '@/features/customers/components/TagPicker';
import { getErrorMessage } from '@/core/api';
import { useUpdateCustomer, useCustomer as useCustomerDetail } from '@/features/customers/hooks';
import { useQueryClient } from '@tanstack/react-query';
import { invalidateAfterCustomerInternalNotesSave } from '@/shared/utils/invalidationHelpers';
import { useStaff } from '@/features/staff/hooks/useStaff';
import {
  useSalesEntry,
  useSalesDocuments,
  useTriggerEmailSigning,
  useDocumentPresign,
  useOverrideSalesStatus,
  useAdvanceSalesEntry,
  useConvertToJob,
  useForceConvertToJob,
  useMarkSalesLost,
  useSalesCalendarEvents,
  useUploadSalesDocument,
  usePauseNudges,
  useUnpauseNudges,
  useSendTextConfirmation,
  useResendEstimateForSalesEntry,
} from '../hooks/useSalesPipeline';
import { ScheduleVisitModal } from './ScheduleVisitModal';
import { MarkDeclinedDialog } from './MarkDeclinedDialog';
import { ForceConvertDialog } from './ForceConvertDialog';
import { AddCustomerEmailDialog } from './AddCustomerEmailDialog';
import { SalesEstimateSheetWrapper } from './SalesEstimateSheetWrapper';
import { SALES_STATUS_CONFIG, TERMINAL_STATUSES, ALL_STATUSES, statusToStageKey } from '../types/pipeline';
import type { SalesEntryStatus, NowActionId, ActivityEvent, StageKey } from '../types/pipeline';
import { DocumentsSection } from './DocumentsSection';
import { SignWellEmbeddedSigner } from './SignWellEmbeddedSigner';
import { StageStepper } from './StageStepper';
import { NowCard } from './NowCard';
import { ActivityStrip } from './ActivityStrip';
import { nowContent } from '../lib/nowContent';
import { formatDistanceToNow } from 'date-fns';
import type { SalesDocument } from '../api/salesPipelineApi';

interface SalesDetailProps {
  entryId: string;
}

const WEEK_OF_KEY = (id: string) => `sales-weekof-${id}`;

export function SalesDetail({ entryId }: SalesDetailProps) {
  const navigate = useNavigate();
  const { data: entry, isLoading, error, refetch } = useSalesEntry(entryId);
  const emailSign = useTriggerEmailSigning();
  const updateCustomer = useUpdateCustomer();
  const queryClient = useQueryClient();
  const overrideStatus = useOverrideSalesStatus();
  const advance = useAdvanceSalesEntry();
  const convertToJob = useConvertToJob();
  const forceConvert = useForceConvertToJob();
  const markLost = useMarkSalesLost();
  const uploadDoc = useUploadSalesDocument();
  const pauseNudges = usePauseNudges();
  const unpauseNudges = useUnpauseNudges();
  const sendTextConfirm = useSendTextConfirmation();
  const resendEstimate = useResendEstimateForSalesEntry();
  const { data: staffData } = useStaff({ is_active: true });

  // Fetch customer for internal_notes display
  const { data: salesCustomer } = useCustomerDetail(entry?.customer_id ?? '');

  // Existing calendar events for this entry — used to determine reschedule path.
  // Backend orders ASC by scheduled_date (api/v1/sales_pipeline.py), so the
  // last item is the most recent. SalesCalendarEvent has no `cancelled_at`
  // column today; if a customer has rescheduled twice, we treat the latest
  // row as the active one.
  const { data: entryEvents } = useSalesCalendarEvents({
    sales_entry_id: entryId,
  });
  const currentEvent =
    entryEvents && entryEvents.length > 0
      ? entryEvents[entryEvents.length - 1] ?? null
      : null;

  // Inline edit state
  const [editingCustomerInfo, setEditingCustomerInfo] = useState(false);
  const [customerInfoForm, setCustomerInfoForm] = useState({
    customer_name: '',
    customer_phone: '',
  });

  // Week-of picker state — persisted to localStorage keyed by entry ID
  // TODO(backend): replace with a proper `week_of` column on the sales entry
  const [weekOfValue, setWeekOfValue] = useState<string | null>(() => {
    try {
      return localStorage.getItem(WEEK_OF_KEY(entryId));
    } catch {
      return null;
    }
  });

  const handleWeekOfChange = useCallback((w: string) => {
    setWeekOfValue(w);
    try {
      localStorage.setItem(WEEK_OF_KEY(entryId), w);
    } catch {
      // ignore
    }
  }, [entryId]);

  // ScheduleVisitModal open state
  const [scheduleModalOpen, setScheduleModalOpen] = useState(false);

  // MarkDeclinedDialog open state
  const [markDeclinedOpen, setMarkDeclinedOpen] = useState(false);

  // NEW-C: ForceConvertDialog opens after the convert endpoint returns 422
  // with "signature" in the detail. Mirrors StatusActionButton handler.
  const [forceConvertOpen, setForceConvertOpen] = useState(false);

  // NEW-D: AddCustomerEmailDialog drives the inline email-add flow used by
  // the now-action-add-email button when the customer row has no email.
  const [addEmailOpen, setAddEmailOpen] = useState(false);

  // Structured-estimate sheet (replaces the legacy PDF dropzone on the
  // ``send_estimate`` stage). Submitting the sheet calls the
  // /send-estimate orchestrator and advances the entry.
  const [estimateSheetOpen, setEstimateSheetOpen] = useState(false);

  // Fetch documents to determine signing button state
  const { data: documents } = useSalesDocuments(entry?.customer_id ?? '');
  // Contracts only — estimate approval no longer flows through SignWell;
  // it goes through the customer portal at ``/portal/estimates/<token>``.
  const signingDocs = useMemo<SalesDocument[]>(
    () => (documents ?? []).filter((d) => d.document_type === 'contract'),
    [documents],
  );
  const hasSigningDoc = signingDocs.length > 0;
  const hasMultipleSigningDocs = signingDocs.length > 1;

  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const selectedDoc = signingDocs.find((d) => d.id === selectedDocId) ?? signingDocs[0] ?? null;

  const presign = useDocumentPresign(entry?.customer_id, selectedDoc?.id);
  const presignReady = !!presign.data?.download_url;
  const presignFailed = presign.isError;
  const signingDisabledReason = !hasSigningDoc
    ? 'Upload a contract document first'
    : presignFailed
      ? 'Contract file is missing or expired — re-upload required.'
      : presign.isLoading
        ? 'Resolving document…'
        : undefined;
  const signingReady = hasSigningDoc && presignReady;

  const handleSaveSalesEntryNotes = useCallback(
    async (next: string | null) => {
      if (!entry?.customer_id) return;
      await updateCustomer.mutateAsync({
        id: entry.customer_id,
        data: { internal_notes: next },
      });
      invalidateAfterCustomerInternalNotesSave(queryClient, entry.customer_id);
    },
    [entry, updateCustomer, queryClient],
  );

  // ── NowCard action handler ──────────────────────────────────────────────────
  const handleNowAction = useCallback(
    (id: NowActionId) => {
      switch (id) {
        case 'schedule_visit':
          setScheduleModalOpen(true);
          break;

        case 'build_and_send_estimate':
          setEstimateSheetOpen(true);
          break;

        case 'convert_to_job':
          // NEW-C: parse the 422 axios response and surface the
          // ForceConvertDialog when the backend reports a missing
          // signature. Mirrors StatusActionButton.handleAdvance.
          convertToJob.mutate(entryId, {
            onSuccess: () => { toast.success('Converted to job'); refetch(); },
            onError: (err) => {
              const detail = axios.isAxiosError(err)
                ? (err.response?.data?.detail ?? 'Failed to convert')
                : 'Failed to convert';
              if (
                typeof detail === 'string'
                && (detail.includes('signature') || detail.includes('Signature'))
              ) {
                setForceConvertOpen(true);
              } else {
                toast.error('Error', {
                  description: typeof detail === 'string' ? detail : 'Failed to convert',
                });
              }
            },
          });
          break;

        case 'view_job':
          // TODO(backend): expose entry.job_id and navigate to /jobs/{job_id}
          navigate('/jobs');
          break;

        case 'view_customer':
          navigate(`/customers/${entry?.customer_id}`);
          break;

        case 'jump_to_schedule':
          navigate('/schedule');
          break;

        case 'mark_declined':
          setMarkDeclinedOpen(true);
          break;

        case 'skip_advance':
          advance.mutate(entryId, {
            onSuccess: () => { toast.success('Status advanced'); refetch(); },
            onError: () => toast.error('Failed to advance'),
          });
          break;

        case 'mark_approved_manual':
          overrideStatus.mutateAsync({
            id: entryId,
            body: { status: 'send_contract' },
          })
            .then(() => { toast.success('Marked as approved'); refetch(); })
            .catch(() => toast.error('Failed to update status'));
          break;

        case 'text_confirmation':
          sendTextConfirm.mutate(entryId, {
            onSuccess: () => toast.success('Confirmation text sent'),
            onError: (err) =>
              toast.error('Failed to send confirmation', {
                description: getErrorMessage(err),
              }),
          });
          break;

        case 'resend_estimate':
          resendEstimate
            .mutateAsync(entryId)
            .then(() => {
              toast.success('Portal link resent');
              refetch();
            })
            .catch((err) =>
              toast.error('Failed to resend estimate', {
                description: getErrorMessage(err),
              }),
            );
          break;

        case 'pause_nudges': {
          // Toggle: if currently paused, unpause; otherwise pause.
          const currentlyPaused = !!entry?.nudges_paused_until;
          const mutation = currentlyPaused ? unpauseNudges : pauseNudges;
          const successLabel = currentlyPaused ? 'Nudges resumed' : 'Nudges paused';
          mutation.mutate(entryId, {
            onSuccess: () => { toast.success(successLabel); refetch(); },
            onError: (err) =>
              toast.error('Failed to update nudge schedule', {
                description: getErrorMessage(err),
              }),
          });
          break;
        }

        case 'add_customer_email':
          setAddEmailOpen(true);
          break;

        default:
          break;
      }
    },
    [
      entryId,
      entry,
      navigate,
      advance,
      convertToJob,
      overrideStatus,
      refetch,
      pauseNudges,
      unpauseNudges,
      sendTextConfirm,
      resendEstimate,
    ],
  );

  // ── File drop handler ───────────────────────────────────────────────────────
  const handleFileDrop = useCallback(
    async (file: File, kind: 'estimate' | 'agreement') => {
      if (!entry?.customer_id) return;
      try {
        await uploadDoc.mutateAsync({
          customerId: entry.customer_id,
          file,
          documentType: kind === 'agreement' ? 'contract' : 'estimate',
        });
        toast.success(
          `${kind === 'agreement' ? 'Agreement' : 'Estimate'} uploaded`,
        );
        refetch();
      } catch (err) {
        toast.error('Upload failed', { description: getErrorMessage(err) });
      }
    },
    [entry, uploadDoc, refetch],
  );

  // ── Derive stage and NowCard content (safe before entry guard) ─────────────
  const stageKey = entry ? statusToStageKey(entry.status) : null;
  const hasEstimateDoc = signingDocs.some((d) => d.document_type === 'estimate');
  // Bug #9: scope contract docs to this entry; legacy pre-H-7 docs
  // (sales_entry_id == null) fall through to keep the old unlock
  // behaviour for grandfathered rows. Without this filter, a customer
  // with two open entries would see the second entry incorrectly
  // marked as having a signed agreement based on the first entry's
  // contract upload.
  const hasSignedAgreement = signingDocs.some(
    (d) =>
      d.document_type === 'contract'
      && (d.sales_entry_id === entry?.id || d.sales_entry_id == null),
  );

  // ── Build ActivityEvent[] from entry fields ─────────────────────────────────
  const activityEvents = useMemo<ActivityEvent[]>(() => {
    if (!entry) return [];
    const events: ActivityEvent[] = [];
    if (entry.lead_id) {
      events.push({ kind: 'moved_from_leads', label: 'From leads', tone: 'neutral' });
    }
    if (entry.status === 'estimate_scheduled' || (stageKey && stageKey !== 'schedule_estimate')) {
      events.push({ kind: 'visit_scheduled', label: 'Visit scheduled', tone: 'done' });
    }
    if (stageKey && ['pending_approval', 'send_contract', 'closed_won'].includes(stageKey)) {
      events.push({ kind: 'estimate_sent', label: 'Estimate sent', tone: 'done' });
    }
    if (stageKey === 'send_contract' || stageKey === 'closed_won') {
      events.push({ kind: 'approved', label: 'Approved', tone: 'done' });
    }
    if (stageKey === 'closed_won') {
      events.push({ kind: 'converted', label: 'Converted to job', tone: 'done' });
    }
    if (entry.status === 'closed_lost') {
      events.push({ kind: 'declined', label: 'Declined', tone: 'neutral' });
    }
    return events;
  }, [entry, stageKey]);

  if (isLoading) return <LoadingPage message="Loading sales entry…" />;

  if (error || !entry)
    return <ErrorMessage error={error ?? new Error('Not found')} onRetry={() => refetch()} />;

  const statusConfig = SALES_STATUS_CONFIG[entry.status];
  const isTerminal = TERMINAL_STATUSES.includes(entry.status);
  const hasEmail = !!(entry.customer_email ?? salesCustomer?.email);

  const startEditCustomerInfo = () => {
    setCustomerInfoForm({
      customer_name: entry.customer_name ?? '',
      customer_phone: entry.customer_phone ?? '',
    });
    setEditingCustomerInfo(true);
  };

  const saveCustomerInfo = async () => {
    if (!entry.customer_id) return;
    try {
      const parts = customerInfoForm.customer_name.trim().split(/\s+/);
      const firstName = parts[0] || '';
      const lastName = parts.slice(1).join(' ') || '';
      await updateCustomer.mutateAsync({
        id: entry.customer_id,
        data: {
          first_name: firstName,
          last_name: lastName,
          phone: customerInfoForm.customer_phone.trim(),
        },
      });
      toast.success('Customer info updated');
      setEditingCustomerInfo(false);
      refetch();
    } catch (err: unknown) {
      toast.error('Update failed', { description: getErrorMessage(err) });
    }
  };

  const handleStatusOverride = async (newStatus: string) => {
    try {
      await overrideStatus.mutateAsync({
        id: entryId,
        body: { status: newStatus as SalesEntryStatus },
      });
      toast.success('Pipeline stage updated');
      refetch();
    } catch (err: unknown) {
      toast.error('Update failed', { description: getErrorMessage(err) });
    }
  };

  // Bug #5 part 1: dropdown-driven stage override. The StageStepper now
  // renders a <DropdownMenu> with the 5 canonical stages; selecting one
  // calls useOverrideSalesStatus and toasts "Moved to <Label>".
  const STAGE_LABELS: Record<StageKey, string> = {
    schedule_estimate: 'Schedule',
    send_estimate: 'Estimate',
    pending_approval: 'Approval',
    send_contract: 'Contract',
    closed_won: 'Closed',
  };
  const handleStageOverride = async (stage: StageKey) => {
    try {
      await overrideStatus.mutateAsync({
        id: entryId,
        body: { status: stage },
      });
      toast.success(`Moved to ${STAGE_LABELS[stage]}`);
      refetch();
    } catch (err) {
      toast.error('Failed to change stage', {
        description: getErrorMessage(err),
      });
    }
  };

  const handleEmailSign = async () => {
    try {
      await emailSign.mutateAsync(entryId);
      toast.success('Signing request sent via email');
      refetch();
    } catch (err) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? 'Failed to send signing request';
      toast.error(msg);
    }
  };

  // ── Derive NowCard content ──────────────────────────────────────────────────
  const firstName = (entry.customer_name ?? 'Customer').split(' ')[0];

  const nowCardContent = stageKey
    ? nowContent({
        stage: stageKey,
        hasEstimateDoc,
        hasSignedAgreement,
        hasCustomerEmail: hasEmail,
        firstName,
        weekOf: weekOfValue ?? undefined,
        nudgesPaused: !!entry.nudges_paused_until,
      })
    : null;

  const isClosedLost = entry.status === 'closed_lost';
  const isClosedWon = entry.status === 'closed_won';

  return (
    <div data-testid="sales-detail-page" className="space-y-6">
      {/* Back button */}
      <Button
        variant="ghost"
        size="sm"
        onClick={() => navigate('/sales')}
        data-testid="back-to-pipeline-btn"
      >
        <ArrowLeft className="mr-1 h-4 w-4" />
        Back to Pipeline
      </Button>

      {/* Header card */}
      <Card>
        <CardHeader className="flex flex-row items-start justify-between">
          <div className="space-y-1">
            {editingCustomerInfo ? (
              <div className="space-y-2" data-testid="customer-info-form">
                <Input
                  value={customerInfoForm.customer_name}
                  onChange={(e) => setCustomerInfoForm((p) => ({ ...p, customer_name: e.target.value }))}
                  placeholder="Customer name"
                  data-testid="sales-customer-name-input"
                />
                <Input
                  value={customerInfoForm.customer_phone}
                  onChange={(e) => setCustomerInfoForm((p) => ({ ...p, customer_phone: e.target.value }))}
                  placeholder="Phone"
                  data-testid="sales-customer-phone-input"
                />
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => setEditingCustomerInfo(false)}>Cancel</Button>
                  <Button size="sm" onClick={saveCustomerInfo} disabled={updateCustomer.isPending} data-testid="save-customer-info-btn">
                    {updateCustomer.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Save'}
                  </Button>
                </div>
              </div>
            ) : (
              <>
                <div className="flex items-center gap-2">
                  <CardTitle className="text-lg">
                    {entry.customer_name ?? 'Unknown Customer'}
                  </CardTitle>
                  <Button variant="ghost" size="sm" onClick={startEditCustomerInfo} data-testid="edit-customer-info-btn" className="h-6 px-2">
                    <Edit className="h-3 w-3" />
                  </Button>
                </div>
                <div className="flex items-center gap-4 text-sm text-slate-500">
                  {entry.customer_phone && (
                    <span className="flex items-center gap-1">
                      <Phone className="h-3.5 w-3.5" />
                      {entry.customer_phone}
                    </span>
                  )}
                  {entry.property_address && (
                    <span>{entry.property_address}</span>
                  )}
                </div>
              </>
            )}
          </div>
          <div className="flex items-center gap-2">
            <span
              className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${statusConfig?.className ?? 'bg-slate-100 text-slate-700'}`}
            >
              {statusConfig?.label ?? entry.status}
              {entry.override_flag && (
                <span className="ml-1" title="Manually overridden">⚠</span>
              )}
            </span>
            {!isTerminal && (
              <Select value="" onValueChange={handleStatusOverride}>
                <SelectTrigger className="h-7 w-auto text-xs border-slate-200" data-testid="pipeline-stage-select">
                  <SelectValue placeholder="Change stage..." />
                </SelectTrigger>
                <SelectContent>
                  {ALL_STATUSES.filter((s) => s !== entry.status).map((s) => (
                    <SelectItem key={s} value={s}>
                      {SALES_STATUS_CONFIG[s]?.label ?? s}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Details grid */}
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-slate-500">Job Type</span>
              <p className="font-medium">{entry.job_type ?? 'N/A'}</p>
            </div>
            <div>
              <span className="text-slate-500">Last Contact</span>
              <p className="font-medium">
                {entry.last_contact_date
                  ? formatDistanceToNow(new Date(entry.last_contact_date), {
                      addSuffix: true,
                    })
                  : 'Never'}
              </p>
            </div>
            {entry.notes && (
              <div className="col-span-2">
                <span className="text-slate-500">Notes</span>
                <p className="font-medium whitespace-pre-wrap">{entry.notes}</p>
              </div>
            )}
            {entry.closed_reason && (
              <div className="col-span-2">
                <span className="text-slate-500">Closed Reason</span>
                <p className="font-medium">{entry.closed_reason}</p>
              </div>
            )}
          </div>

          {/* Signing actions row — only signing-related buttons remain here */}
          {!isTerminal && (
            <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-100">
              {/* Document selector when multiple signing docs exist */}
              {hasMultipleSigningDocs && (
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      size="sm"
                      variant="outline"
                      data-testid="signing-doc-selector"
                    >
                      <FileText className="mr-1 h-3.5 w-3.5" />
                      {selectedDoc?.file_name ?? 'Select document'}
                      <ChevronDown className="ml-1 h-3 w-3" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="start">
                    {signingDocs.map((doc) => (
                      <DropdownMenuItem
                        key={doc.id}
                        onClick={() => setSelectedDocId(doc.id)}
                        data-testid={`signing-doc-option-${doc.id}`}
                      >
                        <FileText className="mr-2 h-3.5 w-3.5 text-slate-400" />
                        <span className="truncate">{doc.file_name}</span>
                        <span className="ml-2 text-xs text-slate-400">{doc.document_type}</span>
                      </DropdownMenuItem>
                    ))}
                  </DropdownMenuContent>
                </DropdownMenu>
              )}

              {/* Email signing */}
              <span title={signingDisabledReason}>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleEmailSign}
                  disabled={emailSign.isPending || !hasEmail || !signingReady}
                  data-testid="email-sign-btn"
                >
                  <Mail className="mr-1 h-3.5 w-3.5" />
                  {emailSign.isPending ? 'Sending…' : 'Email for Signature'}
                </Button>
              </span>

              {/* Embedded on-site signing */}
              <SignWellEmbeddedSigner
                entryId={entryId}
                onComplete={() => refetch()}
                disabled={!signingReady}
                disabledReason={signingDisabledReason}
              />
            </div>
          )}
        </CardContent>
      </Card>

      {/* ── Stage Walkthrough (hidden for terminal statuses) ── */}
      {isClosedLost ? (
        <div
          className="rounded-lg bg-slate-100 border border-slate-200 px-4 py-3 text-sm text-slate-600"
          data-testid="closed-lost-banner"
        >
          Closed Lost{entry.closed_reason ? ` — ${entry.closed_reason}` : ''}. No further actions.
        </div>
      ) : isClosedWon ? (
        <div
          className="rounded-lg bg-emerald-50 border border-emerald-200 px-4 py-3 text-sm text-emerald-800"
          data-testid="closed-won-banner"
        >
          Closed Won — converted to job. No further actions.
        </div>
      ) : (
        <>
          {/* Per-entry pending-reschedule banner (per OQ-2). Surfaces the
              customer's R reply inline so staff doesn't have to scroll up
              to the queue at the top of /sales. */}
          {currentEvent?.confirmation_status === 'reschedule_requested' && (
            <div
              className="rounded-lg bg-orange-50 border border-orange-200 px-4 py-3 text-sm text-orange-900"
              data-testid="pending-reschedule-banner"
            >
              <p className="font-semibold">
                Customer asked to reschedule this estimate visit.
              </p>
              <p className="mt-1 text-orange-800">
                Pick a new slot in &quot;Schedule visit&quot; — submitting will
                update the visit and send a fresh Y/R/C confirmation. Their
                suggested times appear on the queue at the top of
                /sales.
              </p>
            </div>
          )}
          {currentEvent?.confirmation_status === 'cancelled' && (
            <div
              className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-900"
              data-testid="cancelled-visit-banner"
            >
              <p className="font-semibold">
                Customer cancelled this estimate visit.
              </p>
              <p className="mt-1 text-red-800">
                Use the manual stage override to mark the entry as Closed
                Lost, or schedule a new visit.
              </p>
            </div>
          )}

          {/* StageStepper */}
          {stageKey && (
            <StageStepper
              currentStage={stageKey}
              onStageOverride={handleStageOverride}
              onMarkLost={() =>
                markLost.mutate(
                  { id: entryId },
                  {
                    onSuccess: () => { toast.success('Marked as lost'); refetch(); },
                    onError: () => toast.error('Failed to mark as lost'),
                  },
                )
              }
              visitScheduled={entry.status === 'estimate_scheduled'}
              visitConfirmationStatus={currentEvent?.confirmation_status}
            />
          )}

          {/* NowCard */}
          {stageKey && nowCardContent && (
            <NowCard
              stageKey={stageKey}
              content={nowCardContent}
              onAction={handleNowAction}
              onFileDrop={handleFileDrop}
              weekOfValue={weekOfValue}
              onWeekOfChange={handleWeekOfChange}
              // TODO(backend): replace with real estimate_sent_at column;
              // nudges_paused_until is now wired (NEW-D).
              estimateSentAt={entry.updated_at ?? entry.created_at}
              nudgesPaused={!!entry.nudges_paused_until}
            />
          )}

          {/* ActivityStrip */}
          <ActivityStrip events={activityEvents} />
        </>
      )}

      {/* Documents section */}
      <DocumentsSection customerId={entry.customer_id} />

      {/* Tags */}
      {entry.customer_id && (
        <Card data-testid="sales-tags-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold text-slate-500 uppercase tracking-wider">
              Tags
            </CardTitle>
          </CardHeader>
          <CardContent>
            <TagPicker customerId={entry.customer_id} />
          </CardContent>
        </Card>
      )}

      {/* Internal Notes Card */}
      <InternalNotesCard
        value={salesCustomer?.internal_notes ?? null}
        onSave={handleSaveSalesEntryNotes}
        isSaving={updateCustomer.isPending}
        readOnly={!entry.customer_id}
        data-testid-prefix="sales-"
      />

      {/* Suppress unused staffData warning */}
      {staffData && null}

      <ScheduleVisitModal
        entry={entry}
        currentEvent={currentEvent}
        open={scheduleModalOpen}
        onOpenChange={setScheduleModalOpen}
      />

      <MarkDeclinedDialog
        open={markDeclinedOpen}
        onOpenChange={setMarkDeclinedOpen}
        isPending={markLost.isPending}
        onConfirm={(reason) => {
          markLost.mutate(
            { id: entryId, closedReason: reason },
            {
              onSuccess: () => {
                toast.success('Marked as declined');
                setMarkDeclinedOpen(false);
                refetch();
              },
              onError: () => toast.error('Failed to mark as declined'),
            },
          );
        }}
      />

      <ForceConvertDialog
        open={forceConvertOpen}
        onOpenChange={setForceConvertOpen}
        isPending={forceConvert.isPending}
        onConfirm={() =>
          forceConvert.mutate(entryId, {
            onSuccess: () => {
              toast.success('Converted to job (forced)');
              setForceConvertOpen(false);
              refetch();
            },
            onError: (err) => {
              toast.error('Failed to force convert', {
                description: getErrorMessage(err),
              });
              setForceConvertOpen(false);
            },
          })
        }
      />

      <AddCustomerEmailDialog
        open={addEmailOpen}
        onOpenChange={setAddEmailOpen}
        customerId={entry.customer_id ?? ''}
        onSaved={() => refetch()}
      />

      {estimateSheetOpen && entry && (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-0 sm:p-4 sm:items-center">
          <SalesEstimateSheetWrapper
            entryId={entryId}
            onClose={() => setEstimateSheetOpen(false)}
            onSuccess={() => {
              refetch();
            }}
          />
        </div>
      )}
    </div>
  );
}
