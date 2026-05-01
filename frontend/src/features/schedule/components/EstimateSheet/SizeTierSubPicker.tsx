import { useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type { ServiceOffering } from '@/features/pricelist';

interface TierEntry {
  label: string;
  price: number;
}

/**
 * Reads ``pricing_rule.tiers`` looking for either an array of
 * ``{label, price}`` entries or an object mapping ``label -> price``.
 * Returns ``[]`` if the rule shape doesn't match the expected forms.
 */
function readTiers(offering: ServiceOffering): TierEntry[] {
  const rule = offering.pricing_rule;
  if (!rule || typeof rule !== 'object') return [];
  const tiers = (rule as Record<string, unknown>).tiers;
  if (Array.isArray(tiers)) {
    return tiers
      .map((t): TierEntry | null => {
        if (t && typeof t === 'object') {
          const label = (t as Record<string, unknown>).label;
          const price = (t as Record<string, unknown>).price;
          if (typeof label === 'string' && typeof price === 'number') {
            return { label, price };
          }
        }
        return null;
      })
      .filter((x): x is TierEntry => x !== null);
  }
  if (tiers && typeof tiers === 'object') {
    return Object.entries(tiers as Record<string, unknown>)
      .map(([label, value]): TierEntry | null => {
        const price = typeof value === 'number' ? value : Number(value);
        return Number.isFinite(price) ? { label, price } : null;
      })
      .filter((x): x is TierEntry => x !== null);
  }
  return [];
}

interface SizeTierSubPickerProps {
  offering: ServiceOffering;
  onSelect: (tierLabel: string, price: number) => void;
  onCancel: () => void;
  testIdPrefix?: string;
}

export function SizeTierSubPicker({
  offering,
  onSelect,
  onCancel,
  testIdPrefix = 'size-tier-subpicker',
}: SizeTierSubPickerProps) {
  const tiers = readTiers(offering);
  const [tier, setTier] = useState<string>(tiers[0]?.label ?? '');

  if (tiers.length === 0) {
    return (
      <div
        className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800"
        data-testid={`${testIdPrefix}-empty`}
      >
        <p>This offering has no tiers configured.</p>
        <Button
          variant="outline"
          size="sm"
          className="mt-2"
          onClick={onCancel}
        >
          Cancel
        </Button>
      </div>
    );
  }

  const selected = tiers.find((t) => t.label === tier) ?? tiers[0];

  return (
    <div
      className="space-y-2 rounded-md border border-slate-200 bg-white p-3"
      data-testid={testIdPrefix}
    >
      <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
        Pick a size tier
      </p>
      <Select value={tier} onValueChange={setTier}>
        <SelectTrigger data-testid={`${testIdPrefix}-trigger`}>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {tiers.map((t) => (
            <SelectItem key={t.label} value={t.label}>
              {t.label} — ${t.price.toFixed(2)}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <div className="flex justify-end gap-2">
        <Button variant="ghost" size="sm" onClick={onCancel}>
          Cancel
        </Button>
        <Button
          size="sm"
          onClick={() => onSelect(selected.label, selected.price)}
          data-testid={`${testIdPrefix}-confirm`}
        >
          Add line
        </Button>
      </div>
    </div>
  );
}
