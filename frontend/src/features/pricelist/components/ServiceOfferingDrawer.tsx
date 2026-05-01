import { useMemo, useState } from 'react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';
import { Textarea } from '@/components/ui/textarea';
import {
  useCreateServiceOffering,
  useUpdateServiceOffering,
} from '../hooks';
import {
  PRICING_MODELS,
  PRICING_MODEL_LABEL,
  SERVICE_CATEGORY_LABEL,
  type CustomerType,
  type PricingModel,
  type PricingRule,
  type ServiceCategory,
  type ServiceOffering,
} from '../types';
import {
  getStructuredFields,
  readField,
  writeField,
} from '../utils/pricingRule';

const CATEGORIES: ServiceCategory[] = [
  'seasonal',
  'repair',
  'installation',
  'diagnostic',
  'landscaping',
];

const CUSTOMER_TYPES: CustomerType[] = ['residential', 'commercial'];

interface ServiceOfferingDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  offering: ServiceOffering | null;
}

interface FormState {
  name: string;
  display_name: string;
  slug: string;
  category: ServiceCategory;
  customer_type: CustomerType | '';
  subcategory: string;
  pricing_model: PricingModel;
  pricing_rule: PricingRule;
  pricing_rule_raw: string;
  pricing_rule_error: string | null;
  includes_materials: boolean;
  description: string;
  is_active: boolean;
}

function blankState(): FormState {
  return {
    name: '',
    display_name: '',
    slug: '',
    category: 'installation',
    customer_type: 'residential',
    subcategory: '',
    pricing_model: 'flat',
    pricing_rule: null,
    pricing_rule_raw: '{}',
    pricing_rule_error: null,
    includes_materials: false,
    description: '',
    is_active: true,
  };
}

function offeringToState(o: ServiceOffering): FormState {
  return {
    name: o.name,
    display_name: o.display_name ?? '',
    slug: o.slug ?? '',
    category: o.category,
    customer_type: o.customer_type ?? '',
    subcategory: o.subcategory ?? '',
    pricing_model: o.pricing_model,
    pricing_rule: o.pricing_rule,
    pricing_rule_raw: o.pricing_rule
      ? JSON.stringify(o.pricing_rule, null, 2)
      : '{}',
    pricing_rule_error: null,
    includes_materials: o.includes_materials,
    description: o.description ?? '',
    is_active: o.is_active,
  };
}

export function ServiceOfferingDrawer({
  open,
  onOpenChange,
  offering,
}: ServiceOfferingDrawerProps) {
  // Re-key form on open + offering identity so a closed→open transition
  // (or switching between offerings) starts from a fresh state without
  // the setState-in-useEffect anti-pattern.
  const formKey = `${open ? 'open' : 'closed'}:${offering?.id ?? 'new'}`;
  return (
    <ServiceOfferingDrawerInner
      key={formKey}
      open={open}
      onOpenChange={onOpenChange}
      offering={offering}
    />
  );
}

