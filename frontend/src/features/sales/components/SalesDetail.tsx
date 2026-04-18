import { useMemo, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
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
} from '../hooks/useSalesPipeline';
import { SALES_STATUS_CONFIG, TERMINAL_STATUSES, ALL_STATUSES } from '../types/pipeline';
import type { SalesEntryStatus } from '../types/pipeline';
import { StatusActionButton } from './StatusActionButton';
import { DocumentsSection } from './DocumentsSection';
import { SignWellEmbeddedSigner } from './SignWellEmbeddedSigner';
import { formatDistanceToNow } from 'date-fns';
import type { SalesDocument } from '../api/salesPipelineApi';

interface SalesDetailProps {
  entryId: string;
}

export function SalesDetail({ entryId }: SalesDetailProps) {
  const navigate = useNavigate();
  const { data: entry, isLoading, error, refetch } = useSalesEntry(entryId);
  const emailSign = useTriggerEmailSigning();
  const updateCustomer = useUpdateCustomer();
  const queryClient = useQueryClient();
  const overrideStatus = useOverrideSalesStatus();
  const { data: staffData } = useStaff({ is_active: true });

  // Fetch customer for internal_notes display
  const { data: salesCustomer } = useCustomerDetail(entry?.customer_id ?? '');

  // Inline edit state — Task 10.1
  const [editingCustomerInfo, setEditingCustomerInfo] = useState(false);
  const [customerInfoForm, setCustomerInfoForm] = useState({
    customer_name: '',
    customer_phone: '',
  });

  const [editingStatus, setEditingStatus] = useState(false);

  // Fetch documents to determine signing button state — Validates: Req 9.3, 9.5
  const { data: documents } = useSalesDocuments(entry?.customer_id ?? '');
  const signingDocs = useMemo<SalesDocument[]>(
    () =>
      (documents ?? []).filter(
        (d) => d.document_type === 'estimate' || d.document_type === 'contract',
      ),
    [documents],
  );
  const hasSigningDoc = signingDocs.length > 0;
  const hasMultipleSigningDocs = signingDocs.length > 1;

  // Track which document is selected when multiple exist
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const selectedDoc = signingDocs.find((d) => d.id === selectedDocId) ?? signingDocs[0] ?? null;

  // bughunt M-17: validate that the selected doc's file_key actually
  // resolves to a presigned URL before unlocking the signing buttons.
  // A doc row whose underlying S3 object is missing/expired now
  // disables Email/Embedded sign instead of opening a broken iframe.
  const presign = useDocumentPresign(
    entry?.customer_id,
    selectedDoc?.id,
  );
  const presignReady = !!presign.data?.download_url;
  const presignFailed = presign.isError;
  const signingDisabledReason = !hasSigningDoc
    ? 'Upload an estimate document first'
    : presignFailed
      ? 'Document file is missing or expired — re-upload required.'
      : presign.isLoading
        ? 'Resolving document…'
        : undefined;
  const signingReady = hasSigningDoc && presignReady;

  // Internal notes save handler — PATCHes the customer, not the sales entry
  const handleSaveSalesEntryNotes = useCallback(
    async (next: string | null) => {
      if (!entry?.customer_id) return;
      await updateCustomer.mutateAsync({
        id: entry.customer_id,
        data: { internal_notes: next },
      });
      invalidateAfterCustomerInternalNotesSave(queryClient, entry.customer_id);
    },
    [entry?.customer_id, updateCustomer, queryClient],
  );

  if (isLoading) return <LoadingPage message="Loading sales entry…" />;

  if (error || !entry)
    return <ErrorMessage error={error ?? new Error('Not found')} onRetry={() => refetch()} />;

  const statusConfig = SALES_STATUS_CONFIG[entry.status];
  const isTerminal = TERMINAL_STATUSES.includes(entry.status);
  const hasEmail = !!entry.customer_name; // email availability checked server-side

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
      // Parse name into first/last
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
      setEditingStatus(false);
      refetch();
    } catch (err: unknown) {
      toast.error('Update failed', { description: getErrorMessage(err) });
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

          {/* Actions row */}
          {!isTerminal && (
            <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-100">
              <StatusActionButton entry={entry} />

              {/* Document selector when multiple signing docs exist — Validates: Req 9.5 */}
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

              {/* Email signing — Validates: Req 9.3; bughunt M-17 */}
              <span title={signingDisabledReason}>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleEmailSign}
                  disabled={
                    emailSign.isPending || !hasEmail || !signingReady
                  }
                  data-testid="email-sign-btn"
                >
                  <Mail className="mr-1 h-3.5 w-3.5" />
                  {emailSign.isPending ? 'Sending…' : 'Email for Signature'}
                </Button>
              </span>

              {/* Embedded on-site signing — Validates: Req 9.3; bughunt M-17 */}
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

      {/* Documents section */}
      <DocumentsSection customerId={entry.customer_id} />

      {/* Internal Notes Card — reads/writes customer.internal_notes */}
      <InternalNotesCard
        value={salesCustomer?.internal_notes ?? null}
        onSave={handleSaveSalesEntryNotes}
        isSaving={updateCustomer.isPending}
        readOnly={!entry.customer_id}
        data-testid-prefix="sales-"
      />
    </div>
  );
}
