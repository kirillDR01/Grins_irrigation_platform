/**
 * LeadConversionConflictModal — confirms lead conversion when Tier-1
 * duplicates exist. Surfaced after ``convert_lead`` / ``move_to_jobs`` /
 * ``move_to_sales`` returns 409 with a ``duplicate_found`` detail.
 *
 * The admin can either use an existing customer (navigate to the customer
 * detail page) or click "Convert anyway" to retry the original mutation
 * with ``force: true``.
 *
 * Validates: CR-6 (bughunt 2026-04-16).
 */

import { AlertTriangle, Loader2 } from 'lucide-react';

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { DuplicateWarning } from '@/features/customers/components/DuplicateWarning';
import type { Customer } from '@/features/customers/types';
import type { DuplicateConflictCustomer } from '../types';

interface LeadConversionConflictModalProps {
  open: boolean;
  onClose: () => void;
  duplicates: DuplicateConflictCustomer[];
  onUseExisting: (customer: DuplicateConflictCustomer) => void;
  onConvertAnyway: () => void;
  isConverting?: boolean;
  phone?: string | null;
  email?: string | null;
}

export function LeadConversionConflictModal({
  open,
  onClose,
  duplicates,
  onUseExisting,
  onConvertAnyway,
  isConverting = false,
  phone,
  email,
}: LeadConversionConflictModalProps) {
  // The inner <DuplicateWarning> expects Customer[] (has many extra fields
  // we don't care about here). The 409 payload carries the same id + name
  // + phone + email, which is all the warning banner reads.
  const matches = duplicates as unknown as Customer[];

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent
        className="max-w-lg"
        data-testid="lead-conversion-conflict-modal"
      >
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-amber-600" />
            Possible duplicate customer
          </DialogTitle>
          <DialogDescription>
            We already have {duplicates.length === 1 ? 'a customer' : 'customers'}{' '}
            matching this lead&apos;s
            {phone ? ` phone (${phone})` : ''}
            {phone && email ? ' or' : ''}
            {email ? ` email (${email})` : ''}
            . You can use the existing record or convert anyway.
          </DialogDescription>
        </DialogHeader>

        <DuplicateWarning
          matches={matches}
          onUseExisting={(c) =>
            onUseExisting(c as unknown as DuplicateConflictCustomer)
          }
        />

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={onClose}
            disabled={isConverting}
            data-testid="cancel-convert-btn"
          >
            Cancel
          </Button>
          <Button
            type="button"
            onClick={onConvertAnyway}
            disabled={isConverting}
            data-testid="convert-anyway-btn"
          >
            {isConverting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Converting…
              </>
            ) : (
              'Convert anyway'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
