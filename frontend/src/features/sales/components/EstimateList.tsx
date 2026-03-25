/**
 * Filtered estimate list for pipeline views (Req 83).
 * Linked from SalesDashboard pipeline cards and FollowUpQueue rows.
 */

import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { LoadingSpinner, ErrorMessage } from '@/shared/components';
import { FileText } from 'lucide-react';
import { useEstimates } from '../hooks';
import { ESTIMATE_STATUS_CONFIG } from '../types';
import type { EstimateStatus, EstimateListItem } from '../types';

interface EstimateListProps {
  /** Pre-filter by status or pipeline category */
  initialFilter?: string;
}

const FILTER_OPTIONS = [
  { value: 'all', label: 'All Estimates' },
  { value: 'draft', label: 'Draft' },
  { value: 'sent', label: 'Sent' },
  { value: 'viewed', label: 'Viewed' },
  { value: 'approved', label: 'Approved' },
  { value: 'rejected', label: 'Rejected' },
  { value: 'needs_followup', label: 'Needs Follow-Up' },
];

function EstimateStatusBadge({ status }: { status: string }) {
  const config = ESTIMATE_STATUS_CONFIG[status as EstimateStatus] ?? ESTIMATE_STATUS_CONFIG.draft;
  return (
    <Badge className={`${config.className} border-0 text-xs font-medium`}>
      {config.label}
    </Badge>
  );
}

function formatCurrency(amount: number): string {
  return `$${amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function EstimateList({ initialFilter }: EstimateListProps) {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const urlFilter = searchParams.get('filter') ?? initialFilter ?? 'all';
  const [statusFilter, setStatusFilter] = useState(urlFilter);

  const params: Record<string, string> = {};
  if (statusFilter && statusFilter !== 'all') {
    if (statusFilter === 'needs_followup') {
      params.needs_followup = 'true';
    } else {
      params.status = statusFilter;
    }
  }

  const { data, isLoading, error } = useEstimates(params);
  const items: EstimateListItem[] = data?.items ?? [];

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorMessage error={error} />;

  return (
    <Card data-testid="estimate-list">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-teal-500" />
            <CardTitle className="text-lg">Estimates</CardTitle>
            <Badge variant="secondary" className="ml-1">{items.length}</Badge>
          </div>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[180px]" data-testid="estimate-filter-select">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {FILTER_OPTIONS.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </CardHeader>
      <CardContent>
        {items.length === 0 ? (
          <p className="text-center text-sm text-slate-400 py-8" data-testid="estimate-list-empty">
            No estimates found.
          </p>
        ) : (
          <Table data-testid="estimate-table">
            <TableHeader>
              <TableRow>
                <TableHead>Estimate #</TableHead>
                <TableHead>Customer</TableHead>
                <TableHead className="text-right">Total</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Days Since Sent</TableHead>
                <TableHead>Next Follow-Up</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((item) => (
                <TableRow
                  key={item.id}
                  className="cursor-pointer hover:bg-slate-50"
                  onClick={() => navigate(`/estimates/${item.id}`)}
                  data-testid={`estimate-row-${item.id}`}
                >
                  <TableCell className="font-medium text-blue-600">
                    {item.id.slice(0, 8).toUpperCase()}
                  </TableCell>
                  <TableCell>{item.customer_name}</TableCell>
                  <TableCell className="text-right">{formatCurrency(item.total)}</TableCell>
                  <TableCell>
                    <EstimateStatusBadge status={item.status} />
                  </TableCell>
                  <TableCell className="text-right">
                    <span className={item.days_since_sent > 14 ? 'text-red-500 font-medium' : ''}>
                      {item.days_since_sent > 0 ? `${item.days_since_sent}d` : '—'}
                    </span>
                  </TableCell>
                  <TableCell>
                    {item.next_follow_up
                      ? new Date(item.next_follow_up).toLocaleDateString()
                      : '—'}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
