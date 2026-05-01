import { useMemo, useState } from 'react';
import { Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { LoadingSpinner } from '@/shared/components';
import {
  PRICING_MODEL_LABEL,
  offeringDisplayLabel,
  useServiceOfferings,
  type CustomerType,
  type PricingModel,
  type ServiceOffering,
} from '@/features/pricelist';
import { SizeTierSubPicker } from './SizeTierSubPicker';
import { VariantSubPicker } from './VariantSubPicker';

export interface PickerLineItemDraft {
  service_offering_id: string;
  item: string;
  description: string;
  unit_price: number;
  quantity: number;
  unit_cost: number | null;
  material_markup_pct: number;
  selected_tier?: string;
  pricing_model: PricingModel;
}

interface LineItemPickerProps {
  /**
   * Resolved customer type for the active estimate. Phase 3 / P4-RESOLVED:
   * caller derives from ``lead.customer_type`` → ``property.property_type``
   * → ``'residential'``. Picker honours it as the default filter and
   * surfaces the override toggle below the search.
   */
  customerType?: CustomerType;
  onAdd: (draft: PickerLineItemDraft) => void;
  onCancel?: () => void;
}

const SUB_PICKER_MODELS = new Set<PricingModel>([
  'size_tier',
  'size_tier_plus_materials',
  'yard_tier',
  'variants',
]);

function rangeAnchorEntries(
  rule: Record<string, unknown> | null | undefined,
): Array<{ label: 'low' | 'mid' | 'high'; value: number }> {
  if (!rule || typeof rule !== 'object') return [];
  const anchors = (rule as Record<string, unknown>).range_anchors;
  if (!anchors || typeof anchors !== 'object') return [];
  const entries: Array<{ label: 'low' | 'mid' | 'high'; value: number }> = [];
  for (const key of ['low', 'mid', 'high'] as const) {
    const v = (anchors as Record<string, unknown>)[key];
    const n = typeof v === 'number' ? v : Number(v);
    if (Number.isFinite(n)) entries.push({ label: key, value: n });
  }
  return entries;
}

function defaultPriceFor(rule: Record<string, unknown> | null | undefined): number | null {
  const anchors = rangeAnchorEntries(rule);
  const mid = anchors.find((a) => a.label === 'mid');
  if (mid) return mid.value;
  if (!rule) return null;
  for (const key of ['price', 'price_min', 'price_per_unit', 'price_per_zone_min']) {
    const v = (rule as Record<string, unknown>)[key];
    const n = typeof v === 'number' ? v : Number(v);
    if (Number.isFinite(n)) return n;
  }
  return null;
}

function readMaxQuantity(
  rule: Record<string, unknown> | null | undefined,
): number | null {
  if (!rule) return null;
  for (const key of ['max_zones_specified', 'max_units_specified', 'max_zones', 'max_units']) {
    const v = (rule as Record<string, unknown>)[key];
    const n = typeof v === 'number' ? v : Number(v);
    if (Number.isFinite(n)) return n;
  }
  return null;
}

export function LineItemPicker({
  customerType,
  onAdd,
  onCancel,
}: LineItemPickerProps) {
  const [overrideAll, setOverrideAll] = useState(false);
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState<ServiceOffering | null>(null);
  const [quantity, setQuantity] = useState<number>(1);

  const params = useMemo(
    () => ({
      page: 1,
      page_size: 100,
      customer_type: overrideAll ? undefined : customerType,
      is_active: true,
      sort_by: 'name',
      sort_order: 'asc' as const,
    }),
    [overrideAll, customerType],
  );

  const { data, isLoading } = useServiceOfferings(params);

  const items = data?.items;
  const filtered = useMemo(() => {
    if (!items) return [] as ServiceOffering[];
    if (!search.trim()) return items;
    const q = search.toLowerCase();
    return items.filter((o) => {
      const label = offeringDisplayLabel(o).toLowerCase();
      const slug = (o.slug ?? '').toLowerCase();
      return label.includes(q) || slug.includes(q);
    });
  }, [items, search]);

  const maxQty = selected ? readMaxQuantity(selected.pricing_rule) : null;
  const aboveMax = maxQty != null && quantity > maxQty;

  function emitDraft(
    offering: ServiceOffering,
    overrides: Partial<PickerLineItemDraft>,
  ): void {
    const baseLabel = offeringDisplayLabel(offering);
    const fallback = defaultPriceFor(offering.pricing_rule) ?? 0;
    const draft: PickerLineItemDraft = {
      service_offering_id: offering.id,
      item: baseLabel,
      description: offering.subcategory ?? '',
      unit_price: overrides.unit_price ?? fallback,
      quantity: overrides.quantity ?? quantity,
      unit_cost: null,
      material_markup_pct: 0,
      pricing_model: offering.pricing_model,
      ...overrides,
    };
    onAdd(draft);
    setSelected(null);
    setQuantity(1);
  }

  function handleAddSelected() {
    if (!selected) return;
    emitDraft(selected, {});
  }

  function handleSwitchToCustom() {
    if (!selected) return;
    onAdd({
      service_offering_id: selected.id,
      item: `${offeringDisplayLabel(selected)} — custom quote`,
      description: 'Above standard tier — manual quote',
      unit_price: 0,
      quantity,
      unit_cost: null,
      material_markup_pct: 0,
      pricing_model: 'custom',
    });
    setSelected(null);
    setQuantity(1);
  }

  function handleAnchorPick(anchor: 'low' | 'mid' | 'high', price: number) {
    if (!selected) return;
    emitDraft(selected, { unit_price: price, selected_tier: anchor });
  }

  function handleTierPick(tierLabel: string, price: number) {
    if (!selected) return;
    emitDraft(selected, {
      unit_price: price,
      selected_tier: tierLabel,
      item: `${offeringDisplayLabel(selected)} (${tierLabel})`,
    });
  }

  function handleVariantPick(variantLabel: string, price: number | null) {
    if (!selected) return;
    emitDraft(selected, {
      unit_price: price ?? defaultPriceFor(selected.pricing_rule) ?? 0,
      selected_tier: variantLabel,
      item: `${offeringDisplayLabel(selected)} — ${variantLabel}`,
    });
  }

  return (
    <div
      className="space-y-3 rounded-lg border border-slate-200 bg-white p-3"
      data-testid="line-item-picker"
    >
      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-2 top-2.5 h-4 w-4 text-slate-400" />
          <Input
            data-testid="line-item-picker-search"
            placeholder={`Search ${overrideAll ? 'all' : customerType ?? 'all'} offerings…`}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-8"
          />
        </div>
        {onCancel && (
          <Button variant="ghost" size="sm" onClick={onCancel}>
            Close
          </Button>
        )}
      </div>

      <label className="flex items-center gap-2 text-xs text-slate-600">
        <Checkbox
          data-testid="line-item-picker-override"
          checked={overrideAll}
          onCheckedChange={(v) => setOverrideAll(v === true)}
        />
        Show all customer types
        {customerType && !overrideAll && (
          <span className="ml-1 rounded bg-slate-100 px-1.5 py-0.5 text-[10px] uppercase text-slate-600">
            {customerType}
          </span>
        )}
      </label>

      {isLoading && (
        <div className="flex justify-center py-4">
          <LoadingSpinner />
        </div>
      )}

      {!isLoading && !selected && (
        <ul
          className="max-h-72 overflow-y-auto divide-y divide-slate-100 rounded-md border border-slate-100"
          data-testid="line-item-picker-results"
        >
          {filtered.length === 0 && (
            <li className="px-3 py-6 text-center text-sm text-slate-500">
              No matching offerings.
            </li>
          )}
          {filtered.map((o) => (
            <li key={o.id}>
              <button
                type="button"
                onClick={() => {
                  setSelected(o);
                  setQuantity(1);
                }}
                className="w-full text-left px-3 py-2 hover:bg-slate-50 transition-colors flex items-start justify-between gap-3"
                data-testid={`line-item-picker-result-${o.id}`}
              >
                <div>
                  <div className="text-sm font-medium text-slate-800">
                    {offeringDisplayLabel(o)}
                  </div>
                  <div className="text-xs text-slate-500">
                    {o.customer_type ?? 'unset'} · {o.subcategory ?? o.category}
                  </div>
                </div>
                <Badge variant="outline" className="shrink-0">
                  {PRICING_MODEL_LABEL[o.pricing_model] ?? o.pricing_model}
                </Badge>
              </button>
            </li>
          ))}
        </ul>
      )}

      {selected && (
        <div
          className="space-y-3 rounded-md border border-slate-200 bg-slate-50 p-3"
          data-testid="line-item-picker-selected"
        >
          <div className="flex items-start justify-between">
            <div>
              <div className="text-sm font-semibold text-slate-800">
                {offeringDisplayLabel(selected)}
              </div>
              <div className="text-xs text-slate-500">
                {PRICING_MODEL_LABEL[selected.pricing_model] ??
                  selected.pricing_model}
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSelected(null)}
              data-testid="line-item-picker-back"
            >
              Back
            </Button>
          </div>

          {SUB_PICKER_MODELS.has(selected.pricing_model) ? (
            selected.pricing_model === 'variants' ? (
              <VariantSubPicker
                offering={selected}
                onSelect={handleVariantPick}
                onCancel={() => setSelected(null)}
              />
            ) : (
              <SizeTierSubPicker
                offering={selected}
                onSelect={handleTierPick}
                onCancel={() => setSelected(null)}
              />
            )
          ) : (
            <>
              {rangeAnchorEntries(selected.pricing_rule).length > 0 && (
                <div data-testid="line-item-picker-anchors" className="space-y-1">
                  <p className="text-[11px] uppercase font-semibold text-slate-500">
                    Quick picks
                  </p>
                  <div className="flex gap-2">
                    {rangeAnchorEntries(selected.pricing_rule).map((a) => (
                      <Button
                        key={a.label}
                        variant="outline"
                        size="sm"
                        onClick={() => handleAnchorPick(a.label, a.value)}
                        data-testid={`line-item-picker-anchor-${a.label}`}
                      >
                        {a.label[0].toUpperCase() + a.label.slice(1)} · $
                        {a.value.toFixed(2)}
                      </Button>
                    ))}
                  </div>
                </div>
              )}

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[11px] uppercase font-semibold text-slate-500">
                    Quantity
                  </label>
                  <Input
                    type="number"
                    min={1}
                    value={quantity}
                    onChange={(e) =>
                      setQuantity(parseInt(e.target.value || '1', 10) || 1)
                    }
                    data-testid="line-item-picker-quantity"
                  />
                  {maxQty != null && (
                    <p className="text-[11px] text-slate-500">
                      Max in standard tier: {maxQty}
                    </p>
                  )}
                </div>
                <div className="flex flex-col justify-end">
                  <Button
                    onClick={handleAddSelected}
                    disabled={aboveMax}
                    data-testid="line-item-picker-add"
                  >
                    Add line
                  </Button>
                </div>
              </div>

              {aboveMax && (
                <div
                  className="rounded-md border border-amber-300 bg-amber-50 p-2 text-xs text-amber-800"
                  data-testid="line-item-picker-above-max"
                >
                  <p className="font-medium">Above standard tier.</p>
                  <p>
                    Switch this line to a custom quote — the tech will fill the
                    price by hand.
                  </p>
                  <Button
                    size="sm"
                    variant="outline"
                    className="mt-2"
                    onClick={handleSwitchToCustom}
                    data-testid="line-item-picker-custom-quote"
                  >
                    Switch to custom quote
                  </Button>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
