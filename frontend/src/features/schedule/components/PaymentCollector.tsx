/**
 * On-site payment collection form (Req 30).
 * Supports Credit Card, Cash, Check, Venmo, Zelle, Send Invoice.
 */

import { useState } from 'react';
import { DollarSign, Loader2, CreditCard } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useCollectPayment } from '../hooks/useAppointmentMutations';
import type { PaymentMethod } from '../types';

interface PaymentCollectorProps {
  appointmentId: string;
  onSuccess?: () => void;
}

const PAYMENT_METHODS: { value: PaymentMethod; label: string }[] = [
  { value: 'credit_card', label: 'Credit Card' },
  { value: 'cash', label: 'Cash' },
  { value: 'check', label: 'Check' },
  { value: 'venmo', label: 'Venmo' },
  { value: 'zelle', label: 'Zelle' },
  { value: 'send_invoice', label: 'Send Invoice' },
];

const METHODS_REQUIRING_REFERENCE: PaymentMethod[] = ['cash', 'check', 'venmo', 'zelle'];

export function PaymentCollector({ appointmentId, onSuccess }: PaymentCollectorProps) {
  const [method, setMethod] = useState<PaymentMethod | ''>('');
  const [amount, setAmount] = useState('');
  const [referenceNumber, setReferenceNumber] = useState('');
  const collectPayment = useCollectPayment();

  const showReference = method !== '' && METHODS_REQUIRING_REFERENCE.includes(method);

  const handleSubmit = async () => {
    if (!method) {
      toast.error('Please select a payment method');
      return;
    }
    const parsedAmount = parseFloat(amount);
    if (isNaN(parsedAmount) || parsedAmount <= 0) {
      toast.error('Please enter a valid amount');
      return;
    }
    try {
      await collectPayment.mutateAsync({
        id: appointmentId,
        data: {
          payment_method: method,
          amount: parsedAmount,
          reference_number: referenceNumber || undefined,
        },
      });
      toast.success('Payment Collected', {
        description: `$${parsedAmount.toFixed(2)} via ${PAYMENT_METHODS.find((m) => m.value === method)?.label}`,
      });
      setMethod('');
      setAmount('');
      setReferenceNumber('');
      onSuccess?.();
    } catch {
      toast.error('Error', { description: 'Failed to collect payment.' });
    }
  };

  return (
    <div data-testid="payment-collector" className="space-y-3 p-3 bg-slate-50 rounded-xl">
      <div className="flex items-center gap-2 mb-1">
        <CreditCard className="h-3.5 w-3.5 text-slate-400" />
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          Collect Payment
        </p>
      </div>

      <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
        <div>
          <label className="text-xs font-medium text-slate-600 mb-1 block">Method</label>
          <Select
            value={method}
            onValueChange={(v) => setMethod(v as PaymentMethod)}
          >
            <SelectTrigger data-testid="payment-method-select" className="min-h-[44px] text-sm md:min-h-0 md:h-8 md:text-xs">
              <SelectValue placeholder="Select method..." />
            </SelectTrigger>
            <SelectContent>
              {PAYMENT_METHODS.map((m) => (
                <SelectItem key={m.value} value={m.value}>
                  {m.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div>
          <label className="text-xs font-medium text-slate-600 mb-1 block">Amount</label>
          <div className="relative">
            <DollarSign className="absolute left-2 top-1/2 -translate-y-1/2 h-3 w-3 text-slate-400" />
            <Input
              type="number"
              step="0.01"
              min="0"
              placeholder="0.00"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className="pl-6 min-h-[44px] text-sm md:min-h-0 md:h-8 md:text-xs"
              data-testid="payment-amount-input"
            />
          </div>
        </div>
      </div>

      {showReference && (
        <div>
          <label className="text-xs font-medium text-slate-600 mb-1 block">
            Reference Number
          </label>
          <Input
            placeholder="Check #, transaction ID, etc."
            value={referenceNumber}
            onChange={(e) => setReferenceNumber(e.target.value)}
            className="min-h-[44px] text-sm md:min-h-0 md:h-8 md:text-xs"
            data-testid="payment-reference-input"
          />
        </div>
      )}

      <Button
        onClick={handleSubmit}
        disabled={collectPayment.isPending || !method || !amount}
        size="sm"
        className="w-full bg-teal-500 hover:bg-teal-600 text-white min-h-[48px] text-sm md:min-h-0 md:h-8 md:text-xs"
        data-testid="collect-payment-btn"
      >
        {collectPayment.isPending ? (
          <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
        ) : (
          <DollarSign className="mr-1.5 h-3.5 w-3.5" />
        )}
        Collect Payment
      </Button>
    </div>
  );
}
