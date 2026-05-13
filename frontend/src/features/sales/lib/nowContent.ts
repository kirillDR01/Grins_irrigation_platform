// nowContent.ts — pure lookup: stage + flags → NowCardContent
// frontend/src/features/sales/lib/nowContent.ts

import type {
  NowCardContent,
  NowCardInputs,
  NowAction,
  NowActionId,
  LucideIconName,
} from '../types/pipeline';

export function nowContent(
  inputs: NowCardInputs & { firstName: string; jobId?: string; sentDate?: string; docName?: string },
): NowCardContent | null {
  const {
    stage, hasEstimateDoc, hasSignedAgreement, hasCustomerEmail,
    firstName, jobId, sentDate, docName, weekOf, nudgesPaused,
  } = inputs;

  switch (stage) {
    case 'schedule_estimate':
      return {
        pill: { tone: 'you', label: 'Your move' },
        title: `Call ${firstName} — agree on a date, then drop them on the schedule.`,
        copyHtml:
          `"Schedule visit" opens the calendar with ${firstName}'s info pre-filled from the lead record. ` +
          `On submit it books the visit and texts ${firstName} a Y/R/C confirmation. ` +
          `"Resend confirmation text" re-sends the most recent visit's Y/R/C SMS if needed.`,
        actions: [
          act('primary', 'Schedule visit', 'now-action-schedule', 'schedule_visit', 'Calendar'),
          act('outline', 'Resend confirmation text', 'now-action-text-confirm', 'text_confirmation', 'MessageSquare'),
        ],
      };

    case 'send_estimate':
      return {
        pill: { tone: 'you', label: 'Your move' },
        title: 'Build the estimate and send it.',
        copyHtml:
          `Tap "Build & send estimate" to add line items and send ${firstName} a portal link for review and approval. ` +
          `Once they approve, this entry auto-advances to <em>Pending Approval</em>.`,
        actions: hasCustomerEmail
          ? [
              act('primary', 'Build & send estimate', 'now-action-build-send-estimate', 'build_and_send_estimate', 'FileText'),
              act('ghost', 'Skip — advance manually', 'now-action-skip-advance', 'skip_advance'),
            ]
          : [
              lock('Build & send estimate', 'now-action-build-send-estimate', 'no email on file — add one to send'),
              act('primary', 'Add customer email', 'now-action-add-email', 'add_customer_email', 'Edit3'),
            ],
      };

    case 'pending_approval':
      return {
        pill: { tone: 'cust', label: 'Waiting on customer' },
        title: `Waiting on ${firstName} to approve or decline.`,
        copyHtml:
          `Sent ${sentDate ?? 'recently'}. Auto follow-up runs on day 2, 5, 8 — then every Monday it sends a one-tap SMS: ` +
          `<em>"Reply A to approve, R to reject"</em>. Matching replies update the pipeline automatically.`,
        showNudgeSchedule: true,
        actions: [
          act('primary', 'Client approved (manual)', 'now-action-approved', 'mark_approved_manual', 'CheckCircle2'),
          act('outline', 'Resend estimate', 'now-action-resend', 'resend_estimate', 'RotateCw'),
          act('outline', nudgesPaused ? 'Resume auto-follow-up' : 'Pause auto-follow-up', 'now-action-pause', 'pause_nudges', nudgesPaused ? 'PlayCircle' : 'PauseCircle'),
          act('danger', 'Client declined', 'now-action-declined', 'mark_declined', 'XCircle'),
        ],
      };

    case 'send_contract':
      return {
        pill: { tone: 'you', label: 'Your move' },
        title: `${firstName} approved — upload the signed agreement, then convert.`,
        copyHtml:
          'Upload the signed agreement PDF below for our records, then convert to a Job.',
        dropzone: { kind: 'agreement', filled: hasSignedAgreement },
        showWeekOfPicker: true,
        actions: hasSignedAgreement
          ? [act('primary', 'Convert to Job', 'now-action-convert', 'convert_to_job', 'ArrowRight')]
          : [lock('Convert to Job', 'now-action-convert', 'upload signed agreement first')],
      };

    case 'closed_won':
      return {
        pill: { tone: 'done', label: 'Complete' },
        title: jobId
          ? `Job #${jobId} created — targeted for ${weekOf ?? 'later this month'}.`
          : `Job created — targeted for ${weekOf ?? 'later this month'}.`,
        copyHtml:
          `${firstName} is now a <em>Customer</em>; this entry has moved out of the Sales tab. ` +
          `The job sits in <em>Jobs</em> with status <em>To Be Scheduled</em> — pin a day and crew on the calendar when you're ready.`,
        actions: [
          act('primary', jobId ? `View Job #${jobId}` : 'View Job', 'now-action-view-job', 'view_job', 'ArrowRight'),
          act('outline', 'View Customer profile', 'now-action-view-customer', 'view_customer', 'User'),
          act('outline', 'Jump to Schedule', 'now-action-jump-schedule', 'jump_to_schedule', 'Calendar'),
        ],
      };
  }
}

/** Strip all HTML tags except <em>, </em>, <b>, </b>. */
export function sanitizeCopy(html: string): string {
  return html.replace(/<(?!\/?(?:em|b)\b)[^>]*>/gi, '');
}

// ────────── tiny builders ──────────

function act(
  kind: 'primary' | 'outline' | 'ghost' | 'danger',
  label: string,
  testId: string,
  onClickId: NowActionId,
  icon?: LucideIconName,
): NowAction {
  return { kind, label, testId, onClickId, icon } as NowAction;
}

function lock(label: string, testId: string, reason: string): NowAction {
  return { kind: 'locked', label, testId, reason };
}
