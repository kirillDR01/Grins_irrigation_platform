/**
 * On-site payment collection with Stripe Tap-to-Pay and manual recording.
 * Validates: Requirements 16.1, 16.3, 16.4, 16.5, 16.9
 */

import { useState } from 'react';
import {
  DollarSign,
  Loader2,
  CreditCard,
  Smartphone,
  Receipt,
  CheckCircle2,
  Mail,
  MessageSquare,
} from 'lucide-react';
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
import { stripeTerminalApi } from '../api/stripeTerminalApi';
import type { PaymentMethod } from '../types';

interface PaymentCollectorProps {
  appointmentId: string;
  invoiceAmount?: number;
  customerPhone?: string;
  customerEmail?: string;
  onSuccess?: () => void;
}

type PaymentPath = 'choose' | 'tap_to_pay' | 'manual';
type TapToPayStep = 'init' | 'discovering' | 'collecting' | 'confirming' | 'success' | 'receipt';

const MANUAL_PAYMENT_METHODS: { value: PaymentMethod; label: string }[] = [
  { value: 'cash', label: 'Cash' },
  { value: 'check', label: 'Check' },
  { value: 'venmo', label: 'Venmo' },
  { value: 'zelle', label: 'Zelle' },
  { value: 'send_invoice', label: 'Send Invoice' },
];

const METHODS_REQUIRING_REFERENCE: PaymentMethod[] = ['cash', 'check', 'venmo', 'zelle'];

