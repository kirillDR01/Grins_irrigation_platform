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

interface VariantEntry {
  label: string;
  price: number | null;
}

function readVariants(offering: ServiceOffering): VariantEntry[] {
  const rule = offering.pricing_rule;
  if (!rule || typeof rule !== 'object') return [];
  const variants = (rule as Record<string, unknown>).variants;
  if (Array.isArray(variants)) {
    return variants
      .map((v): VariantEntry | null => {
        if (v && typeof v === 'object') {
          const label = (v as Record<string, unknown>).label;
          const price = (v as Record<string, unknown>).price;
          if (typeof label === 'string') {
            const p = typeof price === 'number' ? price : Number(price);
            return {
              label,
              price: Number.isFinite(p) ? p : null,
            };
          }
        }
        return null;
      })
      .filter((x): x is VariantEntry => x !== null);
  }
  if (variants && typeof variants === 'object') {
    return Object.entries(variants as Record<string, unknown>)
      .map(([label, value]): VariantEntry => {
        if (typeof value === 'number') return { label, price: value };
        if (value && typeof value === 'object') {
          const inner = (value as Record<string, unknown>).price;
          const p = typeof inner === 'number' ? inner : Number(inner);
          return { label, price: Number.isFinite(p) ? p : null };
        }
        return { label, price: null };
      });
  }
  return [];
}

interface VariantSubPickerProps {
  offering: ServiceOffering;
  onSelect: (variantLabel: string, price: number | null) => void;
  onCancel: () => void;
  testIdPrefix?: string;
}

export function VariantSubPicker({
  offering,
  onSelect,
  onCancel,
  testIdPrefix = 'variant-subpicker',
}: VariantSubPickerProps) {
  const variants = readVariants(offering);
  const [variant, setVariant] = useState<string>(variants[0]?.label ?? '');

  if (variants.length === 0) {
    return (
      <div
        className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800"
        data-testid={`${testIdPrefix}-empty`}
      >
        <p>This offering has no variants configured.</p>
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

  const selected = variants.find((v) => v.label === variant) ?? variants[0];

  return (
    <div
      className="space-y-2 rounded-md border border-slate-200 bg-white p-3"
      data-testid={testIdPrefix}
    >
      <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
        Pick a variant
      </p>
      <Select value={variant} onValueChange={setVariant}>
        <SelectTrigger data-testid={`${testIdPrefix}-trigger`}>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {variants.map((v) => (
            <SelectItem key={v.label} value={v.label}>
              {v.label}
              {v.price != null ? ` — $${v.price.toFixed(2)}` : ''}
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
