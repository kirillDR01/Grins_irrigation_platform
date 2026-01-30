/**
 * PaymentDialog component.
 * Dialog for recording payments on invoices.
 */

import { useState } from 'react';
import { format } from 'date-fns';
import { CalendarIcon, DollarSign } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Calendar } from '@/components/ui/calendar';
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
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';
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
  { value: 'stripe', label: 'Credit Card (Stripe)' },
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
  const [paymentDate, setPaymentDate] = useState<Date>(new Date());
  const [reference, setReference] = useState('');
  const [notes, setNotes] = useState('');
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
      setPaymentDate(new Date());
      setReference('');
      setNotes('');
      setError('');
    }
    onOpenChange(newOpen);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent
        className="sm:max-w-md"
        data-testid="payment-dialog"
      >
        <DialogHeader className="p-6 border-b border-slate-100 bg-slate-50/50 -m-6 mb-0">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-full bg-teal-100">
              <DollarSign className="h-5 w-5 text-teal-600" />
            </div>
            <div>
              <DialogTitle className="text-lg font-bold text-slate-800">
                Record Payment
              </DialogTitle>
              <DialogDescription className="text-sm text-slate-500">
                Enter the payment details for this invoice.
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-4 py-6">
          {/* Amount input */}
          <div className="space-y-2">
            <Label htmlFor="payment-amount" className="text-sm font-medium text-slate-700">
              Amount
            </Label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm font-medium">
                $
              </span>
              <Input
                id="payment-amount"
                type="number"
                step="0.01"
                min="0.01"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                className="pl-7 border-slate-200 rounded-lg bg-white text-slate-700 text-sm placeholder-slate-400 focus:border-teal-500 focus:ring-2 focus:ring-teal-100"
                data-testid="payment-amount"
                disabled={isLoading}
              />
            </div>
            <p className="text-xs text-slate-400">
              Remaining balance: ${remainingBalance.toFixed(2)}
            </p>
          </div>

          {/* Payment method select */}
          <div className="space-y-2">
            <Label htmlFor="payment-method" className="text-sm font-medium text-slate-700">
              Payment Method
            </Label>
            <Select
              value={paymentMethod}
              onValueChange={(value) => setPaymentMethod(value as PaymentMethod)}
              disabled={isLoading}
            >
              <SelectTrigger
                id="payment-method"
                className="w-full border-slate-200 rounded-lg bg-white text-slate-700 text-sm focus:border-teal-500 focus:ring-2 focus:ring-teal-100"
                data-testid="payment-method"
              >
                <SelectValue placeholder="Select payment method" />
              </SelectTrigger>
              <SelectContent
                className="bg-white rounded-lg shadow-lg border border-slate-100"
                data-testid="payment-method-options"
              >
                {PAYMENT_METHODS.map((method) => (
                  <SelectItem
                    key={method.value}
                    value={method.value}
                    className="hover:bg-slate-50 text-slate-700 focus:bg-teal-50 focus:text-teal-700"
                  >
                    {method.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Payment date picker */}
          <div className="space-y-2">
            <Label className="text-sm font-medium text-slate-700">
              Payment Date
            </Label>
            <Popover>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  className={cn(
                    'w-full justify-start text-left font-normal border-slate-200 rounded-lg bg-white text-slate-700 text-sm hover:bg-slate-50 focus:border-teal-500 focus:ring-2 focus:ring-teal-100',
                    !paymentDate && 'text-slate-400'
                  )}
                  disabled={isLoading}
                  data-testid="payment-date-picker"
                >
                  <CalendarIcon className="mr-2 h-4 w-4 text-slate-400" />
                  {paymentDate ? format(paymentDate, 'PPP') : 'Select date'}
                </Button>
              </PopoverTrigger>
              <PopoverContent
                className="w-auto p-0 bg-white rounded-xl shadow-lg border border-slate-100"
                align="start"
                data-testid="payment-date-calendar"
              >
                <Calendar
                  mode="single"
                  selected={paymentDate}
                  onSelect={(date) => date && setPaymentDate(date)}
                  initialFocus
                />
              </PopoverContent>
            </Popover>
          </div>

          {/* Reference input (optional) */}
          <div className="space-y-2">
            <Label htmlFor="payment-reference" className="text-sm font-medium text-slate-700">
              Reference <span className="text-slate-400 font-normal">(optional)</span>
            </Label>
            <Input
              id="payment-reference"
              type="text"
              value={reference}
              onChange={(e) => setReference(e.target.value)}
              placeholder="Check number, transaction ID, etc."
              className="border-slate-200 rounded-lg bg-white text-slate-700 text-sm placeholder-slate-400 focus:border-teal-500 focus:ring-2 focus:ring-teal-100"
              data-testid="payment-reference"
              disabled={isLoading}
            />
          </div>

          {/* Notes textarea (optional) */}
          <div className="space-y-2">
            <Label htmlFor="payment-notes" className="text-sm font-medium text-slate-700">
              Notes <span className="text-slate-400 font-normal">(optional)</span>
            </Label>
            <Textarea
              id="payment-notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Add any additional notes about this payment..."
              className="border-slate-200 rounded-xl bg-white text-slate-700 text-sm placeholder-slate-400 focus:border-teal-500 focus:ring-2 focus:ring-teal-100 min-h-[80px] resize-none"
              data-testid="payment-notes"
              disabled={isLoading}
            />
          </div>

          {/* Error message */}
          {error && (
            <p className="text-sm text-red-500" data-testid="payment-error">
              {error}
            </p>
          )}
        </div>

        <DialogFooter className="p-6 border-t border-slate-100 bg-slate-50/50 -m-6 mt-0 gap-3">
          <Button
            variant="outline"
            onClick={() => handleOpenChange(false)}
            disabled={isLoading}
            className="bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 px-4 py-2.5 rounded-lg transition-all"
            data-testid="payment-cancel"
          >
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={isLoading}
            className="bg-teal-500 hover:bg-teal-600 text-white px-5 py-2.5 rounded-lg shadow-sm shadow-teal-200 transition-all"
            data-testid="submit-payment-btn"
          >
            {isLoading ? 'Recording...' : 'Record Payment'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
