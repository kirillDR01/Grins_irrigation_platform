// @ts-nocheck — pre-existing TS errors documented in bughunt/2026-04-29-pre-existing-tsc-errors.md
/**
 * Side-by-side merge comparison modal with radio buttons for field selection.
 *
 * Validates: CRM Changes Update 2 Req 6.1, 6.2, 6.3, 6.7, 6.12
 */

import { useState, useMemo } from 'react';
import { Users, AlertTriangle, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useMergeCustomers, useCustomer } from '../hooks';
import { usePreviewMerge } from '../hooks/usePreviewMerge';
import type { MergeFieldSelection } from '../types';
import { getCustomerFullName } from '../types';
import { toast } from 'sonner';

/** Fields eligible for radio-button selection during merge. */
const MERGE_FIELDS = [
  { key: 'first_name', label: 'First Name' },
  { key: 'last_name', label: 'Last Name' },
  { key: 'phone', label: 'Phone' },
  { key: 'email', label: 'Email' },
  { key: 'lead_source', label: 'Lead Source' },
  { key: 'internal_notes', label: 'Internal Notes' },
] as const;

interface MergeComparisonModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  customerAId: string;
  customerBId: string;
  score: number;
  onMergeComplete?: () => void;
}

export function MergeComparisonModal({
  open,
  onOpenChange,
  customerAId,
  customerBId,
  score,
  onMergeComplete,
}: MergeComparisonModalProps) {
  const { data: customerA, isLoading: loadingA } = useCustomer(customerAId);
  const { data: customerB, isLoading: loadingB } = useCustomer(customerBId);

  // Primary defaults to A; user can swap
  const [primarySide, setPrimarySide] = useState<'a' | 'b'>('a');
  const primaryId = primarySide === 'a' ? customerAId : customerBId;
  const duplicateId = primarySide === 'a' ? customerBId : customerAId;

  // Field selections: default to primary's value, keyed by primarySide
  const [selections, setSelections] = useState<Record<string, 'a' | 'b'>>({});

  // Derive effective selections: use explicit selections if they exist, else default to primary
  const effectiveSelections = useMemo(() => {
    const result: Record<string, 'a' | 'b'> = {};
    for (const f of MERGE_FIELDS) {
      result[f.key] = selections[f.key] ?? primarySide;
    }
    return result;
  }, [selections, primarySide]);

  // Preview
  const fieldSelections: MergeFieldSelection[] = Object.entries(effectiveSelections).map(
    ([field_name, source]) => ({ field_name, source })
  );
  const {
    data: preview,
    isLoading: previewLoading,
    error: previewError,
  } = usePreviewMerge(primaryId, duplicateId, fieldSelections, open && !!customerA && !!customerB);

  const mergeMutation = useMergeCustomers(primaryId);

  const handleConfirm = async () => {
    try {
      await mergeMutation.mutateAsync({
        duplicate_id: duplicateId,
        field_selections: fieldSelections,
      });
      toast.success('Customers merged successfully');
      onOpenChange(false);
      onMergeComplete?.();
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Merge failed';
      toast.error(msg);
    }
  };

  const isLoading = loadingA || loadingB;
  const hasBlockers = (preview?.blockers?.length ?? 0) > 0;

  const getFieldValue = (side: 'a' | 'b', key: string): string => {
    const c = side === 'a' ? customerA : customerB;
    if (!c) return '';
    const val = (c as Record<string, unknown>)[key];
    return val != null ? String(val) : '';
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto" data-testid="merge-comparison-modal">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Users className="h-5 w-5" />
            Merge Customers
            <Badge variant="outline" className="ml-2">Score: {score}</Badge>
          </DialogTitle>
          <DialogDescription>
            Select which values to keep for each field. The duplicate record will be merged into the primary.
          </DialogDescription>
        </DialogHeader>

        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
          </div>
        ) : customerA && customerB ? (
          <div className="space-y-4">
            {/* Blockers */}
            {hasBlockers && (
              <Alert variant="destructive" data-testid="merge-blockers">
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>
                  <p className="font-medium">Cannot merge:</p>
                  <ul className="list-disc pl-4 mt-1 text-sm">
                    {preview!.blockers.map((b, i) => <li key={i}>{b}</li>)}
                  </ul>
                </AlertDescription>
              </Alert>
            )}

            {/* Primary selector */}
            <div className="grid grid-cols-2 gap-3">
              {(['a', 'b'] as const).map((side) => {
                const c = side === 'a' ? customerA : customerB;
                const isPrimary = primarySide === side;
                return (
                  <button
                    key={side}
                    type="button"
                    onClick={() => { setPrimarySide(side); setSelections({}); }}
                    className={`p-3 rounded-lg border-2 text-left transition-colors ${
                      isPrimary
                        ? 'border-teal-300 bg-teal-50/50'
                        : 'border-slate-200 hover:border-slate-300'
                    }`}
                    data-testid={`select-primary-${side}`}
                  >
                    <Badge variant={isPrimary ? 'default' : 'outline'} className="text-xs mb-1">
                      {isPrimary ? 'Primary (Keep)' : 'Duplicate (Remove)'}
                    </Badge>
                    <p className="font-medium text-slate-800">{getCustomerFullName(c)}</p>
                    <p className="text-xs text-slate-500">{c.phone}</p>
                  </button>
                );
              })}
            </div>

            {/* Field-by-field radio selection */}
            <div className="border rounded-lg divide-y" data-testid="field-selections">
              {MERGE_FIELDS.map(({ key, label }) => {
                const valA = getFieldValue('a', key);
                const valB = getFieldValue('b', key);
                const differ = valA !== valB;
                return (
                  <div key={key} className="grid grid-cols-[120px_1fr_1fr] items-center gap-2 px-3 py-2 text-sm">
                    <span className="font-medium text-slate-600">{label}</span>
                    {(['a', 'b'] as const).map((side) => {
                      const val = side === 'a' ? valA : valB;
                      const selected = effectiveSelections[key] === side;
                      return (
                        <label
                          key={side}
                          className={`flex items-center gap-2 rounded px-2 py-1 cursor-pointer ${
                            selected ? 'bg-teal-50 text-teal-800' : 'text-slate-500'
                          } ${differ ? '' : 'opacity-60'}`}
                        >
                          <input
                            type="radio"
                            name={`merge-${key}`}
                            checked={selected}
                            onChange={() =>
                              setSelections((s) => ({ ...s, [key]: side }))
                            }
                            className="accent-teal-600"
                            data-testid={`radio-${key}-${side}`}
                          />
                          <span className="truncate">{val || <em className="text-slate-400">empty</em>}</span>
                        </label>
                      );
                    })}
                  </div>
                );
              })}
            </div>

            {/* Preview summary */}
            {preview && !hasBlockers && (
              <div className="bg-slate-50 rounded-lg p-3 text-sm text-slate-600 space-y-1" data-testid="merge-preview">
                <p className="font-medium text-slate-700">Records to reassign:</p>
                <ul className="grid grid-cols-2 gap-x-4 gap-y-0.5">
                  <li>Jobs: {preview.jobs_to_reassign}</li>
                  <li>Invoices: {preview.invoices_to_reassign}</li>
                  <li>Properties: {preview.properties_to_reassign}</li>
                  <li>Communications: {preview.communications_to_reassign}</li>
                  <li>Agreements: {preview.agreements_to_reassign}</li>
                </ul>
              </div>
            )}
            {previewLoading && (
              <p className="text-xs text-slate-400 text-center">Loading preview…</p>
            )}
            {previewError && (
              <p className="text-xs text-red-500 text-center">Preview failed</p>
            )}

            {/* Actions */}
            <div className="flex justify-end gap-2 pt-2">
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button
                onClick={handleConfirm}
                disabled={mergeMutation.isPending || hasBlockers}
                data-testid="confirm-merge-btn"
              >
                {mergeMutation.isPending ? 'Merging…' : 'Confirm Merge'}
              </Button>
            </div>
          </div>
        ) : (
          <p className="text-sm text-slate-500 text-center py-4">Customer data not found.</p>
        )}
      </DialogContent>
    </Dialog>
  );
}
