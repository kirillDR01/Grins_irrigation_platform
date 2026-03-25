import { useState } from 'react';
import { CreditCard, Zap } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { useCustomerPaymentMethods, useChargeCustomer } from '../hooks';
import { toast } from 'sonner';

const brandIcons: Record<string, string> = {
  visa: '💳 Visa',
  mastercard: '💳 Mastercard',
  amex: '💳 Amex',
  discover: '💳 Discover',
};

interface PaymentMethodsProps {
  customerId: string;
}

export function PaymentMethods({ customerId }: PaymentMethodsProps) {
  const { data: methods, isLoading, error } = useCustomerPaymentMethods(customerId);
  const chargeMutation = useChargeCustomer(customerId);

  const [chargeDialogOpen, setChargeDialogOpen] = useState(false);
  const [selectedMethodId, setSelectedMethodId] = useState<string | null>(null);
  const [chargeAmount, setChargeAmount] = useState('');
  const [chargeDescription, setChargeDescription] = useState('');

  const handleCharge = async () => {
    if (!selectedMethodId) return;
    const amount = parseFloat(chargeAmount);
    if (isNaN(amount) || amount <= 0) {
      toast.error('Enter a valid amount');
      return;
    }
    if (!chargeDescription.trim()) {
      toast.error('Enter a description');
      return;
    }
    try {
      await chargeMutation.mutateAsync({
        payment_method_id: selectedMethodId,
        amount,
        description: chargeDescription.trim(),
      });
      toast.success(`Charged $${amount.toFixed(2)} successfully`);
      setChargeDialogOpen(false);
      setChargeAmount('');
      setChargeDescription('');
      setSelectedMethodId(null);
    } catch {
      toast.error('Failed to process charge');
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-3" data-testid="payment-methods-loading">
        {Array.from({ length: 2 }).map((_, i) => (
          <Skeleton key={i} className="h-16 w-full rounded-lg" />
        ))}
      </div>
    );
  }

  if (error) {
    return <p className="text-red-600 text-sm" data-testid="payment-methods-error">Failed to load payment methods.</p>;
  }

  if (!methods || methods.length === 0) {
    return (
      <div className="text-center py-8" data-testid="payment-methods-empty">
        <CreditCard className="h-10 w-10 text-slate-300 mx-auto mb-2" />
        <p className="text-sm text-slate-500">No saved payment methods</p>
        <p className="text-xs text-slate-400 mt-1">Payment methods are added via Stripe checkout</p>
      </div>
    );
  }

  return (
    <div data-testid="payment-methods" className="space-y-3">
      {methods.map((method) => (
        <div
          key={method.id}
          className="flex items-center justify-between p-4 rounded-lg border border-slate-100 bg-white"
          data-testid={`payment-method-${method.id}`}
        >
          <div className="flex items-center gap-3">
            <div className="p-2 bg-slate-100 rounded-lg">
              <CreditCard className="h-5 w-5 text-slate-600" />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-800">
                {brandIcons[method.brand.toLowerCase()] || `💳 ${method.brand}`} •••• {method.last4}
              </p>
              <p className="text-xs text-slate-400">
                Expires {String(method.exp_month).padStart(2, '0')}/{method.exp_year}
              </p>
            </div>
            {method.is_default && (
              <Badge variant="teal" className="text-xs">Default</Badge>
            )}
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              setSelectedMethodId(method.id);
              setChargeDialogOpen(true);
            }}
            data-testid={`charge-btn-${method.id}`}
          >
            <Zap className="h-3.5 w-3.5 mr-1" />
            Charge
          </Button>
        </div>
      ))}

      {/* Charge dialog */}
      <Dialog open={chargeDialogOpen} onOpenChange={setChargeDialogOpen}>
        <DialogContent data-testid="charge-dialog">
          <DialogHeader>
            <DialogTitle>Charge Payment Method</DialogTitle>
            <DialogDescription>
              Enter the amount and description for this charge.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="charge-amount">Amount ($)</Label>
              <Input
                id="charge-amount"
                type="number"
                min="0.01"
                step="0.01"
                value={chargeAmount}
                onChange={(e) => setChargeAmount(e.target.value)}
                placeholder="0.00"
                data-testid="charge-amount-input"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="charge-description">Description</Label>
              <Input
                id="charge-description"
                value={chargeDescription}
                onChange={(e) => setChargeDescription(e.target.value)}
                placeholder="e.g., Spring system startup"
                data-testid="charge-description-input"
              />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setChargeDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleCharge}
              disabled={chargeMutation.isPending}
              data-testid="confirm-charge-btn"
            >
              {chargeMutation.isPending ? 'Processing...' : 'Charge'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
