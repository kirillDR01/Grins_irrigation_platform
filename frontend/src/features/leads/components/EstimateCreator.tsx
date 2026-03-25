import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Trash2, Loader2, Send } from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useEstimateTemplates, useCreateEstimate } from '../hooks';
import type { EstimateLineItem } from '../types';

interface EstimateCreatorProps {
  leadId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const emptyLineItem: EstimateLineItem = {
  item: '',
  description: '',
  unit_price: 0,
  quantity: 1,
};

export function EstimateCreator({ leadId, open, onOpenChange }: EstimateCreatorProps) {
  const { data: templates } = useEstimateTemplates();
  const createEstimate = useCreateEstimate();
  const navigate = useNavigate();
  const [selectedTemplateId, setSelectedTemplateId] = useState('');
  const [lineItems, setLineItems] = useState<EstimateLineItem[]>([{ ...emptyLineItem }]);
  const [notes, setNotes] = useState('');
  const [validUntil, setValidUntil] = useState('');

  const handleTemplateSelect = (templateId: string) => {
    setSelectedTemplateId(templateId);
    if (templateId === 'none') {
      setLineItems([{ ...emptyLineItem }]);
      setNotes('');
      return;
    }
    const template = templates?.find((t) => t.id === templateId);
    if (template) {
      setLineItems(template.line_items.length > 0 ? [...template.line_items] : [{ ...emptyLineItem }]);
      setNotes(template.terms ?? '');
    }
  };

  const updateLineItem = (index: number, field: keyof EstimateLineItem, value: string | number) => {
    setLineItems((prev) =>
      prev.map((item, i) => (i === index ? { ...item, [field]: value } : item))
    );
  };

  const addLineItem = () => {
    setLineItems((prev) => [...prev, { ...emptyLineItem }]);
  };

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
        lead_id: leadId,
        template_id: selectedTemplateId !== 'none' ? selectedTemplateId : undefined,
        line_items: validItems,
        notes: notes || undefined,
        valid_until: validUntil || undefined,
      });
      const estimateId = (result as { id?: string })?.id;
      toast.success('Estimate Created', {
        description: 'Estimate has been sent to the customer.',
        ...(estimateId && {
          action: {
            label: 'View Details',
            onClick: () => navigate(`/estimates/${estimateId}`),
          },
        }),
      });
      onOpenChange(false);
      resetForm();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to create estimate';
      toast.error('Error', { description: msg });
    }
  };

  const resetForm = () => {
    setSelectedTemplateId('');
    setLineItems([{ ...emptyLineItem }]);
    setNotes('');
    setValidUntil('');
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl max-h-[85vh] overflow-y-auto" data-testid="estimate-creator-dialog">
        <DialogHeader>
          <DialogTitle>Create Estimate</DialogTitle>
          <DialogDescription>
            Select a template or build a custom estimate with line items.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5 py-4">
          {/* Template Selector */}
          <div>
            <label className="text-sm font-medium text-slate-700 mb-1.5 block">Template</label>
            <Select value={selectedTemplateId} onValueChange={handleTemplateSelect}>
              <SelectTrigger data-testid="estimate-template-select">
                <SelectValue placeholder="Select a template..." />
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

          {/* Line Items */}
          <div>
            <label className="text-sm font-medium text-slate-700 mb-2 block">Line Items</label>
            <div className="space-y-3">
              {lineItems.map((item, index) => (
                <div
                  key={index}
                  className="grid grid-cols-12 gap-2 items-start"
                  data-testid={`line-item-${index}`}
                >
                  <div className="col-span-4">
                    <Input
                      placeholder="Item name"
                      value={item.item}
                      onChange={(e) => updateLineItem(index, 'item', e.target.value)}
                      data-testid={`line-item-name-${index}`}
                    />
                  </div>
                  <div className="col-span-3">
                    <Input
                      placeholder="Description"
                      value={item.description}
                      onChange={(e) => updateLineItem(index, 'description', e.target.value)}
                    />
                  </div>
                  <div className="col-span-2">
                    <Input
                      type="number"
                      placeholder="Price"
                      value={item.unit_price || ''}
                      onChange={(e) => updateLineItem(index, 'unit_price', parseFloat(e.target.value) || 0)}
                      data-testid={`line-item-price-${index}`}
                    />
                  </div>
                  <div className="col-span-2">
                    <Input
                      type="number"
                      placeholder="Qty"
                      min={1}
                      value={item.quantity || ''}
                      onChange={(e) => updateLineItem(index, 'quantity', parseInt(e.target.value) || 1)}
                    />
                  </div>
                  <div className="col-span-1 flex justify-center pt-2">
                    {lineItems.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeLineItem(index)}
                        className="text-slate-400 hover:text-red-500"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={addLineItem}
              className="mt-2"
              data-testid="add-line-item-btn"
            >
              <Plus className="mr-1 h-4 w-4" />
              Add Line Item
            </Button>
          </div>

          {/* Total */}
          <div className="flex justify-end">
            <div className="text-right">
              <p className="text-xs text-slate-400 uppercase">Total</p>
              <p className="text-xl font-bold text-slate-800" data-testid="estimate-total">
                ${total.toFixed(2)}
              </p>
            </div>
          </div>

          {/* Valid Until */}
          <div>
            <label className="text-sm font-medium text-slate-700 mb-1.5 block">Valid Until</label>
            <Input
              type="date"
              value={validUntil}
              onChange={(e) => setValidUntil(e.target.value)}
              data-testid="estimate-valid-until"
            />
          </div>

          {/* Notes */}
          <div>
            <label className="text-sm font-medium text-slate-700 mb-1.5 block">Notes / Terms</label>
            <Textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Additional notes or terms..."
              rows={3}
              data-testid="estimate-notes"
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={createEstimate.isPending}
            data-testid="send-estimate-btn"
          >
            {createEstimate.isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Send className="mr-2 h-4 w-4" />
            )}
            Send Estimate
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
