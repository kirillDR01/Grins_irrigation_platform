import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';
import { useServiceOfferingHistory } from '../hooks';
import {
  PRICING_MODEL_LABEL,
  offeringDisplayLabel,
  type ServiceOffering,
} from '../types';

interface ArchiveHistorySheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  offering: ServiceOffering | null;
}

/**
 * Phase 2 ships with a placeholder card. The full chain renders once
 * Phase 1.5 lands the Stripe-style archive+create migration that
 * populates ``replaced_by_id``. The hook already calls the future
 * endpoint and falls back to ``[]`` so this component lights up
 * automatically when the backend starts returning rows.
 */
export function ArchiveHistorySheet({
  open,
  onOpenChange,
  offering,
}: ArchiveHistorySheetProps) {
  const { data: history, isLoading } = useServiceOfferingHistory(
    offering?.id ?? '',
  );

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full sm:max-w-lg flex flex-col gap-0"
        data-testid="archive-history-sheet"
      >
        <SheetHeader>
          <SheetTitle>Price history</SheetTitle>
          <SheetDescription>
            {offering
              ? `Versions of "${offeringDisplayLabel(offering)}"`
              : 'Select an offering to view its history.'}
          </SheetDescription>
        </SheetHeader>

        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
          {isLoading && (
            <p className="text-sm text-slate-500" data-testid="history-loading">
              Loading history…
            </p>
          )}

          {!isLoading && (!history || history.length === 0) && (
            <div
              className="rounded-md border border-dashed border-slate-300 bg-slate-50/60 p-4 text-sm text-slate-600"
              data-testid="history-placeholder"
            >
              <p className="font-medium text-slate-800">
                History view available after Phase 1.5
              </p>
              <p className="mt-1 text-slate-500">
                The Stripe-style archive + create migration is queued behind
                this phase. Once it ships, every price edit appears here as a
                replaced row with a diff against the next version.
              </p>
            </div>
          )}

          {history && history.length > 0 && (
            <ul className="space-y-2" data-testid="history-list">
              {history.map((entry) => (
                <li
                  key={entry.id}
                  className="rounded-md border border-slate-200 bg-white p-3 text-sm"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-slate-800">
                      {entry.display_name ?? '—'}
                    </span>
                    <span className="text-xs text-slate-500">
                      {new Date(entry.updated_at).toLocaleString()}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-slate-500">
                    Pricing: {PRICING_MODEL_LABEL[entry.pricing_model] ?? entry.pricing_model}
                    {entry.is_active ? '' : ' · archived'}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
