import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ExternalLink, FileText } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useCustomerInvoices } from '../hooks';
import { invoiceStatusColors } from '../types';
import type { InvoiceStatus } from '../types';

interface InvoiceHistoryProps {
  customerId: string;
}

export function InvoiceHistory({ customerId }: InvoiceHistoryProps) {
  const [page, setPage] = useState(1);
  const pageSize = 10;
  const { data, isLoading, error } = useCustomerInvoices(customerId, {
    page,
    page_size: pageSize,
  });

  if (isLoading) {
    return (
      <div className="space-y-3" data-testid="invoices-loading">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-12 w-full rounded-lg" />
        ))}
      </div>
    );
  }

  if (error) {
    return <p className="text-red-600 text-sm" data-testid="invoices-error">Failed to load invoices.</p>;
  }

  const invoices = data?.items ?? [];
  const totalPages = data?.total_pages ?? 1;

  if (invoices.length === 0) {
    return (
      <div className="text-center py-8" data-testid="invoices-empty">
        <FileText className="h-10 w-10 text-slate-300 mx-auto mb-2" />
        <p className="text-sm text-slate-500">No invoices yet</p>
      </div>
    );
  }

  return (
    <div data-testid="invoice-history" className="space-y-4">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Invoice #</TableHead>
            <TableHead>Date</TableHead>
            <TableHead>Amount</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Due</TableHead>
            <TableHead className="text-right">Action</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {invoices.map((invoice) => (
            <TableRow key={invoice.id} data-testid={`invoice-row-${invoice.id}`}>
              <TableCell className="font-medium text-slate-800">
                {invoice.invoice_number}
              </TableCell>
              <TableCell className="text-slate-600">
                {new Date(invoice.date).toLocaleDateString()}
              </TableCell>
              <TableCell className="font-medium text-slate-800">
                ${invoice.total_amount.toLocaleString('en-US', { minimumFractionDigits: 2 })}
              </TableCell>
              <TableCell>
                <Badge
                  className={`${invoiceStatusColors[invoice.status as InvoiceStatus] || 'bg-slate-100 text-slate-700'} capitalize`}
                  data-testid={`invoice-status-${invoice.status}`}
                >
                  {invoice.status}
                </Badge>
              </TableCell>
              <TableCell>
                <DueBadge invoice={invoice} />
              </TableCell>
              <TableCell className="text-right">
                <Button variant="ghost" size="sm" asChild className="h-7 px-2">
                  <Link to={`/invoices/${invoice.id}`} data-testid={`view-invoice-${invoice.id}`}>
                    <ExternalLink className="h-3.5 w-3.5 mr-1" />
                    View
                  </Link>
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between" data-testid="invoice-pagination">
          <p className="text-xs text-slate-500">
            Page {page} of {totalPages} ({data?.total ?? 0} invoices)
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

function DueBadge({ invoice }: { invoice: { status: string; days_until_due: number | null; days_past_due: number | null } }) {
  if (invoice.status === 'paid' || invoice.status === 'cancelled' || invoice.status === 'void') {
    return <span className="text-xs text-slate-400">—</span>;
  }
  if (invoice.days_past_due != null && invoice.days_past_due > 0) {
    return (
      <span className="text-xs font-medium text-red-600" data-testid="days-past-due">
        {invoice.days_past_due}d overdue
      </span>
    );
  }
  if (invoice.days_until_due != null) {
    const color = invoice.days_until_due <= 7 ? 'text-amber-600' : 'text-slate-600';
    return (
      <span className={`text-xs font-medium ${color}`} data-testid="days-until-due">
        {invoice.days_until_due}d left
      </span>
    );
  }
  return <span className="text-xs text-slate-400">—</span>;
}
