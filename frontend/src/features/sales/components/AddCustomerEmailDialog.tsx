import { useState } from 'react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { useUpdateCustomer } from '@/features/customers';
import { getErrorMessage } from '@/core/api';

interface AddCustomerEmailDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  customerId: string;
  onSaved?: () => void;
}

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function AddCustomerEmailDialog({
  open,
  onOpenChange,
  customerId,
  onSaved,
}: AddCustomerEmailDialogProps) {
  const [email, setEmail] = useState('');
  const updateCustomer = useUpdateCustomer();

  const trimmed = email.trim();
  const isValid = EMAIL_RE.test(trimmed);

  const handleSubmit = async () => {
    if (!isValid || !customerId) return;
    try {
      await updateCustomer.mutateAsync({
        id: customerId,
        data: { email: trimmed },
      });
      toast.success('Email saved');
      setEmail('');
      onOpenChange(false);
      onSaved?.();
    } catch (err) {
      toast.error('Failed to save email', {
        description: getErrorMessage(err),
      });
    }
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        if (!o) setEmail('');
        onOpenChange(o);
      }}
    >
      <DialogContent data-testid="add-customer-email-dialog">
        <DialogHeader>
          <DialogTitle>Add Customer Email</DialogTitle>
          <DialogDescription>
            Adding an email unlocks email-based estimate sending and signing
            flows for this customer.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-2">
          <Label htmlFor="customer-email-input">Email address</Label>
          <Input
            id="customer-email-input"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="customer@example.com"
            data-testid="customer-email-input"
            autoComplete="email"
          />
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            data-testid="cancel-add-email-btn"
            onClick={() => onOpenChange(false)}
            disabled={updateCustomer.isPending}
          >
            Cancel
          </Button>
          <Button
            data-testid="confirm-add-email-btn"
            onClick={handleSubmit}
            disabled={!isValid || updateCustomer.isPending}
          >
            {updateCustomer.isPending ? 'Saving…' : 'Save Email'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
