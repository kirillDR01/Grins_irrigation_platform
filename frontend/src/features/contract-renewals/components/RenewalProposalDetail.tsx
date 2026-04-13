import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { format } from 'date-fns';
import { ArrowLeft, CheckCircle, XCircle, Pencil } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { LoadingPage, ErrorMessage, WeekPicker } from '@/shared/components';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import {
  useRenewalProposal,
  useApproveAll,
  useRejectAll,
  useApproveJob,
  useRejectJob,
  useModifyJob,
} from '../hooks/useContractRenewals';
import {
  PROPOSAL_STATUS_CONFIG,
  PROPOSED_JOB_STATUS_CONFIG,
  type ProposedJob,
} from '../types';

interface Props {
  proposalId: string;
}

export function RenewalProposalDetail({ proposalId }: Props) {
  const navigate = useNavigate();
  const { data: proposal, isLoading, error } = useRenewalProposal(proposalId);
  const approveAll = useApproveAll();
  const rejectAll = useRejectAll();
  const approveJob = useApproveJob();
  const rejectJob = useRejectJob();
  const modifyJob = useModifyJob();

  // Track per-job edits: { [jobId]: { admin_notes, target_start_date, target_end_date } }
  const [edits, setEdits] = useState<Record<string, { admin_notes?: string; target_start_date?: string; target_end_date?: string }>>({});
  const [editingJobId, setEditingJobId] = useState<string | null>(null);

  const getEdit = (jobId: string) => edits[jobId] ?? {};

  const updateEdit = useCallback((jobId: string, field: string, value: string | null) => {
    setEdits((prev) => ({
      ...prev,
      [jobId]: { ...prev[jobId], [field]: value },
    }));
  }, []);

  const handleApproveAll = useCallback(async () => {
    try {
      await approveAll.mutateAsync(proposalId);
      toast.success('All proposed jobs approved — real jobs created');
    } catch {
      toast.error('Failed to approve all');
    }
  }, [approveAll, proposalId]);

  const handleRejectAll = useCallback(async () => {
    try {
      await rejectAll.mutateAsync(proposalId);
      toast.success('All proposed jobs rejected');
    } catch {
      toast.error('Failed to reject all');
    }
  }, [rejectAll, proposalId]);

  const handleApproveJob = useCallback(async (job: ProposedJob) => {
    const edit = edits[job.id];
    try {
      await approveJob.mutateAsync({
        proposalId,
        jobId: job.id,
        modifications: edit ? {
          target_start_date: edit.target_start_date ?? undefined,
          target_end_date: edit.target_end_date ?? undefined,
          admin_notes: edit.admin_notes ?? undefined,
        } : undefined,
      });
      toast.success(`Job "${job.service_type}" approved`);
      setEditingJobId(null);
    } catch {
      toast.error('Failed to approve job');
    }
  }, [approveJob, proposalId, edits]);

  const handleRejectJob = useCallback(async (job: ProposedJob) => {
    try {
      await rejectJob.mutateAsync({ proposalId, jobId: job.id });
      toast.success(`Job "${job.service_type}" rejected`);
    } catch {
      toast.error('Failed to reject job');
    }
  }, [rejectJob, proposalId]);

  const handleSaveModification = useCallback(async (job: ProposedJob) => {
    const edit = edits[job.id];
    if (!edit) return;
    try {
      await modifyJob.mutateAsync({
        proposalId,
        jobId: job.id,
        modifications: {
          target_start_date: edit.target_start_date ?? undefined,
          target_end_date: edit.target_end_date ?? undefined,
          admin_notes: edit.admin_notes ?? undefined,
        },
      });
      toast.success('Modification saved');
      setEditingJobId(null);
    } catch {
      toast.error('Failed to save modification');
    }
  }, [modifyJob, proposalId, edits]);

  if (isLoading) return <LoadingPage message="Loading proposal..." />;
  if (error) return <ErrorMessage error={error} />;
  if (!proposal) return <ErrorMessage error={new Error('Proposal not found')} />;

  const statusCfg = PROPOSAL_STATUS_CONFIG[proposal.status];
  const isPending = proposal.status === 'pending';

  return (
    <div data-testid="renewal-proposal-detail" className="space-y-4">
      <Button variant="ghost" size="sm" onClick={() => navigate('/contract-renewals')} data-testid="back-btn">
        <ArrowLeft className="h-4 w-4 mr-1" /> Back to Renewals
      </Button>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-lg">
              Renewal Proposal{proposal.customer_name ? ` — ${proposal.customer_name}` : ''}
            </CardTitle>
            <p className="text-sm text-slate-500 mt-1">
              {proposal.agreement_number ? `${proposal.agreement_number} · ` : ''}
              Created {format(new Date(proposal.created_at), 'MMM d, yyyy h:mm a')}
              {' · '}{proposal.proposed_job_count} proposed jobs
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className={cn('inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium', statusCfg.className)}>
              {statusCfg.label}
            </span>
            {isPending && (
              <>
                <Button
                  size="sm"
                  className="bg-emerald-600 hover:bg-emerald-700 text-white"
                  onClick={handleApproveAll}
                  disabled={approveAll.isPending}
                  data-testid="approve-all-btn"
                >
                  <CheckCircle className="h-4 w-4 mr-1" /> Approve All
                </Button>
                <Button
                  size="sm"
                  variant="destructive"
                  onClick={handleRejectAll}
                  disabled={rejectAll.isPending}
                  data-testid="reject-all-btn"
                >
                  <XCircle className="h-4 w-4 mr-1" /> Reject All
                </Button>
              </>
            )}
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <Table data-testid="proposed-jobs-table">
            <TableHeader>
              <TableRow>
                <TableHead>Service Type</TableHead>
                <TableHead>Week Of</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Admin Notes</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {proposal.proposed_jobs.map((job) => {
                const jobStatusCfg = PROPOSED_JOB_STATUS_CONFIG[job.status];
                const isEditing = editingJobId === job.id;
                const edit = getEdit(job.id);
                const jobPending = job.status === 'pending';

                return (
                  <TableRow key={job.id} data-testid="proposed-job-row">
                    <TableCell className="font-medium">{job.service_type}</TableCell>
                    <TableCell>
                      {isEditing ? (
                        <WeekPicker
                          value={edit.target_start_date ?? job.target_start_date}
                          onChange={(v) => {
                            updateEdit(job.id, 'target_start_date', v);
                            // Compute Sunday from Monday
                            if (v) {
                              const monday = new Date(v + 'T00:00:00');
                              const sunday = new Date(monday);
                              sunday.setDate(sunday.getDate() + 6);
                              updateEdit(job.id, 'target_end_date', sunday.toISOString().split('T')[0]);
                            } else {
                              updateEdit(job.id, 'target_end_date', null);
                            }
                          }}
                          data-testid="edit-week-picker"
                        />
                      ) : (
                        job.target_start_date
                          ? `Week of ${format(new Date(job.target_start_date + 'T00:00:00'), 'M/d/yyyy')}`
                          : '—'
                      )}
                    </TableCell>
                    <TableCell>
                      <span className={cn('inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium', jobStatusCfg.className)}>
                        {jobStatusCfg.label}
                      </span>
                    </TableCell>
                    <TableCell>
                      {isEditing ? (
                        <Textarea
                          value={edit.admin_notes ?? job.admin_notes ?? ''}
                          onChange={(e) => updateEdit(job.id, 'admin_notes', e.target.value)}
                          placeholder="Add notes..."
                          className="min-h-[60px] text-sm"
                          data-testid="edit-admin-notes"
                        />
                      ) : (
                        <span className="text-sm text-slate-600">{job.admin_notes || '—'}</span>
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      {jobPending && (
                        <div className="flex items-center justify-end gap-1">
                          {isEditing ? (
                            <>
                              <Button size="sm" variant="outline" onClick={() => handleSaveModification(job)} disabled={modifyJob.isPending} data-testid="save-modify-btn">
                                Save
                              </Button>
                              <Button size="sm" variant="ghost" onClick={() => setEditingJobId(null)}>
                                Cancel
                              </Button>
                            </>
                          ) : (
                            <>
                              <Button
                                size="sm"
                                variant="ghost"
                                className="text-emerald-600 hover:bg-emerald-50"
                                onClick={() => handleApproveJob(job)}
                                disabled={approveJob.isPending}
                                data-testid="approve-job-btn"
                              >
                                <CheckCircle className="h-3.5 w-3.5 mr-1" /> Approve
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                className="text-red-600 hover:bg-red-50"
                                onClick={() => handleRejectJob(job)}
                                disabled={rejectJob.isPending}
                                data-testid="reject-job-btn"
                              >
                                <XCircle className="h-3.5 w-3.5 mr-1" /> Reject
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => setEditingJobId(job.id)}
                                data-testid="modify-job-btn"
                              >
                                <Pencil className="h-3.5 w-3.5 mr-1" /> Modify
                              </Button>
                            </>
                          )}
                        </div>
                      )}
                      {job.created_job_id && (
                        <span className="text-xs text-emerald-600">Job created</span>
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
