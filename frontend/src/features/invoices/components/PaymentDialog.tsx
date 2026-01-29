/**
 * PaymentDialog component.
 * Dialog for recording payments on invoices.
 */

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type { PaymentMethod, PaymentRecord } from '../types';

interface PaymentDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  remainingBalance: number;
  onSubmit: (data: PaymentRecord) => void;
  isLoading?: boolean;
}

const PAYMENT_METHODS: { value: PaymentMethod; label: string }[] = [
  { value: 'cash', label: 'Cash' },
  { value: 'check', label: 'Check' },
  { value: 'venmo', label: 'Venmo' },
  { value: 'zelle', label: 'Zelle' },
  { value: 'stripe', label: 'Stripe' },
];

export function PaymentDialog({
  open,
  onOpenChange,
  remainingBalance,
  onSubmit,
  isLoading = false,
}: PaymentDialogProps) {
  const [amount, setAmount] = useState(remainingBalance.toFixed(2));
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod | ''>('');
  const [reference, setReference] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = () => {
    setError('');

    const parsedAmount = parseFloat(amount);
    if (isNaN(parsedAmount) || parsedAmount <= 0) {
      setError('Please enter a valid amount greater than 0');
      return;
    }

    if (!paymentMethod) {
      setError('Please select a payment method');
      return;
    }

    onSubmit({
      amount: parsedAmount,
      payment_method: paymentMethod,
      payment_reference: reference || undefined,
    });
  };

  const handleOpenChange = (newOpen: boolean) => {
    if (!newOpen) {
      // Reset form when closing
      setAmount(remainingBalance.toFixed(2));
      setPaymentMethod('');
      setReference('');
      setError('');
    }
    onOpenChange(newOpen);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent data-testid="payment-dialog">
        <DialogHeader>
          <DialogTitle>Record Payment</DialogTitle>
          <DialogDescription>
            Enter the payment details for this invoice.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Amount input */}
          <div className="space-y-2">
            <Label htmlFor="payment-amount">Amount</Label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
                $
              </span>
              <Input
                id="payment-amount"
                type="number"
                step="0.01"
                min="0.01"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                className="pl-7"
                data-testid="payment-amount"
                disabled={isLoading}
              />
            </div>
            <p className="text-xs text-muted-foreground">
              Remaining balance: ${remainingBalance.toFixed(2)}
            </p>
          </div>

          {/* Payment method select */}
          <div className="space-y-2">
            <Label htmlFor="payment-method">Payment Method</Label>
            <Select
              value={paymentMethod}
              onValueChange={(value) => setPaymentMethod(value as PaymentMethod)}
              disabled={isLoading}
            >
              <SelectTrigger
                id="payment-method"
                className="w-full"
                data-testid="payment-method"
              >
                <SelectValue placeholder="Select payment method" />
              </SelectTrigger>
              <SelectContent>
                {PAYMENT_METHODS.map((method) => (
                  <SelectItem key={method.value} value={method.value}>
                    {method.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Reference input (optional) */}
          <div className="space-y-2">
            <Label htmlFor="payment-reference">
              Reference <span className="text-muted-foreground">(optional)</span>
            </Label>
            <Input
              id="payment-reference"
              type="text"
              value={reference}
              onChange={(e) => setReference(e.target.value)}
              placeholder="Check number, transaction ID, etc."
              data-testid="payment-reference"
              disabled={isLoading}
            />
          </div>

          {/* Error message */}
          {error && (
            <p className="text-sm text-destructive" data-testid="payment-error">
              {error}
            </p>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => handleOpenChange(false)}
            disabled={isLoading}
            data-testid="payment-cancel"
          >
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={isLoading}
            data-testid="submit-payment-btn"
          >
            {isLoading ? 'Recording...' : 'Record Payment'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
