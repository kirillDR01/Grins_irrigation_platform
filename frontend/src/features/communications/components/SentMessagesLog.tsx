import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { LoadingSpinner, ErrorMessage } from '@/shared/components';
import { Send, ChevronLeft, ChevronRight } from 'lucide-react';
import { cn } from '@/shared/utils/cn';
import { useSentMessages } from '../hooks';
import type { SentMessage, SentMessageListParams, DeliveryStatus } from '../types';

const STATUS_BADGE_CLASSES: Record<DeliveryStatus, string> = {
  delivered: 'bg-emerald-100 text-emerald-700',
  sent: 'bg-blue-100 text-blue-700',
  pending: 'bg-amber-100 text-amber-700',
  failed: 'bg-red-100 text-red-700',
};

// Radix Select does not allow empty-string values for SelectItem or the
// Select's `value` prop, so we use a sentinel for the "All" option and
// translate to/from `undefined` in the filter state.
const ALL_FILTER_VALUE = '__all__';

const MESSAGE_TYPES = [
  { value: ALL_FILTER_VALUE, label: 'All Types' },
  { value: 'appointment_reminder', label: 'Appointment Reminder' },
  { value: 'invoice_reminder', label: 'Invoice Reminder' },
  { value: 'estimate_sent', label: 'Estimate Sent' },
  { value: 'lead_confirmation', label: 'Lead Confirmation' },
  { value: 'review_request', label: 'Review Request' },
  { value: 'campaign', label: 'Campaign' },
  { value: 'day_of_reminder', label: 'Day-Of Reminder' },
  { value: 'delay_notification', label: 'Delay Notification' },
];

const DELIVERY_STATUSES = [
  { value: ALL_FILTER_VALUE, label: 'All Statuses' },
  { value: 'delivered', label: 'Delivered' },
  { value: 'sent', label: 'Sent' },
  { value: 'pending', label: 'Pending' },
  { value: 'failed', label: 'Failed' },
];

function truncateContent(content: string | null | undefined, maxLength = 80): string {
  if (!content) return '—';
  if (content.length <= maxLength) return content;
  return content.slice(0, maxLength) + '…';
}

function formatSentAt(sentAt: string | null | undefined): string {
  if (!sentAt) return '—';
  const d = new Date(sentAt);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleString();
}

