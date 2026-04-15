/**
 * Global duplicate review queue — paginated list of merge candidates sorted by score.
 *
 * Validates: CRM Changes Update 2 Req 6.1, 6.2, 6.3, 6.7, 6.12
 */

import { useState } from 'react';
import { Users, Merge } from 'lucide-react';
import { Button } from '@/components/ui/button';
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
import { LoadingPage, ErrorMessage } from '@/shared/components';
import { useDuplicateReviewQueue } from '../hooks';
import { MergeComparisonModal } from './MergeComparisonModal';
import type { MergeCandidate } from '../types';

interface DuplicateReviewQueueProps {
  onClose?: () => void;
}

export function DuplicateReviewQueue({ onClose }: DuplicateReviewQueueProps) {
  const [page, setPage] = useState(0);
  const limit = 20;
  const { data, isLoading, error, refetch } = useDuplicateReviewQueue(page * limit, limit);

  const [selectedCandidate, setSelectedCandidate] = useState<MergeCandidate | null>(null);

  if (isLoading) return <LoadingPage message="Loading duplicates…" />;
  if (error) return <ErrorMessage error={error} onRetry={() => refetch()} />;

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / limit));

  return (
    <>
      <Card data-testid="duplicate-review-queue">
        <CardHeader className="border-b border-slate-100">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Users className="h-5 w-5 text-teal-500" />
              Duplicate Review Queue
              {total > 0 && (
                <Badge variant="secondary" data-testid="duplicate-count-badge">
                  {total}
                </Badge>
              )}
            </CardTitle>
            {onClose && (
              <Button variant="ghost" size="sm" onClick={onClose}>
                Back to Customers
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {items.length === 0 ? (
            <div className="text-center py-12 text-slate-500">
              <Users className="h-10 w-10 mx-auto mb-3 text-slate-300" />
              <p>No duplicate candidates found.</p>
            </div>
          ) : (
            <>
              <Table data-testid="duplicate-table">
                <TableHeader>
                  <TableRow className="bg-slate-50/50">
                    <TableHead className="px-6 py-3 text-xs uppercase tracking-wider">Score</TableHead>
                    <TableHead className="px-6 py-3 text-xs uppercase tracking-wider">Customer A</TableHead>
                    <TableHead className="px-6 py-3 text-xs uppercase tracking-wider">Customer B</TableHead>
                    <TableHead className="px-6 py-3 text-xs uppercase tracking-wider">Signals</TableHead>
                    <TableHead className="px-6 py-3 text-xs uppercase tracking-wider">Status</TableHead>
                    <TableHead className="px-6 py-3 text-xs uppercase tracking-wider">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {items.map((c) => (
                    <TableRow key={c.id} data-testid={`candidate-row-${c.id}`}>
                      <TableCell className="px-6 py-3">
                        <Badge
                          variant={c.score >= 80 ? 'destructive' : c.score >= 50 ? 'default' : 'outline'}
                        >
                          {c.score}
                        </Badge>
                      </TableCell>
                      <TableCell className="px-6 py-3 text-sm">{c.customer_a_id.slice(0, 8)}…</TableCell>
                      <TableCell className="px-6 py-3 text-sm">{c.customer_b_id.slice(0, 8)}…</TableCell>
                      <TableCell className="px-6 py-3">
                        <div className="flex gap-1 flex-wrap">
                          {Object.keys(c.match_signals).map((sig) => (
                            <Badge key={sig} variant="outline" className="text-xs">
                              {sig}
                            </Badge>
                          ))}
                        </div>
                      </TableCell>
                      <TableCell className="px-6 py-3">
                        <Badge variant="secondary" className="text-xs capitalize">
                          {c.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="px-6 py-3">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setSelectedCandidate(c)}
                          data-testid={`review-merge-${c.id}`}
                        >
                          <Merge className="h-3.5 w-3.5 mr-1" />
                          Review & Merge
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="p-4 border-t border-slate-100 flex items-center justify-between">
                  <span className="text-sm text-slate-500">
                    Showing {page * limit + 1}–{Math.min((page + 1) * limit, total)} of {total}
                  </span>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={page === 0}
                      onClick={() => setPage((p) => p - 1)}
                    >
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={page >= totalPages - 1}
                      onClick={() => setPage((p) => p + 1)}
                    >
                      Next
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* Merge comparison modal */}
      {selectedCandidate && (
        <MergeComparisonModal
          open={!!selectedCandidate}
          onOpenChange={(open) => { if (!open) setSelectedCandidate(null); }}
          customerAId={selectedCandidate.customer_a_id}
          customerBId={selectedCandidate.customer_b_id}
          score={selectedCandidate.score}
          onMergeComplete={() => {
            setSelectedCandidate(null);
            refetch();
          }}
        />
      )}
    </>
  );
}
