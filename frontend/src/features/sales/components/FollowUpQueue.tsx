import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { LoadingSpinner, ErrorMessage } from '@/shared/components';
import { Clock } from 'lucide-react';
import { useFollowUps } from '../hooks';
import type { FollowUpItem } from '../types';

export function FollowUpQueue() {
  const navigate = useNavigate();
  const { data, isLoading, error } = useFollowUps();

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorMessage error={error} />;

  const items = data?.items ?? [];

  return (
    <Card data-testid="follow-up-queue">
      <CardHeader>
        <div className="flex items-center gap-2">
          <Clock className="h-5 w-5 text-blue-500" />
          <CardTitle className="text-lg">Follow-Up Queue</CardTitle>
          <Badge variant="secondary" className="ml-auto">{items.length} pending</Badge>
        </div>
        <p className="text-sm text-slate-500">Estimates with upcoming follow-up reminders</p>
      </CardHeader>
      <CardContent>
        {items.length === 0 ? (
          <p className="text-center text-sm text-slate-400 py-8">No follow-ups scheduled.</p>
        ) : (
          <Table data-testid="follow-up-table">
            <TableHeader>
              <TableRow>
                <TableHead>Customer</TableHead>
                <TableHead className="text-right">Estimate Total</TableHead>
                <TableHead className="text-right">Days Since Sent</TableHead>
                <TableHead>Next Follow-Up</TableHead>
                <TableHead>Promotion</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((item: FollowUpItem) => (
                <TableRow
                  key={item.id}
                  className="cursor-pointer hover:bg-slate-50"
                  onClick={() => navigate(`/estimates/${item.estimate_id}`)}
                  data-testid={`follow-up-row-${item.id}`}
                >
                  <TableCell className="font-medium">{item.customer_name}</TableCell>
                  <TableCell className="text-right">${item.estimate_total.toLocaleString()}</TableCell>
                  <TableCell className="text-right">
                    <span className={item.days_since_sent > 14 ? 'text-red-500 font-medium' : ''}>
                      {item.days_since_sent}d
                    </span>
                  </TableCell>
                  <TableCell>
                    {item.next_follow_up
                      ? new Date(item.next_follow_up).toLocaleDateString()
                      : '—'}
                  </TableCell>
                  <TableCell>
                    {item.promotion_code ? (
                      <Badge variant="outline" className="text-xs">{item.promotion_code}</Badge>
                    ) : (
                      <span className="text-slate-400">—</span>
                    )}
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
