import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { LoadingSpinner, ErrorMessage } from '@/shared/components';
import { Inbox, CheckCircle2 } from 'lucide-react';
import { cn } from '@/shared/utils/cn';
import { useUnaddressedCommunications, useMarkAddressed } from '../hooks';
import type { Communication, CommunicationChannel } from '../types';

const channelBadgeVariant: Record<CommunicationChannel, 'info' | 'success' | 'warning'> = {
  SMS: 'info',
  EMAIL: 'success',
  PHONE: 'warning',
};

function truncateContent(content: string, maxLength = 80): string {
  if (content.length <= maxLength) return content;
  return content.slice(0, maxLength) + '…';
}

const PAGE_SIZE = 20;

export function CommunicationsQueue() {
  const { data, isLoading, error } = useUnaddressedCommunications();
  const markAddressed = useMarkAddressed();
  const [page, setPage] = useState(1);
  const [mutatingId, setMutatingId] = useState<string | null>(null);

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorMessage error={error} />;

  const allItems = data?.items ?? [];
  const totalPages = Math.ceil(allItems.length / PAGE_SIZE);
  const items = allItems.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  return (
    <Card data-testid="communications-queue">
      <CardHeader>
        <div className="flex items-center gap-2">
          <Inbox className="h-5 w-5 text-amber-500" />
          <CardTitle className="text-lg">Needs Attention</CardTitle>
          <Badge variant="secondary" className="ml-auto">
            {items.length} unaddressed
          </Badge>
        </div>
        <p className="text-sm text-slate-500">
          Inbound messages that haven't been addressed yet
        </p>
      </CardHeader>
      <CardContent>
        {items.length === 0 ? (
          <p
            className="text-center text-sm text-slate-400 py-8"
            data-testid="empty-queue-message"
          >
            All caught up — no unaddressed messages.
          </p>
        ) : (
          <Table data-testid="communications-queue-table">
            <TableHeader>
              <TableRow>
                <TableHead>Customer</TableHead>
                <TableHead>Channel</TableHead>
                <TableHead>Message</TableHead>
                <TableHead>Received</TableHead>
                <TableHead className="text-right">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((item: Communication) => (
                <TableRow
                  key={item.id}
                  data-testid={`queue-row-${item.id}`}
                  className={cn(
                    'hover:bg-slate-50',
                    !item.addressed && 'bg-amber-50/30',
                  )}
                >
                  <TableCell className="font-medium">
                    {item.customer_name}
                  </TableCell>
                  <TableCell>
                    <Badge variant={channelBadgeVariant[item.channel]}>
                      {item.channel}
                    </Badge>
                  </TableCell>
                  <TableCell className="max-w-xs">
                    <span className="text-sm text-slate-600">
                      {truncateContent(item.content)}
                    </span>
                  </TableCell>
                  <TableCell className="text-sm text-slate-500 whitespace-nowrap">
                    {new Date(item.created_at).toLocaleString()}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      size="sm"
                      variant="outline"
                      data-testid={`mark-addressed-btn-${item.id}`}
                      disabled={mutatingId === item.id}
                      onClick={() => {
                        setMutatingId(item.id);
                        markAddressed.mutate(item.id, {
                          onSettled: () => setMutatingId(null),
                        });
                      }}
                    >
                      <CheckCircle2 className="h-4 w-4 mr-1" />
                      Mark as Addressed
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          {totalPages > 1 && (
            <div className="flex items-center justify-between pt-4 text-xs text-slate-500">
              <span>Page {page} of {totalPages} ({allItems.length} total)</span>
              <div className="flex gap-1">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => p - 1)}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        )}
      </CardContent>
    </Card>
  );
}
