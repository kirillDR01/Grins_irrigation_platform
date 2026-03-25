import { useLocation } from 'react-router-dom';
import { CheckCircle2, XCircle, PenLine, FileText } from 'lucide-react';

type ConfirmationAction = 'approved' | 'rejected' | 'signed';

const actionConfig: Record<ConfirmationAction, {
  icon: typeof CheckCircle2;
  iconColor: string;
  title: string;
  message: string;
  nextSteps: string[];
}> = {
  approved: {
    icon: CheckCircle2,
    iconColor: 'text-emerald-500',
    title: 'Estimate Approved!',
    message: 'Thank you for approving the estimate. We appreciate your business.',
    nextSteps: [
      'You will receive a confirmation email shortly.',
      'Our team will reach out to schedule the work.',
      'A contract may be sent for your signature.',
    ],
  },
  rejected: {
    icon: XCircle,
    iconColor: 'text-slate-500',
    title: 'Estimate Declined',
    message: 'We understand. Thank you for letting us know.',
    nextSteps: [
      'If you change your mind, please contact us.',
      'We can prepare a revised estimate if needed.',
    ],
  },
  signed: {
    icon: PenLine,
    iconColor: 'text-emerald-500',
    title: 'Contract Signed!',
    message: 'Thank you for signing the contract. We look forward to working with you.',
    nextSteps: [
      'You will receive a copy of the signed contract via email.',
      'Our team will begin scheduling the work.',
      'You can reach out anytime with questions.',
    ],
  },
};

export function ApprovalConfirmation() {
  const location = useLocation();
  const action = (location.state as { action?: ConfirmationAction })?.action ?? 'approved';
  const config = actionConfig[action] ?? actionConfig.approved;
  const Icon = config.icon;

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4" data-testid="approval-confirmation-page">
      <div className="max-w-md w-full text-center space-y-6">
        <Icon className={`h-16 w-16 mx-auto ${config.iconColor}`} data-testid="confirmation-icon" />

        <div className="space-y-2">
          <h1 className="text-2xl font-bold text-slate-800" data-testid="confirmation-title">
            {config.title}
          </h1>
          <p className="text-slate-600" data-testid="confirmation-message">
            {config.message}
          </p>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-6 text-left space-y-3">
          <h2 className="font-semibold text-slate-700 flex items-center gap-2">
            <FileText className="h-4 w-4" />
            Next Steps
          </h2>
          <ul className="space-y-2" data-testid="next-steps-list">
            {config.nextSteps.map((step, idx) => (
              <li key={idx} className="flex items-start gap-2 text-sm text-slate-600">
                <span className="text-teal-500 font-bold mt-0.5">•</span>
                {step}
              </li>
            ))}
          </ul>
        </div>

        <p className="text-xs text-slate-400">
          You may close this page.
        </p>
      </div>
    </div>
  );
}