export function SentMessagesLog() {
  const [params, setParams] = useState<SentMessageListParams>({
    page: 1,
    page_size: 20,
  });
  const [search, setSearch] = useState('');

  const { data, isLoading, error } = useSentMessages(params);

  const updateFilter = (key: keyof SentMessageListParams, value: string) => {
    setParams((prev) => ({
      ...prev,
      // Treat the "all" sentinel and empty string as "no filter".
      [key]: value && value !== ALL_FILTER_VALUE ? value : undefined,
      page: 1,
    }));
  };

  const handleSearch = () => {
    setParams((prev) => ({
      ...prev,
      search: search || undefined,
      page: 1,
    }));
  };

  const items = data?.items ?? [];
  const totalPages = data?.total_pages ?? 1;
  const currentPage = data?.page ?? 1;

  if (error) return <ErrorMessage error={error} />;

  return (
    <Card data-testid="sent-messages-log">
      <CardHeader>
        <div className="flex items-center gap-2">
          <Send className="h-5 w-5 text-blue-500" />
          <CardTitle className="text-lg">Sent Messages</CardTitle>
          <Badge variant="secondary" className="ml-auto">
            {data?.total ?? 0} total
          </Badge>
        </div>
        <p className="text-sm text-slate-500">
          Outbound notifications sent to customers and leads
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Filters */}
        <div
          className="flex flex-wrap gap-3 items-end"
          data-testid="sent-messages-filters"
        >
          <div className="space-y-1">
            <label className="text-xs font-medium text-slate-500">
              Message Type
            </label>
            <Select
              value={params.message_type ?? ALL_FILTER_VALUE}
              onValueChange={(v) => updateFilter('message_type', v)}
            >
              <SelectTrigger
                className="w-[180px]"
                data-testid="filter-message-type"
              >
                <SelectValue placeholder="All Types" />
              </SelectTrigger>
              <SelectContent>
                {MESSAGE_TYPES.map((t) => (
                  <SelectItem key={t.value} value={t.value}>
                    {t.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-medium text-slate-500">
              Delivery Status
            </label>
            <Select
              value={params.delivery_status ?? ALL_FILTER_VALUE}
              onValueChange={(v) => updateFilter('delivery_status', v)}
            >
              <SelectTrigger
                className="w-[160px]"
                data-testid="filter-delivery-status"
              >
                <SelectValue placeholder="All Statuses" />
              </SelectTrigger>
              <SelectContent>
                {DELIVERY_STATUSES.map((s) => (
                  <SelectItem key={s.value} value={s.value}>
                    {s.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-medium text-slate-500">From</label>
            <Input
              type="date"
              className="w-[150px]"
              data-testid="filter-date-from"
              value={params.date_from ?? ''}
              onChange={(e) => updateFilter('date_from', e.target.value)}
            />
          </div>

          <div className="space-y-1">
            <label className="text-xs font-medium text-slate-500">To</label>
            <Input
              type="date"
              className="w-[150px]"
              data-testid="filter-date-to"
              value={params.date_to ?? ''}
              onChange={(e) => updateFilter('date_to', e.target.value)}
            />
          </div>

          <div className="space-y-1 flex-1 min-w-[200px]">
            <label className="text-xs font-medium text-slate-500">Search</label>
            <div className="flex gap-2">
              <Input
                placeholder="Recipient name or phone…"
                data-testid="filter-search"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              />
              <Button
                variant="outline"
                size="sm"
                data-testid="filter-search-btn"
                onClick={handleSearch}
              >
                Search
              </Button>
            </div>
          </div>
        </div>

        {/* Table */}
        {isLoading ? (
          <LoadingSpinner />
        ) : items.length === 0 ? (
          <p
            className="text-center text-sm text-slate-400 py-8"
            data-testid="empty-sent-messages"
          >
            No sent messages found.
          </p>
        ) : (
          <>
            <Table data-testid="sent-messages-table">
              <TableHeader>
                <TableRow>
                  <TableHead>Recipient</TableHead>
                  <TableHead>Phone</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Content</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Sent At</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((msg: SentMessage) => (
                  <TableRow
                    key={msg.id}
                    data-testid={`sent-row-${msg.id}`}
                    className="hover:bg-slate-50"
                  >
                    <TableCell className="font-medium">
                      {msg.recipient_name ?? '—'}
                    </TableCell>
                    <TableCell className="text-sm text-slate-500">
                      {msg.recipient_phone ?? '—'}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="text-xs">
                        {(msg.message_type ?? 'unknown').replace(/_/g, ' ')}
                      </Badge>
                    </TableCell>
                    <TableCell className="max-w-xs">
                      <span className="text-sm text-slate-600">
                        {truncateContent(msg.content)}
                      </span>
                    </TableCell>
                    <TableCell>
                      <span
                        className={cn(
                          'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
                          STATUS_BADGE_CLASSES[msg.delivery_status],
                        )}
                        data-testid={`status-${msg.delivery_status}`}
                        title={
                          msg.delivery_status === 'failed' && msg.error_message
                            ? msg.error_message
                            : undefined
                        }
                      >
                        {msg.delivery_status}
                      </span>
                    </TableCell>
                    <TableCell className="text-sm text-slate-500 whitespace-nowrap">
                      {formatSentAt(msg.sent_at)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>

            {/* Pagination */}
            <div
              className="flex items-center justify-between pt-2"
              data-testid="sent-messages-pagination"
            >
              <p className="text-sm text-slate-500">
                Page {currentPage} of {totalPages} ({data?.total ?? 0} messages)
              </p>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  data-testid="pagination-prev"
                  disabled={currentPage <= 1}
                  onClick={() =>
                    setParams((prev) => ({
                      ...prev,
                      page: (prev.page ?? 1) - 1,
                    }))
                  }
                >
                  <ChevronLeft className="h-4 w-4" />
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  data-testid="pagination-next"
                  disabled={currentPage >= totalPages}
                  onClick={() =>
                    setParams((prev) => ({
                      ...prev,
                      page: (prev.page ?? 1) + 1,
                    }))
                  }
                >
                  Next
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
