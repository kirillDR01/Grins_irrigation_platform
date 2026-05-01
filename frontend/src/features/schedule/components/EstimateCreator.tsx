/**
 * On-site estimate creation from appointment context (Req 32).
 * Template selection + line items editor.
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Trash2, Loader2, Send, Calculator, BookOpen } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useEstimateTemplates } from '@/features/leads/hooks';
import type { CustomerType } from '@/features/pricelist';
import { useCreateEstimateFromAppointment } from '../hooks/useAppointmentMutations';
import {
  LineItemPicker,
  type PickerLineItemDraft,
} from './EstimateSheet/LineItemPicker';

interface EstimateCreatorProps {
  appointmentId: string;
  onSuccess?: () => void;
  /**
   * Optional resolved customer type for the picker pre-filter.
   * Phase 3 / P4-RESOLVED — caller decides via lead.customer_type
   * → property.property_type → fallback. Defaults to ``residential``
   * with the override toggle inside the picker.
   */
  customerType?: CustomerType;
}

interface LineItem {
  item: string;
  description: string;
  unit_price: number;
  quantity: number;
  service_offering_id?: string;
  unit_cost?: number | null;
  material_markup_pct?: number;
  selected_tier?: string;
}

const emptyLineItem: LineItem = { item: '', description: '', unit_price: 0, quantity: 1 };

function lineItemMargin(item: LineItem): number | null {
  if (item.unit_cost == null || item.unit_cost <= 0) return null;
  const revenue = item.unit_price * item.quantity;
  if (revenue <= 0) return null;
  const cost = item.unit_cost * item.quantity;
  return ((revenue - cost) / revenue) * 100;
}

