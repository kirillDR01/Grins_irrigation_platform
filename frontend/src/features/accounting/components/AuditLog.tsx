import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { LoadingSpinner } from '@/shared/components';
import { Shield, ChevronLeft, ChevronRight } from 'lucide-react';
import { useAuditLog } from '../hooks';
import type { AuditLogParams } from '../types';

const ACTION_COLORS: Record<string, string> = {
  'customer.merge': 'bg-blue-100 text-blue-700',
  'customer.delete': 'bg-red-100 text-red-700',
  'invoice.bulk_notify': 'bg-amber-100 text-amber-700',
  'staff.create': 'bg-emerald-100 text-emerald-700',
  'staff.update': 'bg-teal-100 text-teal-700',
  'campaign.send': 'bg-purple-100 text-purple-700',
  'payment.collect': 'bg-green-100 text-green-700',
  'estimate.approve': 'bg-cyan-100 text-cyan-700',
  'estimate.reject': 'bg-orange-100 text-orange-700',
  'schedule.modify': 'bg-indigo-100 text-indigo-700',
  'data.export': 'bg-pink-100 text-pink-700',
};

const RESOURCE_TYPES = [
  'customer', 'invoice', 'staff', 'campaign', 'payment',
  'estimate', 'schedule', 'expense', 'lead', 'job',
];

export function AuditLog() {
  const [params, setParams] = useState<AuditLogParams>({ page: 1, page_size: 20 });
  const { data: auditLog, isLoading } = useAuditLog(params);

  const getActionColor = (action: string) => {
    return ACTION_COLORS[action] ?? 'bg-gray-100 text-gray-700';
  };

  return (
    <Card data-testid="audit-log">
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          <Shield className="h-5 w-5 text-slate-500" />
          Audit Log
        </CardTitle>
        <p className="text-sm text-slate-500">Recent administrative actions</p>
      </CardHeader>
      <CardContent>
        {/* Filters */}
        <div className="flex flex-wrap gap-3 mb-4" data-testid="audit-log-filters">
          <Select
            value={params.resource_type ?? 'all'}
            onValueChange={(v) => setParams((p) => ({ ...p, resource_type: v === 'all' ? undefined : v, page: 1 }))}
          >
            <SelectTrigger className="w-36" data-testid="audit-resource-filter">
              <SelectValue placeholder="All Resources" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Resources</SelectItem>
              {RESOURCE_TYPES.map((rt) => (
                <SelectItem key={rt} value={rt}>{rt.charAt(0).toUpperCase() + rt.slice(1)}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Input
            type="date"
            value={params.start_date ?? ''}
            onChange={(e) => setParams((p) => ({ ...p, start_date: e.target.value || undefined, page: 1 }))}
            className="w-40"
            data-testid="audit-start-date"
          />
          <Input
            type="date"
            value={params.end_date ?? ''}
            onChange={(e) => setParams((p) => ({ ...p, end_date: e.target.value || undefined, page: 1 }))}
            className="w-40"
            data-testid="audit-end-date"
          />
        </div>

        {isLoading ? (
          <div className="flex justify-center py-8"><LoadingSpinner /></div>
        ) : (
          <>
            <Table data-testid="audit-log-table">
              <TableHeader>
                <TableRow>
                  <TableHead>Timestamp</TableHead>
                  <TableHead>Action</TableHead>
                  <TableHead>Resource</TableHead>
                  <TableHead>Actor</TableHead>
                  <TableHead>Details</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(auditLog?.items ?? []).length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center text-slate-500 py-8">
                      No audit log entries found
                    </TableCell>
                  </TableRow>
                ) : (
                  auditLog?.items.map((entry) => (
                    <TableRow key={entry.id} data-testid="audit-log-row">
                      <TableCell className="text-sm text-slate-500 whitespace-nowrap">
                        {new Date(entry.created_at).toLocaleString()}
                      </TableCell>
                      <TableCell>
                        <Badge className={getActionColor(entry.action)}>
                          {entry.action}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm">
                        <span className="text-slate-500">{entry.resource_type}</span>
                        <span className="text-slate-400 ml-1 text-xs font-mono">
                          {entry.resource_id.slice(0, 8)}
                        </span>
                      </TableCell>
                      <TableCell className="text-sm">
                        <span className="text-slate-700">{entry.actor_role}</span>
                      </TableCell>
                      <TableCell className="text-sm text-slate-500 max-w-[200px] truncate">
                        {Object.keys(entry.details).length > 0
                          ? JSON.stringify(entry.details).slice(0, 80)
                          : '—'}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>

            {/* Pagination */}
            {(auditLog?.total_pages ?? 1) > 1 && (
              <div className="flex items-center justify-center gap-2 mt-4">
                <Button
                  variant="outline"
                  size="icon"
                  disabled={(params.page ?? 1) <= 1}
                  onClick={() => setParams((p) => ({ ...p, page: (p.page ?? 1) - 1 }))}
                  data-testid="audit-prev-page"
                >
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                <span className="text-sm text-slate-500">
                  Page {params.page} of {auditLog?.total_pages ?? 1}
                </span>
                <Button
                  variant="outline"
                  size="icon"
                  disabled={(params.page ?? 1) >= (auditLog?.total_pages ?? 1)}
                  onClick={() => setParams((p) => ({ ...p, page: (p.page ?? 1) + 1 }))}
                  data-testid="audit-next-page"
                >
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
