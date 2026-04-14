import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { ArrowLeft, ChevronDown, FileText, Mail, Phone } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { LoadingPage, ErrorMessage } from '@/shared/components';
import {
  useSalesEntry,
  useSalesDocuments,
  useTriggerEmailSigning,
} from '../hooks/useSalesPipeline';
import { SALES_STATUS_CONFIG, TERMINAL_STATUSES } from '../types/pipeline';
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

  if (isLoading) return <LoadingPage message="Loading sales entry…" />;
  if (error || !entry)
    return <ErrorMessage error={error ?? new Error('Not found')} onRetry={() => refetch()} />;

  const statusConfig = SALES_STATUS_CONFIG[entry.status];
  const isTerminal = TERMINAL_STATUSES.includes(entry.status);
  const hasEmail = !!entry.customer_name; // email availability checked server-side

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
            <CardTitle className="text-lg">
              {entry.customer_name ?? 'Unknown Customer'}
            </CardTitle>
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
          </div>
          <span
            className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${statusConfig?.className ?? 'bg-slate-100 text-slate-700'}`}
          >
            {statusConfig?.label ?? entry.status}
            {entry.override_flag && (
              <span className="ml-1" title="Manually overridden">⚠</span>
            )}
          </span>
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

              {/* Email signing — Validates: Req 9.3 */}
              <span
                title={!hasSigningDoc ? 'Upload an estimate document first' : undefined}
              >
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleEmailSign}
                  disabled={emailSign.isPending || !hasEmail || !hasSigningDoc}
                  data-testid="email-sign-btn"
                >
                  <Mail className="mr-1 h-3.5 w-3.5" />
                  {emailSign.isPending ? 'Sending…' : 'Email for Signature'}
                </Button>
              </span>

              {/* Embedded on-site signing — Validates: Req 9.3 */}
              <SignWellEmbeddedSigner
                entryId={entryId}
                onComplete={() => refetch()}
                disabled={!hasSigningDoc}
                disabledReason={!hasSigningDoc ? 'Upload an estimate document first' : undefined}
              />
            </div>
          )}
        </CardContent>
      </Card>

      {/* Documents section */}
      <DocumentsSection customerId={entry.customer_id} />
    </div>
  );
}