export function EstimateCreator({
  appointmentId,
  onSuccess,
  customerType,
}: EstimateCreatorProps) {
  const { data: templates } = useEstimateTemplates();
  const createEstimate = useCreateEstimateFromAppointment();
  const navigate = useNavigate();
  const [selectedTemplateId, setSelectedTemplateId] = useState('');
  const [lineItems, setLineItems] = useState<LineItem[]>([{ ...emptyLineItem }]);
  const [notes, setNotes] = useState('');
  const [pickerOpen, setPickerOpen] = useState(false);

  const handlePickerAdd = (draft: PickerLineItemDraft) => {
    const next: LineItem = {
      item: draft.item,
      description: draft.description,
      unit_price: draft.unit_price,
      quantity: draft.quantity,
      service_offering_id: draft.service_offering_id,
      unit_cost: draft.unit_cost,
      material_markup_pct: draft.material_markup_pct,
      selected_tier: draft.selected_tier,
    };
    setLineItems((prev) => {
      const onlyEmpty =
        prev.length === 1 && !prev[0].item.trim() && prev[0].unit_price === 0;
      if (onlyEmpty) return [next];
      return [...prev, next];
    });
  };

  const handleTemplateSelect = (templateId: string) => {
    setSelectedTemplateId(templateId);
    if (templateId === 'none') {
      setLineItems([{ ...emptyLineItem }]);
      setNotes('');
      return;
    }
    const template = templates?.find((t) => t.id === templateId);
    if (template) {
      setLineItems(
        template.line_items.length > 0 ? [...template.line_items] : [{ ...emptyLineItem }]
      );
      setNotes(template.terms ?? '');
    }
  };

  const updateLineItem = (
    index: number,
    field: keyof LineItem,
    value: string | number | null,
  ) => {
    setLineItems((prev) =>
      prev.map((item, i) => (i === index ? { ...item, [field]: value } : item))
    );
  };

  const addLineItem = () => setLineItems((prev) => [...prev, { ...emptyLineItem }]);

  const removeLineItem = (index: number) => {
    setLineItems((prev) => prev.filter((_, i) => i !== index));
  };

  const total = lineItems.reduce((sum, item) => sum + item.unit_price * item.quantity, 0);

  const handleSubmit = async () => {
    const validItems = lineItems.filter((item) => item.item.trim());
    if (validItems.length === 0) {
      toast.error('Add at least one line item');
      return;
    }
    try {
      const result = await createEstimate.mutateAsync({
        id: appointmentId,
        data: {
          template_id: selectedTemplateId !== 'none' ? selectedTemplateId : undefined,
          line_items: validItems,
          notes: notes || undefined,
        },
      });
      toast.success('Estimate Created', {
        description: 'Estimate has been sent to the customer.',
        action: {
          label: 'View Details',
          onClick: () => navigate(`/estimates/${result.id}`),
        },
      });
      onSuccess?.();
    } catch {
      toast.error('Error', { description: 'Failed to create estimate.' });
    }
  };

  return (
    <div data-testid="estimate-creator" className="space-y-3 p-3 bg-slate-50 rounded-xl">
      <div className="flex items-center gap-2 mb-1">
        <Calculator className="h-3.5 w-3.5 text-slate-400" />
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          Create Estimate
        </p>
      </div>

      {/* Entry points — pricelist picker + template selector coexist (E7). */}
      <div className="flex flex-wrap items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setPickerOpen((p) => !p)}
          data-testid="appt-pricelist-toggle"
        >
          <Plus className="mr-1 h-3 w-3" />
          {pickerOpen ? 'Close pricelist' : 'Add from pricelist'}
        </Button>
        <div className="flex-1 min-w-[180px]">
          <Select value={selectedTemplateId} onValueChange={handleTemplateSelect}>
            <SelectTrigger
              data-testid="appt-estimate-template-select"
              className="min-h-[44px] text-sm md:min-h-0 md:h-8 md:text-xs"
            >
              <BookOpen className="mr-1 h-3 w-3 text-slate-400" />
              <SelectValue placeholder="Use a template…" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="none">No Template (Custom)</SelectItem>
              {templates?.map((t) => (
                <SelectItem key={t.id} value={t.id}>
                  {t.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {pickerOpen && (
        <LineItemPicker
          customerType={customerType}
          onAdd={handlePickerAdd}
          onCancel={() => setPickerOpen(false)}
        />
      )}

      {/* Line Items */}
      <div className="space-y-2">
        <label className="text-xs font-medium text-slate-600 block">Line Items</label>
        {lineItems.map((item, index) => {
          const margin = lineItemMargin(item);
          return (
            <div
              key={index}
              className="space-y-1.5 rounded-md border border-slate-200 bg-white/50 p-2"
              data-testid={`appt-line-item-${index}`}
            >
              <div className="grid grid-cols-2 gap-1.5 items-start md:grid-cols-12">
                <div className="col-span-2 md:col-span-4">
                  <Input
                    placeholder="Item"
                    value={item.item}
                    onChange={(e) => updateLineItem(index, 'item', e.target.value)}
                    className="min-h-[44px] text-sm md:min-h-0 md:h-7 md:text-xs"
                    data-testid={`appt-line-item-name-${index}`}
                  />
                </div>
                <div className="col-span-2 md:col-span-3">
                  <Input
                    placeholder="Description"
                    value={item.description}
                    onChange={(e) =>
                      updateLineItem(index, 'description', e.target.value)
                    }
                    className="min-h-[44px] text-sm md:min-h-0 md:h-7 md:text-xs"
                  />
                </div>
                <div className="col-span-1 md:col-span-2">
                  <Input
                    type="number"
                    placeholder="Price"
                    value={item.unit_price || ''}
                    onChange={(e) =>
                      updateLineItem(
                        index,
                        'unit_price',
                        parseFloat(e.target.value) || 0,
                      )
                    }
                    className="min-h-[44px] text-sm md:min-h-0 md:h-7 md:text-xs"
                    data-testid={`appt-line-item-price-${index}`}
                  />
                </div>
                <div className="col-span-1 md:col-span-2 flex items-center gap-1">
                  <Input
                    type="number"
                    placeholder="Qty"
                    min={1}
                    value={item.quantity || ''}
                    onChange={(e) =>
                      updateLineItem(
                        index,
                        'quantity',
                        parseInt(e.target.value) || 1,
                      )
                    }
                    className="min-h-[44px] text-sm md:min-h-0 md:h-7 md:text-xs"
                  />
                  {lineItems.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeLineItem(index)}
                      className="text-slate-400 hover:text-red-500 p-1 min-w-[44px] min-h-[44px] flex items-center justify-center md:min-w-0 md:min-h-0 md:p-0"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  )}
                </div>
              </div>
              {/* Staff-only internal cost (Phase 3 / P5). Hidden from
                  customer renders — never include this in the
                  customer-facing PDF/portal templates. */}
              <div
                className="grid grid-cols-2 gap-1.5 items-center md:grid-cols-12"
                data-testid={`appt-line-item-cost-row-${index}`}
              >
                <label className="col-span-2 md:col-span-4 text-[11px] text-slate-500">
                  Internal cost (hidden from customer)
                </label>
                <div className="col-span-1 md:col-span-3">
                  <Input
                    type="number"
                    min={0}
                    step="0.01"
                    placeholder="Cost / unit"
                    value={item.unit_cost ?? ''}
                    onChange={(e) => {
                      const v = e.target.value;
                      const parsed = v === '' ? null : parseFloat(v);
                      updateLineItem(
                        index,
                        'unit_cost',
                        Number.isFinite(parsed as number) ? (parsed as number) : null,
                      );
                    }}
                    className="min-h-[36px] text-xs md:min-h-0 md:h-7"
                    data-testid={`appt-line-item-unit-cost-${index}`}
                  />
                </div>
                <div className="col-span-1 md:col-span-3 text-[11px] text-slate-500">
                  {margin != null ? (
                    <span data-testid={`appt-line-item-margin-${index}`}>
                      Margin: {margin.toFixed(1)}%
                    </span>
                  ) : (
                    <span className="text-slate-300">Margin: —</span>
                  )}
                </div>
                <div className="col-span-2 md:col-span-2 text-right">
                  {item.service_offering_id && (
                    <span
                      className="text-[10px] uppercase tracking-wide text-emerald-600"
                      data-testid={`appt-line-item-from-pricelist-${index}`}
                    >
                      pricelist
                    </span>
                  )}
                </div>
              </div>
            </div>
          );
        })}
        <Button
          variant="ghost"
          size="sm"
          onClick={addLineItem}
          className="h-6 text-xs"
          data-testid="appt-add-line-item-btn"
        >
          <Plus className="mr-1 h-3 w-3" /> Add Item
        </Button>
      </div>

      {/* Total */}
      <div className="flex justify-end">
        <p className="text-sm font-bold text-slate-800" data-testid="appt-estimate-total">
          Total: ${total.toFixed(2)}
        </p>
      </div>

      {/* Notes */}
      <Textarea
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        placeholder="Notes or terms..."
        rows={2}
        className="text-sm md:text-xs"
        data-testid="appt-estimate-notes"
      />

      <Button
        onClick={handleSubmit}
        disabled={createEstimate.isPending}
        size="sm"
        className="w-full bg-amber-500 hover:bg-amber-600 text-white min-h-[48px] text-sm md:min-h-0 md:h-8 md:text-xs"
        data-testid="appt-send-estimate-btn"
      >
        {createEstimate.isPending ? (
          <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
        ) : (
          <Send className="mr-1.5 h-3.5 w-3.5" />
        )}
        Send Estimate
      </Button>
    </div>
  );
}