function ServiceOfferingDrawerInner({
  open,
  onOpenChange,
  offering,
}: ServiceOfferingDrawerProps) {
  const [state, setState] = useState<FormState>(() =>
    offering ? offeringToState(offering) : blankState(),
  );
  const isEdit = offering != null;

  const create = useCreateServiceOffering();
  const update = useUpdateServiceOffering();
  const submitting = create.isPending || update.isPending;

  const structuredFields = useMemo(
    () => getStructuredFields(state.pricing_model),
    [state.pricing_model],
  );

  function patch(partial: Partial<FormState>) {
    setState((s) => ({ ...s, ...partial }));
  }

  function setStructuredField(key: string, value: string, inputType: 'number' | 'text') {
    const next = writeField(state.pricing_rule, key, value, inputType);
    patch({
      pricing_rule: next,
      pricing_rule_raw: next ? JSON.stringify(next, null, 2) : '{}',
      pricing_rule_error: null,
    });
  }

  function setRawJson(value: string) {
    if (!value.trim()) {
      patch({
        pricing_rule_raw: value,
        pricing_rule: null,
        pricing_rule_error: null,
      });
      return;
    }
    try {
      const parsed = JSON.parse(value) as PricingRule;
      patch({
        pricing_rule_raw: value,
        pricing_rule: parsed,
        pricing_rule_error: null,
      });
    } catch (e) {
      patch({
        pricing_rule_raw: value,
        pricing_rule_error: e instanceof Error ? e.message : 'Invalid JSON',
      });
    }
  }

  async function handleSubmit() {
    if (state.pricing_rule_error) {
      toast.error('Fix pricing rule JSON before saving.');
      return;
    }
    if (!state.name.trim()) {
      toast.error('Name is required.');
      return;
    }
    const payload = {
      name: state.name.trim(),
      category: state.category,
      pricing_model: state.pricing_model,
      description: state.description.trim() || null,
      slug: state.slug.trim() || null,
      display_name: state.display_name.trim() || null,
      customer_type: (state.customer_type || null) as CustomerType | null,
      subcategory: state.subcategory.trim() || null,
      pricing_rule: state.pricing_rule,
      includes_materials: state.includes_materials,
    };

    try {
      if (isEdit && offering) {
        await update.mutateAsync({
          id: offering.id,
          data: { ...payload, is_active: state.is_active },
        });
        toast.success(`Updated "${payload.name}"`);
      } else {
        await create.mutateAsync(payload);
        toast.success(`Created "${payload.name}"`);
      }
      onOpenChange(false);
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Save failed';
      toast.error(msg);
    }
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full sm:max-w-xl flex flex-col gap-0 overflow-y-auto"
        data-testid="service-offering-drawer"
      >
        <SheetHeader>
          <SheetTitle>{isEdit ? 'Edit offering' : 'New offering'}</SheetTitle>
          <SheetDescription>
            {isEdit
              ? 'Update fields below. Pricing changes take effect on the next estimate.'
              : 'Add a service offering to the pricelist.'}
          </SheetDescription>
        </SheetHeader>

        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="offering-name">Name *</Label>
            <Input
              id="offering-name"
              data-testid="offering-name-input"
              value={state.name}
              onChange={(e) => patch({ name: e.target.value })}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="offering-display-name">Display name</Label>
              <Input
                id="offering-display-name"
                data-testid="offering-display-name-input"
                value={state.display_name}
                onChange={(e) => patch({ display_name: e.target.value })}
                placeholder={state.name}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="offering-slug">Slug</Label>
              <Input
                id="offering-slug"
                data-testid="offering-slug-input"
                value={state.slug}
                onChange={(e) => patch({ slug: e.target.value })}
                placeholder="spring_startup"
                disabled={isEdit && !!offering?.slug}
              />
              {isEdit && offering?.slug && (
                <p className="text-xs text-slate-500">
                  Slug is immutable once set.
                </p>
              )}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>Category</Label>
              <Select
                value={state.category}
                onValueChange={(v) => patch({ category: v as ServiceCategory })}
              >
                <SelectTrigger data-testid="offering-category-trigger">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {CATEGORIES.map((c) => (
                    <SelectItem key={c} value={c}>
                      {SERVICE_CATEGORY_LABEL[c]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label>Customer type</Label>
              <Select
                value={state.customer_type || 'unset'}
                onValueChange={(v) =>
                  patch({
                    customer_type: v === 'unset' ? '' : (v as CustomerType),
                  })
                }
              >
                <SelectTrigger data-testid="offering-customer-type-trigger">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="unset">— unset —</SelectItem>
                  {CUSTOMER_TYPES.map((t) => (
                    <SelectItem key={t} value={t}>
                      {t === 'residential' ? 'Residential' : 'Commercial'}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="offering-subcategory">Subcategory</Label>
            <Input
              id="offering-subcategory"
              value={state.subcategory}
              onChange={(e) => patch({ subcategory: e.target.value })}
              placeholder="seasonal_maintenance"
            />
          </div>

          <div className="space-y-1.5">
            <Label>Pricing model *</Label>
            <Select
              value={state.pricing_model}
              onValueChange={(v) => patch({ pricing_model: v as PricingModel })}
            >
              <SelectTrigger data-testid="offering-pricing-model-trigger">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PRICING_MODELS.map((m) => (
                  <SelectItem key={m} value={m}>
                    {PRICING_MODEL_LABEL[m]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {structuredFields.length > 0 && (
            <div
              className="space-y-3 rounded-md border border-slate-200 bg-slate-50/50 p-3"
              data-testid="pricing-rule-structured-panel"
            >
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {PRICING_MODEL_LABEL[state.pricing_model]} fields
              </p>
              {structuredFields.map((f) => (
                <div key={f.key} className="space-y-1.5">
                  <Label htmlFor={`rule-${f.key}`}>{f.label}</Label>
                  <Input
                    id={`rule-${f.key}`}
                    data-testid={`rule-${f.key}`}
                    type={f.inputType}
                    value={readField(state.pricing_rule, f.key)}
                    onChange={(e) =>
                      setStructuredField(f.key, e.target.value, f.inputType)
                    }
                  />
                  {f.helpText && (
                    <p className="text-xs text-slate-500">{f.helpText}</p>
                  )}
                </div>
              ))}
            </div>
          )}

          <div className="space-y-1.5">
            <Label htmlFor="offering-rule-json">Raw pricing rule (JSON)</Label>
            <Textarea
              id="offering-rule-json"
              data-testid="offering-rule-json"
              value={state.pricing_rule_raw}
              onChange={(e) => setRawJson(e.target.value)}
              rows={6}
              className="font-mono text-xs"
            />
            {state.pricing_rule_error && (
              <p className="text-xs text-rose-600" role="alert">
                {state.pricing_rule_error}
              </p>
            )}
          </div>

          <div className="flex items-center gap-2">
            <Checkbox
              id="offering-includes-materials"
              checked={state.includes_materials}
              onCheckedChange={(v) =>
                patch({ includes_materials: v === true })
              }
            />
            <Label
              htmlFor="offering-includes-materials"
              className="text-sm font-normal"
            >
              Includes materials (passed at cost)
            </Label>
          </div>

          {isEdit && (
            <div className="flex items-center gap-2">
              <Checkbox
                id="offering-is-active"
                checked={state.is_active}
                onCheckedChange={(v) => patch({ is_active: v === true })}
              />
              <Label
                htmlFor="offering-is-active"
                className="text-sm font-normal"
              >
                Active
              </Label>
            </div>
          )}

          <div className="space-y-1.5">
            <Label htmlFor="offering-description">Description</Label>
            <Textarea
              id="offering-description"
              value={state.description}
              onChange={(e) => patch({ description: e.target.value })}
              rows={3}
            />
          </div>
        </div>

        <SheetFooter className="flex-row justify-end gap-2 border-t border-slate-100 px-4 py-3">
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={submitting}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={submitting || !!state.pricing_rule_error}
            data-testid="offering-save"
          >
            {submitting ? 'Saving…' : isEdit ? 'Save changes' : 'Create offering'}
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
