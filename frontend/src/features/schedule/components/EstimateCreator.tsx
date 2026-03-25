/**
 * On-site estimate creation from appointment context (Req 32).
 * Template selection + line items editor.
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Trash2, Loader2, Send, Calculator } from 'lucide-react';
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
import { useCreateEstimateFromAppointment } from '../hooks/useAppointmentMutations';

interface EstimateCreatorProps {
  appointmentId: string;
  onSuccess?: () => void;
}

interface LineItem {
  item: string;
  description: string;
  unit_price: number;
  quantity: number;
}

const emptyLineItem: LineItem = { item: '', description: '', unit_price: 0, quantity: 1 };

export function EstimateCreator({ appointmentId, onSuccess }: EstimateCreatorProps) {
  const { data: templates } = useEstimateTemplates();
  const createEstimate = useCreateEstimateFromAppointment();
  const navigate = useNavigate();
  const [selectedTemplateId, setSelectedTemplateId] = useState('');
  const [lineItems, setLineItems] = useState<LineItem[]>([{ ...emptyLineItem }]);
  const [notes, setNotes] = useState('');

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

  const updateLineItem = (index: number, field: keyof LineItem, value: string | number) => {
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

      {/* Template Selector */}
      <div>
        <label className="text-xs font-medium text-slate-600 mb-1 block">Template</label>
        <Select value={selectedTemplateId} onValueChange={handleTemplateSelect}>
          <SelectTrigger data-testid="appt-estimate-template-select" className="min-h-[44px] text-sm md:min-h-0 md:h-8 md:text-xs">
            <SelectValue placeholder="Select a template..." />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="none">No Template (Custom)</SelectItem>
            {templates?.map((t) => (
              <SelectItem key={t.id} value={t.id}>{t.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Line Items */}
      <div className="space-y-2">
        <label className="text-xs font-medium text-slate-600 block">Line Items</label>
        {lineItems.map((item, index) => (
          <div key={index} className="grid grid-cols-2 gap-1.5 items-start md:grid-cols-12" data-testid={`appt-line-item-${index}`}>
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
                onChange={(e) => updateLineItem(index, 'description', e.target.value)}
                className="min-h-[44px] text-sm md:min-h-0 md:h-7 md:text-xs"
              />
            </div>
            <div className="col-span-1 md:col-span-2">
              <Input
                type="number"
                placeholder="Price"
                value={item.unit_price || ''}
                onChange={(e) => updateLineItem(index, 'unit_price', parseFloat(e.target.value) || 0)}
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
                onChange={(e) => updateLineItem(index, 'quantity', parseInt(e.target.value) || 1)}
                className="min-h-[44px] text-sm md:min-h-0 md:h-7 md:text-xs"
              />
              {lineItems.length > 1 && (
                <button type="button" onClick={() => removeLineItem(index)} className="text-slate-400 hover:text-red-500 p-1 min-w-[44px] min-h-[44px] flex items-center justify-center md:min-w-0 md:min-h-0 md:p-0">
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
          </div>
        ))}
        <Button variant="ghost" size="sm" onClick={addLineItem} className="h-6 text-xs" data-testid="appt-add-line-item-btn">
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
