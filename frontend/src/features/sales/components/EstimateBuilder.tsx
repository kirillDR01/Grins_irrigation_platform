import { useState, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Separator } from '@/components/ui/separator';
import { Plus, Trash2, ChevronRight, ChevronLeft, Send } from 'lucide-react';
import { toast } from 'sonner';
import { useEstimateTemplates, useCreateEstimate, useSendEstimate } from '../hooks';
import type { EstimateLineItem, EstimateTier, TierName } from '../types';

const STEPS = ['Template', 'Line Items', 'Tiers', 'Discount', 'Preview'] as const;

const EMPTY_LINE_ITEM: EstimateLineItem = {
  item: '',
  description: '',
  unit_price: 0,
  quantity: 1,
  material_cost: 0,
  labor_cost: 0,
};

export function EstimateBuilder() {
  const [step, setStep] = useState(0);
  const [lineItems, setLineItems] = useState<EstimateLineItem[]>([{ ...EMPTY_LINE_ITEM }]);
  const [tiers, setTiers] = useState<EstimateTier[]>([]);
  const [useTiers, setUseTiers] = useState(false);
  const [promotionCode, setPromotionCode] = useState('');
  const [discountPercent, setDiscountPercent] = useState(0);
  const [notes, setNotes] = useState('');
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>('');

  const { data: templates } = useEstimateTemplates();
  const createEstimate = useCreateEstimate();
  const sendEstimate = useSendEstimate();

  // Calculate totals
  const calculateLineTotal = (item: EstimateLineItem) =>
    (item.material_cost + item.labor_cost) * item.quantity;

  const subtotal = lineItems.reduce((sum, item) => sum + calculateLineTotal(item), 0);
  const discountAmount = subtotal * (discountPercent / 100);
  const total = subtotal - discountAmount;

  const addLineItem = useCallback(() => {
    setLineItems((prev) => [...prev, { ...EMPTY_LINE_ITEM }]);
  }, []);

  const removeLineItem = useCallback((index: number) => {
    setLineItems((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const updateLineItem = useCallback((index: number, field: keyof EstimateLineItem, value: string | number) => {
    setLineItems((prev) =>
      prev.map((item, i) => (i === index ? { ...item, [field]: value } : item))
    );
  }, []);

  const handleSelectTemplate = (templateId: string) => {
    setSelectedTemplateId(templateId);
    const template = templates?.find((t) => t.id === templateId);
    if (template) {
      setLineItems(
        template.line_items.map((li) => ({
          ...li,
          material_cost: li.unit_price,
          labor_cost: 0,
        }))
      );
    }
  };

  const initializeTiers = () => {
    if (tiers.length === 0) {
      const tierNames: TierName[] = ['good', 'better', 'best'];
      setTiers(
        tierNames.map((name) => ({
          name,
          line_items: lineItems.map((li) => ({ ...li })),
          total: lineItems.reduce((sum, li) => sum + calculateLineTotal(li), 0),
        }))
      );
    }
    setUseTiers(true);
  };

  const handleSubmit = async () => {
    try {
      const result = await createEstimate.mutateAsync({
        template_id: selectedTemplateId || undefined,
        line_items: lineItems,
        options: useTiers ? tiers : undefined,
        promotion_code: promotionCode || undefined,
        notes: notes || undefined,
      });
      toast.success('Estimate created successfully');
      // Auto-send
      if (result?.id) {
        await sendEstimate.mutateAsync(result.id);
        toast.success('Estimate sent to customer');
      }
    } catch {
      toast.error('Failed to create estimate');
    }
  };

  const canGoNext = () => {
    if (step === 1) return lineItems.some((li) => li.item.trim() !== '');
    return true;
  };

  return (
    <Card data-testid="estimate-builder">
      <CardHeader>
        <CardTitle className="text-lg">Estimate Builder</CardTitle>
        {/* Step indicator */}
        <div className="flex items-center gap-2 mt-2">
          {STEPS.map((label, i) => (
            <div key={label} className="flex items-center gap-2">
              <button
                onClick={() => setStep(i)}
                data-testid={`step-${i}`}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                  i === step
                    ? 'bg-teal-100 text-teal-700'
                    : i < step
                      ? 'bg-emerald-50 text-emerald-600'
                      : 'bg-slate-100 text-slate-400'
                }`}
              >
                <span className="w-5 h-5 rounded-full bg-current/10 flex items-center justify-center text-[10px]">
                  {i + 1}
                </span>
                {label}
              </button>
              {i < STEPS.length - 1 && <ChevronRight className="h-3 w-3 text-slate-300" />}
            </div>
          ))}
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Step 1: Template Selection */}
        {step === 0 && (
          <div className="space-y-4" data-testid="step-template">
            <p className="text-sm text-slate-500">Select a template to start from, or begin with a blank estimate.</p>
            <Select value={selectedTemplateId} onValueChange={handleSelectTemplate}>
              <SelectTrigger data-testid="template-select">
                <SelectValue placeholder="Choose a template (optional)" />
              </SelectTrigger>
              <SelectContent>
                {templates?.map((t) => (
                  <SelectItem key={t.id} value={t.id}>{t.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button variant="outline" onClick={() => setStep(1)} data-testid="start-blank-btn">
              Start Blank
            </Button>
          </div>
        )}

        {/* Step 2: Line Items */}
        {step === 1 && (
          <div className="space-y-4" data-testid="step-line-items">
            {lineItems.map((item, index) => (
              <div key={index} className="grid grid-cols-12 gap-2 items-end" data-testid={`line-item-${index}`}>
                <div className="col-span-3">
                  <Label className="text-xs">Item</Label>
                  <Input
                    value={item.item}
                    onChange={(e) => updateLineItem(index, 'item', e.target.value)}
                    placeholder="Item name"
                    data-testid={`line-item-name-${index}`}
                  />
                </div>
                <div className="col-span-2">
                  <Label className="text-xs">Description</Label>
                  <Input
                    value={item.description}
                    onChange={(e) => updateLineItem(index, 'description', e.target.value)}
                    placeholder="Description"
                  />
                </div>
                <div className="col-span-2">
                  <Label className="text-xs">Material $</Label>
                  <Input
                    type="number"
                    min={0}
                    step={0.01}
                    value={item.material_cost || ''}
                    onChange={(e) => updateLineItem(index, 'material_cost', parseFloat(e.target.value) || 0)}
                    data-testid={`line-item-material-${index}`}
                  />
                </div>
                <div className="col-span-2">
                  <Label className="text-xs">Labor $</Label>
                  <Input
                    type="number"
                    min={0}
                    step={0.01}
                    value={item.labor_cost || ''}
                    onChange={(e) => updateLineItem(index, 'labor_cost', parseFloat(e.target.value) || 0)}
                    data-testid={`line-item-labor-${index}`}
                  />
                </div>
                <div className="col-span-1">
                  <Label className="text-xs">Qty</Label>
                  <Input
                    type="number"
                    min={1}
                    value={item.quantity}
                    onChange={(e) => updateLineItem(index, 'quantity', parseInt(e.target.value) || 1)}
                    data-testid={`line-item-qty-${index}`}
                  />
                </div>
                <div className="col-span-1 text-right text-sm font-medium pt-5">
                  ${calculateLineTotal(item).toFixed(2)}
                </div>
                <div className="col-span-1 pt-5">
                  {lineItems.length > 1 && (
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => removeLineItem(index)}
                      data-testid={`remove-line-item-${index}`}
                    >
                      <Trash2 className="h-4 w-4 text-red-400" />
                    </Button>
                  )}
                </div>
              </div>
            ))}
            <Button variant="outline" size="sm" onClick={addLineItem} data-testid="add-line-item-btn">
              <Plus className="h-4 w-4 mr-1" /> Add Line Item
            </Button>
            <Separator />
            <div className="flex justify-end text-sm font-semibold" data-testid="subtotal">
              Subtotal: ${subtotal.toFixed(2)}
            </div>
          </div>
        )}

        {/* Step 3: Tiers */}
        {step === 2 && (
          <div className="space-y-4" data-testid="step-tiers">
            {!useTiers ? (
              <div className="text-center py-8">
                <p className="text-sm text-slate-500 mb-4">
                  Optionally create Good / Better / Best pricing tiers for the customer.
                </p>
                <Button onClick={initializeTiers} data-testid="create-tiers-btn">
                  Create Tiers
                </Button>
                <Button variant="ghost" className="ml-2" onClick={() => setStep(3)} data-testid="skip-tiers-btn">
                  Skip
                </Button>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {tiers.map((tier) => (
                  <Card key={tier.name} data-testid={`tier-${tier.name}`}>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-base capitalize">{tier.name}</CardTitle>
                    </CardHeader>
                    <CardContent className="text-sm space-y-1">
                      {tier.line_items.map((li, i) => (
                        <div key={i} className="flex justify-between">
                          <span className="text-slate-600">{li.item || `Item ${i + 1}`}</span>
                          <span className="font-medium">${calculateLineTotal(li).toFixed(2)}</span>
                        </div>
                      ))}
                      <Separator className="my-2" />
                      <div className="flex justify-between font-semibold">
                        <span>Total</span>
                        <span>${tier.line_items.reduce((s, li) => s + calculateLineTotal(li), 0).toFixed(2)}</span>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Step 4: Discount */}
        {step === 3 && (
          <div className="space-y-4 max-w-md" data-testid="step-discount">
            <div>
              <Label>Promotion Code</Label>
              <Input
                value={promotionCode}
                onChange={(e) => setPromotionCode(e.target.value)}
                placeholder="Enter promo code"
                data-testid="promo-code-input"
              />
            </div>
            <div>
              <Label>Discount %</Label>
              <Input
                type="number"
                min={0}
                max={100}
                value={discountPercent || ''}
                onChange={(e) => setDiscountPercent(parseFloat(e.target.value) || 0)}
                data-testid="discount-percent-input"
              />
            </div>
            <div className="text-sm space-y-1 pt-2">
              <div className="flex justify-between"><span>Subtotal</span><span>${subtotal.toFixed(2)}</span></div>
              {discountPercent > 0 && (
                <div className="flex justify-between text-red-500">
                  <span>Discount ({discountPercent}%)</span>
                  <span>-${discountAmount.toFixed(2)}</span>
                </div>
              )}
              <Separator />
              <div className="flex justify-between font-bold text-base" data-testid="total-amount">
                <span>Total</span><span>${total.toFixed(2)}</span>
              </div>
            </div>
          </div>
        )}

        {/* Step 5: Preview & Send */}
        {step === 4 && (
          <div className="space-y-4" data-testid="step-preview">
            <div className="bg-slate-50 rounded-lg p-4 space-y-3">
              <h3 className="font-semibold text-slate-800">Estimate Preview</h3>
              <div className="space-y-1 text-sm">
                {lineItems.filter((li) => li.item).map((li, i) => (
                  <div key={i} className="flex justify-between">
                    <span>{li.item} × {li.quantity}</span>
                    <span>${calculateLineTotal(li).toFixed(2)}</span>
                  </div>
                ))}
              </div>
              <Separator />
              <div className="text-sm space-y-1">
                <div className="flex justify-between"><span>Subtotal</span><span>${subtotal.toFixed(2)}</span></div>
                {discountPercent > 0 && (
                  <div className="flex justify-between text-red-500">
                    <span>Discount ({discountPercent}%)</span><span>-${discountAmount.toFixed(2)}</span>
                  </div>
                )}
                <div className="flex justify-between font-bold text-base">
                  <span>Total</span><span>${total.toFixed(2)}</span>
                </div>
              </div>
              {promotionCode && (
                <p className="text-xs text-slate-500">Promo: {promotionCode}</p>
              )}
            </div>
            <div>
              <Label>Notes</Label>
              <Textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Additional notes for the customer..."
                data-testid="estimate-notes"
              />
            </div>
            <Button
              onClick={handleSubmit}
              disabled={createEstimate.isPending || sendEstimate.isPending}
              data-testid="send-estimate-btn"
            >
              <Send className="h-4 w-4 mr-2" />
              {createEstimate.isPending ? 'Creating...' : sendEstimate.isPending ? 'Sending...' : 'Create & Send Estimate'}
            </Button>
          </div>
        )}

        {/* Navigation */}
        <div className="flex justify-between pt-4">
          <Button
            variant="outline"
            onClick={() => setStep((s) => Math.max(0, s - 1))}
            disabled={step === 0}
            data-testid="prev-step-btn"
          >
            <ChevronLeft className="h-4 w-4 mr-1" /> Back
          </Button>
          {step < STEPS.length - 1 && (
            <Button
              onClick={() => setStep((s) => s + 1)}
              disabled={!canGoNext()}
              data-testid="next-step-btn"
            >
              Next <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
