/**
 * CustomerNotesEditor — shared, auto-save-on-blur editor for the customer's
 * canonical internal_notes blob.
 *
 * Cluster A unification: every surface that previously had a per-entity
 * notes textarea (Customer / Sales / Job / Appointment / Lead post-convert)
 * mounts this component so all reads/writes go through one column.
 *
 * Save semantics:
 * - Auto-saves on blur whenever the textarea value changed since the last
 *   successful save.
 * - Flashes a "Saved" indicator for 1500ms on success.
 * - Reverts to the previous value + toasts on error.
 * - Skips the PATCH entirely if the value is unchanged.
 *
 * Use as: `<CustomerNotesEditor customerId={...} initialValue={customer.internal_notes} />`
 * On surfaces that fetch the customer themselves, pass `initialValue` from
 * the fetched customer row. The component does not re-fetch; the parent's
 * TanStack Query cache invalidation (handled by useUpdateCustomer +
 * invalidateAfterCustomerMutation) keeps the rendered value fresh.
 */

import { useRef, useState } from 'react';
import { toast } from 'sonner';
import { Textarea } from '@/components/ui/textarea';
import { useUpdateCustomer } from '@/features/customers/hooks/useCustomerMutations';
import { invalidateAfterCustomerInternalNotesSave } from '@/shared/utils/invalidationHelpers';
import { useQueryClient } from '@tanstack/react-query';

const SAVED_FLASH_MS = 1500;

export interface CustomerNotesEditorProps {
  customerId: string;
  initialValue?: string | null;
  readOnly?: boolean;
  placeholder?: string;
  rows?: number;
  'data-testid'?: string;
}

export function CustomerNotesEditor({
  customerId,
  initialValue = '',
  readOnly = false,
  placeholder = 'Internal notes — visible to staff only',
  rows = 5,
  'data-testid': testId = 'customer-notes-editor',
}: CustomerNotesEditorProps) {
  const queryClient = useQueryClient();
  const updateCustomer = useUpdateCustomer();
  const initialValueRef = useRef<string>(initialValue ?? '');
  const [savedFlash, setSavedFlash] = useState(false);

  const handleBlur = (event: React.FocusEvent<HTMLTextAreaElement>) => {
    if (readOnly) return;
    const next = event.currentTarget.value;
    if (next === initialValueRef.current) return;

    updateCustomer.mutate(
      {
        id: customerId,
        data: { internal_notes: next.trim() === '' ? null : next },
      },
      {
        onSuccess: () => {
          initialValueRef.current = next;
          invalidateAfterCustomerInternalNotesSave(queryClient, customerId);
          setSavedFlash(true);
          setTimeout(() => setSavedFlash(false), SAVED_FLASH_MS);
        },
        onError: () => {
          event.currentTarget.value = initialValueRef.current;
          toast.error("Couldn't save notes — try again");
        },
      },
    );
  };

  return (
    <div className="space-y-1.5" data-testid={testId}>
      <Textarea
        defaultValue={initialValueRef.current}
        disabled={readOnly || updateCustomer.isPending}
        onBlur={handleBlur}
        placeholder={placeholder}
        rows={rows}
        data-testid={`${testId}-textarea`}
      />
      <div className="flex items-center justify-end gap-2 h-4 text-xs">
        {updateCustomer.isPending && (
          <span className="text-slate-400">Saving…</span>
        )}
        {savedFlash && !updateCustomer.isPending && (
          <span
            className="text-emerald-600 font-medium"
            data-testid={`${testId}-saved-indicator`}
          >
            Saved
          </span>
        )}
      </div>
    </div>
  );
}
