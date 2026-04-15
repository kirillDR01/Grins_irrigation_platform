import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { format } from 'date-fns';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { LoadingPage, ErrorMessage } from '@/shared/components';
import { useRenewalProposals, useApproveAll, useRejectAll } from '../hooks/useContractRenewals';
import { PROPOSAL_STATUS_CONFIG, type RenewalProposal } from '../types';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import { CheckCircle, XCircle } from 'lucide-react';

export function RenewalReviewList() {
  const navigate = useNavigate();
  const { data: proposals, isLoading, error } = useRenewalProposals();
  const approveAll = useApproveAll();
  const rejectAll = useRejectAll();

  const handleRowClick = useCallback(
    (proposal: RenewalProposal) => {
      navigate(`/contract-renewals/${proposal.id}`);
    },
    [navigate],
  );

  const handleApproveAll = useCallback(
    async (e: React.MouseEvent, proposalId: string) => {
      e.stopPropagation();
      try {
        await approveAll.mutateAsync(proposalId);
        toast.success('All proposed jobs approved');
      } catch {
        toast.error('Failed to approve proposal');
      }
    },
    [approveAll],
  );

  const handleRejectAll = useCallback(
    async (e: React.MouseEvent, proposalId: string) => {
      e.stopPropagation();
      try {
        await rejectAll.mutateAsync(proposalId);
        toast.success('All proposed jobs rejected');
      } catch {
        toast.error('Failed to reject proposal');
      }
    },
    [rejectAll],
  );

  if (isLoading) return <LoadingPage message="Loading renewal proposals..." />;
  if (error) return <ErrorMessage error={error} />;

  if (!proposals?.length) {
    return (
      <Card data-testid="renewals-empty">
        <CardContent className="py-12 text-center text-slate-500">
          No pending renewal proposals.
        </CardContent>
      </Card>
    );
  }

  return (
    <div data-testid="renewal-review-list">
      <Card>
        <CardContent className="p-0">
          <Table data-testid="renewals-table">
            <TableHeader>
              <TableRow>
                <TableHead>Customer</TableHead>
                <TableHead>Agreement</TableHead>
                <TableHead className="text-center">Proposed Jobs</TableHead>
                <TableHead>Created</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {proposals.map((proposal) => {
                const statusCfg = PROPOSAL_STATUS_CONFIG[proposal.status];
                const isPending = proposal.status === 'pending';
                return (
                  <TableRow
                    key={proposal.id}
                    className="cursor-pointer hover:bg-slate-50"
                    onClick={() => handleRowClick(proposal)}
                    data-testid="renewal-row"
                  >
                    <TableCell className="font-medium">
                      {proposal.customer_name || proposal.customer_id.slice(0, 8) + '…'}
                    </TableCell>
                    <TableCell>
                      {proposal.agreement_number || proposal.service_agreement_id.slice(0, 8) + '…'}
                    </TableCell>
                    <TableCell className="text-center">
                      {proposal.proposed_job_count}
                    </TableCell>
                    <TableCell>
                      {format(new Date(proposal.created_at), 'MMM d, yyyy')}
                    </TableCell>
                    <TableCell>
                      <span className={cn('inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium', statusCfg.className)}>
                        {statusCfg.label}
                      </span>
                    </TableCell>
                    <TableCell className="text-right">
                      {isPending && (
                        <div className="flex items-center justify-end gap-1">
                          <Button
                            size="sm"
                            variant="ghost"
                            className="text-emerald-600 hover:text-emerald-700 hover:bg-emerald-50"
                            onClick={(e) => handleApproveAll(e, proposal.id)}
                            disabled={approveAll.isPending}
                            data-testid="approve-all-btn"
                          >
                            <CheckCircle className="h-4 w-4 mr-1" />
                            Approve All
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            className="text-red-600 hover:text-red-700 hover:bg-red-50"
                            onClick={(e) => handleRejectAll(e, proposal.id)}
                            disabled={rejectAll.isPending}
                            data-testid="reject-all-btn"
                          >
                            <XCircle className="h-4 w-4 mr-1" />
                            Reject All
                          </Button>
                        </div>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
