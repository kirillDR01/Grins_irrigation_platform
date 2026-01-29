import { Link, useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  DollarSign,
  User,
  FileText,
  Send,
  CreditCard,
  Bell,
  AlertTriangle,
  Clock,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { LoadingPage, ErrorMessage } from '@/shared/components';
import { useInvoice } from '../hooks';
import {
  useSendInvoice,
  useSendReminder,
  useSendLienWarning,
  useMarkLienFiled,
} from '../hooks/useInvoiceMutations';
import { InvoiceStatusBadge } from './InvoiceStatusBadge';
import type { InvoiceLineItem } from '../types';

interface InvoiceDetailProps {
  invoiceId?: string;
  onEdit?: () => void;
  onRecordPayment?: () => void;
}

export function InvoiceDetail({
  invoiceId: propInvoiceId,
  onEdit,
  onRecordPayment,
}: InvoiceDetailProps) {
  const { id: paramId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const id = propInvoiceId || paramId || '';

  const { data: invoice, isLoading, error, refetch } = useInvoice(id);
  const sendInvoiceMutation = useSendInvoice();
  const sendReminderMutation = useSendReminder();
  const sendLienWarningMutation = useSendLienWarning();
  const markLienFiledMutation = useMarkLienFiled();

  const handleSendInvoice = async () => {
    if (!invoice) return;
    try {
      await sendInvoiceMutation.mutateAsync(invoice.id);
    } catch (err) {
      console.error('Failed to send invoice:', err);
    }
  };

  const handleSendReminder = async () => {
    if (!invoice) return;
    try {
      await sendReminderMutation.mutateAsync(invoice.id);
    } catch (err) {
      console.error('Failed to send reminder:', err);
    }
  };

  const handleSendLienWarning = async () => {
    if (!invoice) return;
    try {
      await sendLienWarningMutation.mutateAsync(invoice.id);
    } catch (err) {
      console.error('Failed to send lien warning:', err);
    }
  };

  const handleMarkLienFiled = async () => {
    if (!invoice) return;
    try {
      await markLienFiledMutation.mutateAsync({
        id: invoice.id,
        filingDate: new Date().toISOString().split('T')[0],
      });
    } catch (err) {
      console.error('Failed to mark lien filed:', err);
    }
  };

  if (isLoading) {
    return <LoadingPage message="Loading invoice details..." />;
  }

  if (error) {
    return <ErrorMessage error={error} onRetry={() => refetch()} />;
  }

  if (!invoice) {
    return <ErrorMessage error={new Error('Invoice not found')} />;
  }

  const formatCurrency = (amount: number | null | undefined) => {
    if (amount == null) return '-';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  };

  const formatDate = (date: string | null | undefined) => {
    if (!date) return '-';
    return new Date(date).toLocaleDateString();
  };

  const remainingBalance = invoice.total_amount - (invoice.paid_amount || 0);
  const canSend = invoice.status === 'draft';
  const canRecordPayment = ['sent', 'viewed', 'partial', 'overdue'].includes(invoice.status);
  const canSendReminder = ['sent', 'viewed', 'overdue'].includes(invoice.status);
  const canSendLienWarning = invoice.lien_eligible && !invoice.lien_warning_sent && invoice.status === 'overdue';
  const canMarkLienFiled = invoice.lien_eligible && invoice.lien_warning_sent && !invoice.lien_filed_date;

  return (
    <div data-testid="invoice-detail" className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate(-1)} aria-label="Go back">
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold" data-testid="invoice-number">
              {invoice.invoice_number}
            </h1>
            <p className="text-muted-foreground">Invoice Details</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <InvoiceStatusBadge status={invoice.status} />
          {onEdit && invoice.status === 'draft' && (
            <Button variant="outline" onClick={onEdit} data-testid="edit-invoice-btn">
              Edit Invoice
            </Button>
          )}
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Invoice Information */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Invoice Information
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-muted-foreground">Invoice Date</p>
                <p className="font-medium">{formatDate(invoice.invoice_date)}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Due Date</p>
                <p className="font-medium">{formatDate(invoice.due_date)}</p>
              </div>
            </div>

            <Separator />

            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-muted-foreground">Amount</p>
                <p className="text-lg font-semibold" data-testid="invoice-amount">
                  {formatCurrency(invoice.amount)}
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Late Fee</p>
                <p className="text-lg font-semibold">
                  {formatCurrency(invoice.late_fee_amount)}
                </p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-muted-foreground">Total Amount</p>
                <p className="text-xl font-bold text-primary">
                  {formatCurrency(invoice.total_amount)}
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Paid Amount</p>
                <p className="text-lg font-semibold text-green-600">
                  {formatCurrency(invoice.paid_amount)}
                </p>
              </div>
            </div>

            {remainingBalance > 0 && (
              <div className="rounded-lg bg-amber-50 p-3">
                <p className="text-sm text-amber-800">
                  Remaining Balance: <span className="font-bold">{formatCurrency(remainingBalance)}</span>
                </p>
              </div>
            )}

            {invoice.notes && (
              <>
                <Separator />
                <div>
                  <p className="text-sm text-muted-foreground">Notes</p>
                  <p className="mt-1">{invoice.notes}</p>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        {/* Customer & Job Information */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <User className="h-5 w-5" />
              Customer & Job
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="text-sm text-muted-foreground">Customer</p>
              {invoice.customer_name ? (
                <Link
                  to={`/customers/${invoice.customer_id}`}
                  className="flex items-center gap-2 text-primary hover:underline font-medium"
                >
                  <User className="h-4 w-4" />
                  {invoice.customer_name}
                </Link>
              ) : (
                <p className="text-muted-foreground">-</p>
              )}
            </div>

            {invoice.customer_phone && (
              <div>
                <p className="text-sm text-muted-foreground">Phone</p>
                <p>{invoice.customer_phone}</p>
              </div>
            )}

            {invoice.customer_email && (
              <div>
                <p className="text-sm text-muted-foreground">Email</p>
                <p>{invoice.customer_email}</p>
              </div>
            )}

            <Separator />

            <div>
              <p className="text-sm text-muted-foreground">Job</p>
              <Link
                to={`/jobs/${invoice.job_id}`}
                className="flex items-center gap-2 text-primary hover:underline"
              >
                <FileText className="h-4 w-4" />
                View Job Details
              </Link>
            </div>

            {invoice.job_description && (
              <div>
                <p className="text-sm text-muted-foreground">Job Description</p>
                <p className="mt-1">{invoice.job_description}</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Line Items */}
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <DollarSign className="h-5 w-5" />
              Line Items
            </CardTitle>
          </CardHeader>
          <CardContent>
            {invoice.line_items && invoice.line_items.length > 0 ? (
              <div className="overflow-x-auto" data-testid="invoice-line-items">
                <table className="w-full">
                  <thead>
                    <tr className="border-b">
                      <th className="py-2 text-left text-sm font-medium text-muted-foreground">Description</th>
                      <th className="py-2 text-right text-sm font-medium text-muted-foreground">Qty</th>
                      <th className="py-2 text-right text-sm font-medium text-muted-foreground">Unit Price</th>
                      <th className="py-2 text-right text-sm font-medium text-muted-foreground">Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {invoice.line_items.map((item: InvoiceLineItem, index: number) => (
                      <tr key={index} className="border-b last:border-0">
                        <td className="py-3">{item.description}</td>
                        <td className="py-3 text-right">{item.quantity}</td>
                        <td className="py-3 text-right">{formatCurrency(item.unit_price)}</td>
                        <td className="py-3 text-right font-medium">{formatCurrency(item.total)}</td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr className="border-t-2">
                      <td colSpan={3} className="py-3 text-right font-medium">Subtotal</td>
                      <td className="py-3 text-right font-bold">{formatCurrency(invoice.amount)}</td>
                    </tr>
                    {invoice.late_fee_amount > 0 && (
                      <tr>
                        <td colSpan={3} className="py-2 text-right text-sm text-muted-foreground">Late Fee</td>
                        <td className="py-2 text-right">{formatCurrency(invoice.late_fee_amount)}</td>
                      </tr>
                    )}
                    <tr>
                      <td colSpan={3} className="py-3 text-right text-lg font-bold">Total</td>
                      <td className="py-3 text-right text-lg font-bold text-primary">{formatCurrency(invoice.total_amount)}</td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            ) : (
              <p className="text-muted-foreground">No line items</p>
            )}
          </CardContent>
        </Card>

        {/* Payment Information */}
        {invoice.paid_at && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <CreditCard className="h-5 w-5" />
                Payment Information
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Payment Method</p>
                  <p className="font-medium capitalize">{invoice.payment_method || '-'}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Paid At</p>
                  <p className="font-medium">{formatDate(invoice.paid_at)}</p>
                </div>
              </div>
              {invoice.payment_reference && (
                <div>
                  <p className="text-sm text-muted-foreground">Reference</p>
                  <p>{invoice.payment_reference}</p>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Lien Information */}
        {invoice.lien_eligible && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-amber-500" />
                Lien Information
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="rounded-lg bg-amber-50 p-3">
                <p className="text-sm text-amber-800 font-medium">
                  This invoice is eligible for mechanic's lien
                </p>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Warning Sent</p>
                  <p className="font-medium">{formatDate(invoice.lien_warning_sent)}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Lien Filed</p>
                  <p className="font-medium">{formatDate(invoice.lien_filed_date)}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Reminder Information */}
        {invoice.reminder_count > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Bell className="h-5 w-5" />
                Reminders
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Reminders Sent</p>
                  <p className="font-medium">{invoice.reminder_count}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Last Reminder</p>
                  <p className="font-medium">{formatDate(invoice.last_reminder_sent)}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Actions */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="h-5 w-5" />
              Actions
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {canSend && (
              <Button
                className="w-full"
                onClick={handleSendInvoice}
                disabled={sendInvoiceMutation.isPending}
                data-testid="send-invoice-btn"
              >
                <Send className="mr-2 h-4 w-4" />
                Send Invoice
              </Button>
            )}
            {canRecordPayment && onRecordPayment && (
              <Button
                className="w-full"
                variant="outline"
                onClick={onRecordPayment}
                data-testid="record-payment-btn"
              >
                <CreditCard className="mr-2 h-4 w-4" />
                Record Payment
              </Button>
            )}
            {canSendReminder && (
              <Button
                className="w-full"
                variant="outline"
                onClick={handleSendReminder}
                disabled={sendReminderMutation.isPending}
                data-testid="send-reminder-btn"
              >
                <Bell className="mr-2 h-4 w-4" />
                Send Reminder
              </Button>
            )}
            {canSendLienWarning && (
              <Button
                className="w-full"
                variant="destructive"
                onClick={handleSendLienWarning}
                disabled={sendLienWarningMutation.isPending}
                data-testid="send-lien-warning-btn"
              >
                <AlertTriangle className="mr-2 h-4 w-4" />
                Send Lien Warning
              </Button>
            )}
            {canMarkLienFiled && (
              <Button
                className="w-full"
                variant="destructive"
                onClick={handleMarkLienFiled}
                disabled={markLienFiledMutation.isPending}
                data-testid="mark-lien-filed-btn"
              >
                <AlertTriangle className="mr-2 h-4 w-4" />
                Mark Lien Filed
              </Button>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
