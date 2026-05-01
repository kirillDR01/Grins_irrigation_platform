/**
 * ApprovedConfirmationCard — green confirmation card surfaced inside the
 * appointment modal when an estimate has been approved by the customer.
 *
 * Two states (umbrella plan Phase 0 / Task 0.7):
 *   - Standalone with new job → "Estimate approved · Job created"
 *     primary CTA "Schedule follow-up" opens the schedule modal against
 *     the new job.
 *   - Attached to a parent job → "Estimate approved · Items added to
 *     current appointment" — no CTA.
 */

import { CheckCircle2 } from 'lucide-react';

interface ApprovedConfirmationCardProps {
  /** Job ID auto-created from the approved estimate (null when N5 OFF or skipped). */
  jobId: string | null;
  /** True when the estimate was attached to an existing in-progress job. */
  attachedToParentJob: boolean;
  /** Optional human-readable job number ("J-1042") for display. */
  jobNumber?: string | null;
  /** Open the schedule modal targeting the auto-created job. */
  onScheduleFollowUp?: () => void;
}

export function ApprovedConfirmationCard({
  jobId,
  attachedToParentJob,
  jobNumber,
  onScheduleFollowUp,
}: ApprovedConfirmationCardProps) {
  if (attachedToParentJob) {
    return (
      <div
        data-testid="estimate-approved-card-attached"
        className="rounded-[14px] border border-[#A7F3D0] bg-[#ECFDF5] px-4 py-3 flex items-start gap-3"
      >
        <CheckCircle2
          size={18}
          className="text-[#059669] flex-shrink-0 mt-0.5"
          strokeWidth={2.5}
        />
        <div className="flex-1 min-w-0">
          <p className="text-[10px] font-extrabold tracking-[0.6px] text-[#047857] uppercase">
            Estimate Approved
          </p>
          <p className="text-[14px] font-semibold text-[#064E3B] leading-snug">
            Items added to current appointment
          </p>
        </div>
      </div>
    );
  }

  if (!jobId) {
    // N5 was OFF or auto-job branch skipped (lead-only / failure).
    return (
      <div
        data-testid="estimate-approved-card-no-job"
        className="rounded-[14px] border border-[#A7F3D0] bg-[#ECFDF5] px-4 py-3 flex items-start gap-3"
      >
        <CheckCircle2
          size={18}
          className="text-[#059669] flex-shrink-0 mt-0.5"
          strokeWidth={2.5}
        />
        <div className="flex-1 min-w-0">
          <p className="text-[10px] font-extrabold tracking-[0.6px] text-[#047857] uppercase">
            Estimate Approved
          </p>
          <p className="text-[14px] font-semibold text-[#064E3B] leading-snug">
            Customer approved this estimate. No job has been auto-created.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div
      data-testid="estimate-approved-card-standalone"
      className="rounded-[14px] border border-[#A7F3D0] bg-[#ECFDF5] px-4 py-3 flex items-start gap-3"
    >
      <CheckCircle2
        size={18}
        className="text-[#059669] flex-shrink-0 mt-0.5"
        strokeWidth={2.5}
      />
      <div className="flex-1 min-w-0">
        <p className="text-[10px] font-extrabold tracking-[0.6px] text-[#047857] uppercase">
          Estimate Approved
        </p>
        <p className="text-[14px] font-semibold text-[#064E3B] leading-snug">
          Job created{jobNumber ? ` (#${jobNumber})` : ''}
        </p>
      </div>
      {onScheduleFollowUp && (
        <button
          type="button"
          onClick={onScheduleFollowUp}
          data-testid="schedule-follow-up-cta"
          className="flex-shrink-0 rounded-md bg-[#059669] px-3 py-1.5 text-[12px] font-semibold text-white hover:bg-[#047857]"
        >
          Schedule follow-up
        </button>
      )}
    </div>
  );
}
