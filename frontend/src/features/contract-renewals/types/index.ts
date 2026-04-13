export type ProposalStatus = 'pending' | 'approved' | 'rejected' | 'partially_approved';
export type ProposedJobStatus = 'pending' | 'approved' | 'rejected';

export interface ProposedJob {
  id: string;
  proposal_id: string;
  service_type: string;
  target_start_date: string | null;
  target_end_date: string | null;
  status: ProposedJobStatus;
  proposed_job_payload: Record<string, unknown> | null;
  admin_notes: string | null;
  created_job_id: string | null;
}

export interface RenewalProposal {
  id: string;
  service_agreement_id: string;
  customer_id: string;
  customer_name: string | null;
  agreement_number: string | null;
  status: ProposalStatus;
  proposed_job_count: number;
  created_at: string;
  reviewed_at: string | null;
  reviewed_by: string | null;
  proposed_jobs: ProposedJob[];
}

export interface ProposedJobModification {
  target_start_date?: string | null;
  target_end_date?: string | null;
  admin_notes?: string | null;
}

export const PROPOSAL_STATUS_CONFIG: Record<ProposalStatus, { label: string; className: string }> = {
  pending: { label: 'Pending Review', className: 'bg-amber-100 text-amber-700' },
  approved: { label: 'Approved', className: 'bg-emerald-100 text-emerald-700' },
  rejected: { label: 'Rejected', className: 'bg-red-100 text-red-700' },
  partially_approved: { label: 'Partially Approved', className: 'bg-blue-100 text-blue-700' },
};

export const PROPOSED_JOB_STATUS_CONFIG: Record<ProposedJobStatus, { label: string; className: string }> = {
  pending: { label: 'Pending', className: 'bg-slate-100 text-slate-700' },
  approved: { label: 'Approved', className: 'bg-emerald-100 text-emerald-700' },
  rejected: { label: 'Rejected', className: 'bg-red-100 text-red-700' },
};