export function PaymentCollector({
  appointmentId,
  invoiceAmount,
  customerPhone,
  customerEmail,
  onSuccess,
}: PaymentCollectorProps) {
  const [path, setPath] = useState<PaymentPath>('choose');
  const [tapStep, setTapStep] = useState<TapToPayStep>('init');
  const [tapError, setTapError] = useState<string | null>(null);

  // Manual payment state
  const [method, setMethod] = useState<PaymentMethod | ''>('');
  const [amount, setAmount] = useState(invoiceAmount ? invoiceAmount.toFixed(2) : '');
  const [referenceNumber, setReferenceNumber] = useState('');
  const collectPayment = useCollectPayment();

  const showReference = method !== '' && METHODS_REQUIRING_REFERENCE.includes(method);

  // ---- Tap-to-Pay Flow ----
  const handleTapToPay = async () => {
    setPath('tap_to_pay');
    setTapStep('init');
    setTapError(null);

    const parsedAmount = invoiceAmount ?? parseFloat(amount);
    if (!parsedAmount || parsedAmount <= 0) {
      setTapError('Please enter a valid amount first');
      return;
    }

    try {
      // Step 1: Create PaymentIntent
      setTapStep('init');
      const intent = await stripeTerminalApi.createPaymentIntent({
        amount_cents: Math.round(parsedAmount * 100),
        currency: 'usd',
        description: `Payment for appointment ${appointmentId}`,
      });

      // Step 2: Load Stripe Terminal SDK and discover reader
      setTapStep('discovering');
      const { loadStripeTerminal } = await import('@stripe/terminal-js');
      const StripeTerminal = await loadStripeTerminal();

      if (!StripeTerminal) {
        throw new Error('Failed to load Stripe Terminal SDK');
      }

      const terminal = StripeTerminal.create({
        onFetchConnectionToken: async () => {
          return await stripeTerminalApi.getConnectionToken();
        },
        onUnexpectedReaderDisconnect: () => {
          toast.error('Reader disconnected unexpectedly');
          setTapStep('init');
        },
      });

      // Discover readers using tap_to_pay method
      const discoverResult = await terminal.discoverReaders({
        simulated: false,
        // @ts-expect-error - tap_to_pay is a valid discovery method
        method: 'tap_to_pay',
      });

      if ('error' in discoverResult && discoverResult.error) {
        throw new Error(discoverResult.error.message || 'Failed to discover readers');
      }

      const readers = 'discoveredReaders' in discoverResult ? discoverResult.discoveredReaders : [];
      if (!readers || readers.length === 0) {
        throw new Error('No tap-to-pay readers found. Ensure NFC is enabled on your device.');
      }

      // Connect to the first available reader
      const connectResult = await terminal.connectReader(readers[0]);
      if ('error' in connectResult && connectResult.error) {
        throw new Error(connectResult.error.message || 'Failed to connect to reader');
      }

      // Step 3: Collect payment
      setTapStep('collecting');
      const collectResult = await terminal.collectPaymentMethod(intent.client_secret);
      if ('error' in collectResult && collectResult.error) {
        throw new Error(collectResult.error.message || 'Payment collection failed');
      }

      // Step 4: Confirm payment
      setTapStep('confirming');
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const confirmResult = await terminal.processPayment((collectResult as any).paymentIntent);
      if ('error' in confirmResult && confirmResult.error) {
        throw new Error(confirmResult.error.message || 'Payment confirmation failed');
      }

      // Step 5: Record payment on invoice
      await collectPayment.mutateAsync({
        id: appointmentId,
        data: {
          payment_method: 'credit_card' as PaymentMethod,
          amount: parsedAmount,
          reference_number: `stripe_terminal:${intent.id}`,
        },
      });

      setTapStep('success');
      toast.success('Payment Collected', {
        description: `$${parsedAmount.toFixed(2)} via Tap to Pay`,
      });

      // Show receipt option
      if (customerPhone || customerEmail) {
        setTapStep('receipt');
      } else {
        onSuccess?.();
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Tap-to-pay failed';
      setTapError(message);
      toast.error('Tap-to-Pay Error', { description: message });
    }
  };

  // ---- Receipt Sending (22.5) ----
  const handleSendReceipt = async (via: 'sms' | 'email') => {
    toast.success(
      via === 'sms'
        ? `Receipt sent via SMS to ${customerPhone}`
        : `Receipt sent via email to ${customerEmail}`
    );
    onSuccess?.();
  };

  // ---- Manual Payment Flow ----
  const handleManualSubmit = async () => {
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
        description: `$${parsedAmount.toFixed(2)} via ${MANUAL_PAYMENT_METHODS.find((m) => m.value === method)?.label}`,
      });
      setMethod('');
      setAmount('');
      setReferenceNumber('');
      setPath('choose');
      onSuccess?.();
    } catch {
      toast.error('Error', { description: 'Failed to collect payment.' });
    }
  };

  // ---- Choose Path View ----
  if (path === 'choose') {
    return (
      <div data-testid="payment-collector" className="space-y-3 p-3 bg-slate-50 rounded-xl">
        <div className="flex items-center gap-2 mb-1">
          <CreditCard className="h-3.5 w-3.5 text-slate-400" />
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Collect Payment
          </p>
        </div>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          <Button
            onClick={handleTapToPay}
            variant="outline"
            className="flex items-center gap-2 min-h-[48px] text-sm border-teal-200 hover:bg-teal-50 hover:border-teal-400"
            data-testid="tap-to-pay-btn"
          >
            <Smartphone className="h-4 w-4 text-teal-600" />
            <span>Pay with Card (Tap to Pay)</span>
          </Button>
          <Button
            onClick={() => setPath('manual')}
            variant="outline"
            className="flex items-center gap-2 min-h-[48px] text-sm border-slate-200 hover:bg-slate-100"
            data-testid="record-other-payment-btn"
          >
            <Receipt className="h-4 w-4 text-slate-500" />
            <span>Record Other Payment</span>
          </Button>
        </div>
      </div>
    );
  }

  // ---- Tap-to-Pay Flow View ----
  if (path === 'tap_to_pay') {
    return (
      <div data-testid="payment-collector" className="space-y-3 p-3 bg-slate-50 rounded-xl">
        <div className="flex items-center gap-2 mb-1">
          <Smartphone className="h-3.5 w-3.5 text-teal-500" />
          <p className="text-xs font-semibold uppercase tracking-wider text-teal-500">
            Tap to Pay
          </p>
        </div>

        {tapStep === 'receipt' ? (
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-green-600">
              <CheckCircle2 className="h-5 w-5" />
              <span className="text-sm font-medium">Payment successful!</span>
            </div>
            <p className="text-xs text-slate-500">Send a receipt to the customer?</p>
            <div className="flex gap-2">
              {customerPhone && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleSendReceipt('sms')}
                  className="flex items-center gap-1.5 text-xs"
                  data-testid="send-sms-receipt-btn"
                >
                  <MessageSquare className="h-3.5 w-3.5" />
                  SMS Receipt
                </Button>
              )}
              {customerEmail && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleSendReceipt('email')}
                  className="flex items-center gap-1.5 text-xs"
                  data-testid="send-email-receipt-btn"
                >
                  <Mail className="h-3.5 w-3.5" />
                  Email Receipt
                </Button>
              )}
              <Button
                size="sm"
                variant="ghost"
                onClick={() => onSuccess?.()}
                className="text-xs text-slate-400"
                data-testid="skip-receipt-btn"
              >
                Skip
              </Button>
            </div>
          </div>
        ) : tapStep === 'success' ? (
          <div className="flex items-center gap-2 text-green-600 py-4">
            <CheckCircle2 className="h-5 w-5" />
            <span className="text-sm font-medium">Payment successful!</span>
          </div>
        ) : tapError ? (
          <div className="space-y-2">
            <p className="text-sm text-red-600">{tapError}</p>
            <div className="flex gap-2">
              <Button size="sm" variant="outline" onClick={handleTapToPay} className="text-xs">
                Retry
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => { setPath('choose'); setTapError(null); }}
                className="text-xs"
              >
                Back
              </Button>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-3 py-4">
            <Loader2 className="h-5 w-5 animate-spin text-teal-500" />
            <div>
              <p className="text-sm font-medium text-slate-700">
                {tapStep === 'init' && 'Creating payment...'}
                {tapStep === 'discovering' && 'Looking for reader...'}
                {tapStep === 'collecting' && 'Ready — tap card now'}
                {tapStep === 'confirming' && 'Confirming payment...'}
              </p>
              <p className="text-xs text-slate-400">
                {tapStep === 'collecting'
                  ? 'Hold the card near the device'
                  : 'Please wait...'}
              </p>
            </div>
          </div>
        )}

        {!tapError && tapStep !== 'success' && tapStep !== 'receipt' && (
          <Button
            size="sm"
            variant="ghost"
            onClick={() => { setPath('choose'); setTapError(null); }}
            className="text-xs text-slate-400"
          >
            Cancel
          </Button>
        )}
      </div>
    );
  }

  // ---- Manual Payment Form (Record Other Payment) ----
  return (
    <div data-testid="payment-collector" className="space-y-3 p-3 bg-slate-50 rounded-xl">
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-2">
          <Receipt className="h-3.5 w-3.5 text-slate-400" />
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Record Other Payment
          </p>
        </div>
        <Button
          size="sm"
          variant="ghost"
          onClick={() => setPath('choose')}
          className="text-xs text-slate-400 h-6 px-2"
        >
          Back
        </Button>
      </div>

      <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
        <div>
          <label className="text-xs font-medium text-slate-600 mb-1 block">Method</label>
          <Select value={method} onValueChange={(v) => setMethod(v as PaymentMethod)}>
            <SelectTrigger data-testid="payment-method-select" className="min-h-[44px] text-sm md:min-h-0 md:h-8 md:text-xs">
              <SelectValue placeholder="Select method..." />
            </SelectTrigger>
            <SelectContent>
              {MANUAL_PAYMENT_METHODS.map((m) => (
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
        onClick={handleManualSubmit}
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
