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
    <div data-testid="invoice-detail" className="animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-4">
          <Button 
            variant="ghost" 
            size="icon" 
            onClick={() => navigate(-1)} 
            aria-label="Go back"
            className="hover:bg-slate-100 rounded-lg"
          >
            <ArrowLeft className="h-4 w-4 text-slate-600" />
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-slate-800" data-testid="invoice-number">
                {invoice.invoice_number}
              </h1>
              <InvoiceStatusBadge status={invoice.status} />
            </div>
            <p className="text-slate-500 mt-1">Invoice Details</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {/* Amount prominently displayed */}
          <div className="text-right mr-4">
            <p className="text-xs text-slate-400 uppercase tracking-wider">Total</p>
            <p className="text-3xl font-bold text-slate-800">{formatCurrency(invoice.total_amount)}</p>
          </div>
          {onEdit && invoice.status === 'draft' && (
            <Button variant="outline" onClick={onEdit} data-testid="edit-invoice-btn">
              Edit Invoice
            </Button>
          )}
        </div>
      </div>

      <div className="grid gap-8 grid-cols-1 lg:grid-cols-3">
        {/* Main Info Card - spans 2 columns */}
        <Card className="lg:col-span-2 bg-white rounded-2xl shadow-sm border border-slate-100 hover:shadow-md transition-shadow">
          <CardHeader className="p-6 border-b border-slate-100">
            <CardTitle className="flex items-center gap-2 font-bold text-slate-800 text-lg">
              <div className="p-2 rounded-lg bg-teal-50">
                <FileText className="h-5 w-5 text-teal-600" />
              </div>
              Invoice Information
            </CardTitle>
          </CardHeader>
          <CardContent className="p-6 space-y-6">
            {/* Dates Row */}
            <div className="grid grid-cols-2 gap-6">
              <div>
                <p className="text-xs text-slate-400 uppercase tracking-wider font-medium">Invoice Date</p>
                <p className="font-medium text-slate-700 mt-1">{formatDate(invoice.invoice_date)}</p>
              </div>
              <div>
                <p className="text-xs text-slate-400 uppercase tracking-wider font-medium">Due Date</p>
                <p className="font-medium text-slate-700 mt-1">{formatDate(invoice.due_date)}</p>
              </div>
            </div>

            <Separator className="bg-slate-100" />

            {/* Amounts Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
              <div className="bg-slate-50 rounded-xl p-4">
                <p className="text-xs text-slate-400 uppercase tracking-wider font-medium">Subtotal</p>
                <p className="text-lg font-semibold text-slate-800 mt-1" data-testid="invoice-amount">
                  {formatCurrency(invoice.amount)}
                </p>
              </div>
              <div className="bg-slate-50 rounded-xl p-4">
                <p className="text-xs text-slate-400 uppercase tracking-wider font-medium">Late Fee</p>
                <p className="text-lg font-semibold text-slate-800 mt-1">
                  {formatCurrency(invoice.late_fee_amount)}
                </p>
              </div>
              <div className="bg-teal-50 rounded-xl p-4 border border-teal-100">
                <p className="text-xs text-teal-600 uppercase tracking-wider font-medium">Total</p>
                <p className="text-xl font-bold text-teal-700 mt-1">
                  {formatCurrency(invoice.total_amount)}
                </p>
              </div>
              <div className="bg-emerald-50 rounded-xl p-4 border border-emerald-100">
                <p className="text-xs text-emerald-600 uppercase tracking-wider font-medium">Paid</p>
                <p className="text-lg font-semibold text-emerald-700 mt-1">
                  {formatCurrency(invoice.paid_amount)}
                </p>
              </div>
            </div>

            {remainingBalance > 0 && (
              <div className="rounded-xl bg-amber-50 p-4 border border-amber-100 flex items-center gap-3">
                <div className="p-2 rounded-full bg-amber-100">
                  <DollarSign className="h-4 w-4 text-amber-600" />
                </div>
                <div>
                  <p className="text-sm font-medium text-amber-800">
                    Remaining Balance
                  </p>
                  <p className="text-lg font-bold text-amber-700">{formatCurrency(remainingBalance)}</p>
                </div>
              </div>
            )}

            {invoice.notes && (
              <>
                <Separator className="bg-slate-100" />
                <div>
                  <p className="text-xs text-slate-400 uppercase tracking-wider font-medium mb-2">Notes</p>
                  <p className="text-slate-600 bg-slate-50 rounded-lg p-3">{invoice.notes}</p>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        {/* Customer & Job Information - Right column */}
        <Card className="bg-white rounded-2xl shadow-sm border border-slate-100 hover:shadow-md transition-shadow">
          <CardHeader className="p-6 border-b border-slate-100">
            <CardTitle className="flex items-center gap-2 font-bold text-slate-800 text-lg">
              <div className="p-2 rounded-lg bg-blue-50">
                <User className="h-5 w-5 text-blue-600" />
              </div>
              Customer & Job
            </CardTitle>
          </CardHeader>
          <CardContent className="p-6 space-y-4">
            <div>
              <p className="text-xs text-slate-400 uppercase tracking-wider font-medium mb-2">Customer</p>
              {invoice.customer_name ? (
                <Link
                  to={`/customers/${invoice.customer_id}`}
                  className="flex items-center gap-2 text-teal-600 hover:text-teal-700 font-medium transition-colors"
                >
                  <div className="w-8 h-8 rounded-full bg-teal-100 flex items-center justify-center">
                    <User className="h-4 w-4 text-teal-600" />
                  </div>
                  {invoice.customer_name}
                </Link>
              ) : (
                <p className="text-slate-400">-</p>
              )}
            </div>

            {invoice.customer_phone && (
              <div>
                <p className="text-xs text-slate-400 uppercase tracking-wider font-medium mb-1">Phone</p>
                <p className="text-slate-600">{invoice.customer_phone}</p>
              </div>
            )}

            {invoice.customer_email && (
              <div>
                <p className="text-xs text-slate-400 uppercase tracking-wider font-medium mb-1">Email</p>
                <p className="text-slate-600">{invoice.customer_email}</p>
              </div>
            )}

            <Separator className="bg-slate-100" />

            <div>
              <p className="text-xs text-slate-400 uppercase tracking-wider font-medium mb-2">Job</p>
              <Link
                to={`/jobs/${invoice.job_id}`}
                className="flex items-center gap-2 text-teal-600 hover:text-teal-700 font-medium transition-colors"
              >
                <FileText className="h-4 w-4" />
                View Job Details
              </Link>
            </div>

            {invoice.job_description && (
              <div>
                <p className="text-xs text-slate-400 uppercase tracking-wider font-medium mb-2">Job Description</p>
                <p className="text-slate-600 text-sm bg-slate-50 rounded-lg p-3">{invoice.job_description}</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Line Items - Full width */}
        <Card className="lg:col-span-3 bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden hover:shadow-md transition-shadow">
          <CardHeader className="p-6 border-b border-slate-100 bg-slate-50/50">
            <CardTitle className="flex items-center gap-2 font-bold text-slate-800 text-lg">
              <div className="p-2 rounded-lg bg-emerald-50">
                <DollarSign className="h-5 w-5 text-emerald-600" />
              </div>
              Line Items
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {invoice.line_items && invoice.line_items.length > 0 ? (
              <div className="overflow-x-auto" data-testid="invoice-line-items">
                <table className="w-full">
                  <thead>
                    <tr className="bg-slate-50/50">
                      <th className="px-6 py-4 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Description</th>
                      <th className="px-6 py-4 text-right text-xs font-medium text-slate-500 uppercase tracking-wider">Qty</th>
                      <th className="px-6 py-4 text-right text-xs font-medium text-slate-500 uppercase tracking-wider">Unit Price</th>
                      <th className="px-6 py-4 text-right text-xs font-medium text-slate-500 uppercase tracking-wider">Total</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-50">
                    {invoice.line_items.map((item: InvoiceLineItem, index: number) => (
                      <tr key={index} className="hover:bg-slate-50/80 transition-colors">
                        <td className="px-6 py-4 text-slate-700">{item.description}</td>
                        <td className="px-6 py-4 text-right text-slate-600">{item.quantity}</td>
                        <td className="px-6 py-4 text-right text-slate-600">{formatCurrency(item.unit_price)}</td>
                        <td className="px-6 py-4 text-right font-medium text-slate-800">{formatCurrency(item.total)}</td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot className="bg-slate-50/50">
                    <tr className="border-t-2 border-slate-100">
                      <td colSpan={3} className="px-6 py-4 text-right font-medium text-slate-600">Subtotal</td>
                      <td className="px-6 py-4 text-right font-bold text-slate-800">{formatCurrency(invoice.amount)}</td>
                    </tr>
                    {invoice.late_fee_amount > 0 && (
                      <tr>
                        <td colSpan={3} className="px-6 py-2 text-right text-sm text-slate-500">Late Fee</td>
                        <td className="px-6 py-2 text-right text-slate-600">{formatCurrency(invoice.late_fee_amount)}</td>
                      </tr>
                    )}
                    <tr className="bg-teal-50">
                      <td colSpan={3} className="px-6 py-4 text-right text-lg font-bold text-slate-800">Total</td>
                      <td className="px-6 py-4 text-right text-lg font-bold text-teal-700">{formatCurrency(invoice.total_amount)}</td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            ) : (
              <div className="p-6 text-center text-slate-400">No line items</div>
            )}
          </CardContent>
        </Card>

        {/* Payment Information */}
        {invoice.paid_at && (
          <Card className="bg-white rounded-2xl shadow-sm border border-slate-100 hover:shadow-md transition-shadow">
            <CardHeader className="p-6 border-b border-slate-100">
              <CardTitle className="flex items-center gap-2 font-bold text-slate-800 text-lg">
                <div className="p-2 rounded-lg bg-emerald-50">
                  <CreditCard className="h-5 w-5 text-emerald-600" />
                </div>
                Payment Information
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-slate-50 rounded-lg p-3">
                  <p className="text-xs text-slate-400 uppercase tracking-wider font-medium">Payment Method</p>
                  <p className="font-medium text-slate-700 capitalize mt-1">{invoice.payment_method || '-'}</p>
                </div>
                <div className="bg-slate-50 rounded-lg p-3">
                  <p className="text-xs text-slate-400 uppercase tracking-wider font-medium">Paid At</p>
                  <p className="font-medium text-slate-700 mt-1">{formatDate(invoice.paid_at)}</p>
                </div>
              </div>
              {invoice.payment_reference && (
                <div>
                  <p className="text-xs text-slate-400 uppercase tracking-wider font-medium mb-1">Reference</p>
                  <p className="text-slate-600 font-mono text-sm bg-slate-50 rounded-lg p-2">{invoice.payment_reference}</p>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Lien Information */}
        {invoice.lien_eligible && (
          <Card className="bg-white rounded-2xl shadow-sm border border-slate-100 hover:shadow-md transition-shadow">
            <CardHeader className="p-6 border-b border-slate-100">
              <CardTitle className="flex items-center gap-2 font-bold text-slate-800 text-lg">
                <div className="p-2 rounded-lg bg-amber-50">
                  <AlertTriangle className="h-5 w-5 text-amber-600" />
                </div>
                Lien Information
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-4">
              <div className="rounded-xl bg-amber-50 p-4 border border-amber-100">
                <p className="text-sm text-amber-800 font-medium flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4" />
                  This invoice is eligible for mechanic's lien
                </p>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-slate-50 rounded-lg p-3">
                  <p className="text-xs text-slate-400 uppercase tracking-wider font-medium">Warning Sent</p>
                  <p className="font-medium text-slate-700 mt-1">{formatDate(invoice.lien_warning_sent)}</p>
                </div>
                <div className="bg-slate-50 rounded-lg p-3">
                  <p className="text-xs text-slate-400 uppercase tracking-wider font-medium">Lien Filed</p>
                  <p className="font-medium text-slate-700 mt-1">{formatDate(invoice.lien_filed_date)}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Reminder Information */}
        {invoice.reminder_count > 0 && (
          <Card className="bg-white rounded-2xl shadow-sm border border-slate-100 hover:shadow-md transition-shadow">
            <CardHeader className="p-6 border-b border-slate-100">
              <CardTitle className="flex items-center gap-2 font-bold text-slate-800 text-lg">
                <div className="p-2 rounded-lg bg-violet-50">
                  <Bell className="h-5 w-5 text-violet-600" />
                </div>
                Reminders
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-slate-50 rounded-lg p-3">
                  <p className="text-xs text-slate-400 uppercase tracking-wider font-medium">Reminders Sent</p>
                  <p className="font-medium text-slate-700 mt-1">{invoice.reminder_count}</p>
                </div>
                <div className="bg-slate-50 rounded-lg p-3">
                  <p className="text-xs text-slate-400 uppercase tracking-wider font-medium">Last Reminder</p>
                  <p className="font-medium text-slate-700 mt-1">{formatDate(invoice.last_reminder_sent)}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Actions */}
        <Card className="bg-white rounded-2xl shadow-sm border border-slate-100 hover:shadow-md transition-shadow">
          <CardHeader className="p-6 border-b border-slate-100">
            <CardTitle className="flex items-center gap-2 font-bold text-slate-800 text-lg">
              <div className="p-2 rounded-lg bg-slate-100">
                <Clock className="h-5 w-5 text-slate-600" />
              </div>
              Actions
            </CardTitle>
          </CardHeader>
          <CardContent className="p-6 space-y-3">
            {canSend && (
              <Button
                className="w-full bg-teal-500 hover:bg-teal-600 text-white shadow-sm shadow-teal-200"
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
                className="w-full bg-red-500 hover:bg-red-600 text-white"
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
                className="w-full bg-red-500 hover:bg-red-600 text-white"
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
