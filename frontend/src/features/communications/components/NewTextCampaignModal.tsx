/**
 * NewTextCampaignModal — 3-step wizard for creating and sending SMS campaigns.
 *
 * Steps: AudienceBuilder → MessageComposer → CampaignReview
 * Draft persistence to localStorage (debounced 500ms) + DB draft on first "Next".
 * UI status labels per Requirement 27: "Queued" (pending), "Sending", "Sent", "Failed", "Cancelled".
 *
 * Validates: Requirements 15.2, 27, 33
 */

import { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import { toast } from 'sonner';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/features/auth';
import { AudienceBuilder } from './AudienceBuilder';
import { MessageComposer } from './MessageComposer';
import { CampaignReview } from './CampaignReview';
import {
  useCreateCampaign,
  useUpdateCampaign,
  useSendCampaign,
  useAudiencePreview,
} from '../hooks';
import type { TargetAudience, AudiencePreview, PollOption } from '../types/campaign';
import { validatePollOptions } from '../utils/pollOptions';

// --- Constants ---

const STEPS = ['Audience', 'Message', 'Review'] as const;
type Step = 0 | 1 | 2;

const DRAFT_DEBOUNCE_MS = 500;

function getDraftKey(userId: string): string {
  return `comms:draft_campaign:${userId}`;
}

interface DraftState {
  audience: TargetAudience;
  messageBody: string;
  pollEnabled?: boolean;
  pollOptions?: PollOption[];
  savedAt: string;
}

// --- Props ---

export interface NewTextCampaignModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Pre-populated customer IDs (from "Text Selected" on Customers tab) */
  preSelectedCustomerIds?: string[];
  /** Pre-populated lead IDs (from "Text Selected" on Leads tab) */
  preSelectedLeadIds?: string[];
}

export function NewTextCampaignModal({
  open,
  onOpenChange,
  preSelectedCustomerIds,
  preSelectedLeadIds,
}: NewTextCampaignModalProps) {
  const { user } = useAuth();
  const userId = user?.id ?? 'anonymous';

  // --- Wizard state ---
  const [step, setStep] = useState<Step>(0);
  const [audience, setAudience] = useState<TargetAudience>({});
  const [messageBody, setMessageBody] = useState('');
  const [campaignId, setCampaignId] = useState<string | null>(null);
  const [pollEnabled, setPollEnabled] = useState(false);
  const [pollOptions, setPollOptions] = useState<PollOption[]>([]);
  const draftCheckedRef = useRef(false);

  // --- Preview state (fetched when entering step 2) ---
  const [preview, setPreview] = useState<AudiencePreview | null>(null);

  // --- Mutations ---
  const createCampaign = useCreateCampaign();
  const updateCampaign = useUpdateCampaign();
  const sendCampaign = useSendCampaign();
  const audiencePreviewMutation = useAudiencePreview();

  // --- Draft persistence (localStorage, debounced 500ms) ---
  const draftTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const saveDraft = useCallback(() => {
    const draft: DraftState = {
      audience,
      messageBody,
      pollEnabled,
      pollOptions,
      savedAt: new Date().toISOString(),
    };
    try {
      localStorage.setItem(getDraftKey(userId), JSON.stringify(draft));
    } catch {
      // localStorage full or unavailable — ignore
    }
  }, [audience, messageBody, pollEnabled, pollOptions, userId]);

  // Debounced auto-save on field change
  useEffect(() => {
    if (!open) return;
    if (draftTimerRef.current) clearTimeout(draftTimerRef.current);
    draftTimerRef.current = setTimeout(saveDraft, DRAFT_DEBOUNCE_MS);
    return () => {
      if (draftTimerRef.current) clearTimeout(draftTimerRef.current);
    };
  }, [audience, messageBody, pollEnabled, pollOptions, open, saveDraft]);

  // --- Draft restoration prompt on open ---
  useEffect(() => {
    if (!open) {
      draftCheckedRef.current = false;
      return;
    }
    if (draftCheckedRef.current) return;
    draftCheckedRef.current = true;

    try {
      const raw = localStorage.getItem(getDraftKey(userId));
      if (!raw) return;
      const draft: DraftState = JSON.parse(raw);
      if (!draft.savedAt) return;

      const savedDate = new Date(draft.savedAt);
      const ago = formatRelativeTime(savedDate);

      toast(`You have an unsaved draft from ${ago}`, {
        action: {
          label: 'Continue',
          onClick: () => {
            setAudience(draft.audience);
            setMessageBody(draft.messageBody);
            if (typeof draft.pollEnabled === 'boolean') {
              setPollEnabled(draft.pollEnabled);
            }
            if (Array.isArray(draft.pollOptions)) {
              setPollOptions(draft.pollOptions);
            }
          },
        },
        cancel: {
          label: 'Discard',
          onClick: () => {
            localStorage.removeItem(getDraftKey(userId));
          },
        },
        duration: 10000,
      });
    } catch {
      // Corrupt draft — ignore
    }
  }, [open, userId]);

  // --- Audience has content check ---
  const hasAudience = useMemo(() => {
    return !!(
      audience.customers?.ids_include?.length ||
      audience.leads?.ids_include?.length ||
      audience.ad_hoc?.recipients?.length
    );
  }, [audience]);

  // --- Poll-options validity (mirrors backend Pydantic PollOption schema) ---
  const pollOptionsValid = useMemo(
    () => (pollEnabled ? validatePollOptions(pollOptions).valid : true),
    [pollEnabled, pollOptions],
  );

  // --- Step navigation ---
  const handleNext = useCallback(async () => {
    if (step === 0) {
      if (!hasAudience) {
        toast.error('Select at least one recipient.');
        return;
      }

      // Persist draft as DB Campaign row on first "Next" (Requirement 33.6)
      if (!campaignId) {
        try {
          const campaign = await createCampaign.mutateAsync({
            name: `SMS Campaign ${new Date().toLocaleDateString()}`,
            campaign_type: 'sms',
            target_audience: audience,
            body: messageBody || '',
            poll_options: pollEnabled && pollOptions.length >= 2 ? pollOptions : null,
          });
          setCampaignId(campaign.id);
        } catch {
          toast.error('Failed to save campaign draft.');
          return;
        }
      }

      // Fetch preview for step 2 and 3
      audiencePreviewMutation.mutate(audience, {
        onSuccess: (data) => setPreview(data),
        onError: () => setPreview(null),
      });

      setStep(1);
    } else if (step === 1) {
      if (!messageBody.trim()) {
        toast.error('Message body cannot be empty.');
        return;
      }
      if (pollEnabled && !pollOptionsValid) {
        toast.error(
          'Fill in labels and start/end dates for every poll option before continuing.',
        );
        return;
      }
      // Persist composed body + poll options to the draft before entering Review
      if (campaignId) {
        try {
          await updateCampaign.mutateAsync({
            id: campaignId,
            data: {
              body: messageBody,
              poll_options: pollEnabled && pollOptions.length >= 2 ? pollOptions : null,
            },
          });
        } catch {
          toast.error('Failed to save message draft.');
          return;
        }
      }
      setStep(2);
    }
  }, [step, hasAudience, campaignId, audience, messageBody, pollEnabled, pollOptions, pollOptionsValid, createCampaign, updateCampaign, audiencePreviewMutation]);

  const handleBack = useCallback(() => {
    if (step > 0) setStep((s) => (s - 1) as Step);
  }, [step]);

  // --- Reset wizard ---
  const resetWizard = useCallback(() => {
    setStep(0);
    setAudience({});
    setMessageBody('');
    setCampaignId(null);
    setPreview(null);
    setPollEnabled(false);
    setPollOptions([]);
  }, []);

  // --- Send / Schedule ---
  const handleSendNow = useCallback(async () => {
    if (!campaignId) return;
    if (!messageBody.trim()) {
      toast.error('Message body cannot be empty.');
      return;
    }
    if (pollEnabled && !pollOptionsValid) {
      toast.error(
        'Fill in labels and start/end dates for every poll option before sending.',
      );
      return;
    }
    try {
      // Persist the composed body + latest audience to the draft before sending.
      await updateCampaign.mutateAsync({
        id: campaignId,
        data: {
          target_audience: audience,
          body: messageBody,
          poll_options: pollEnabled && pollOptions.length >= 2 ? pollOptions : null,
        },
      });
      await sendCampaign.mutateAsync(campaignId);
      toast.success('Campaign queued for sending.');
      localStorage.removeItem(getDraftKey(userId));
      onOpenChange(false);
      resetWizard();
    } catch {
      toast.error('Failed to send campaign.');
    }
  }, [campaignId, messageBody, audience, pollEnabled, pollOptions, pollOptionsValid, updateCampaign, sendCampaign, userId, onOpenChange, resetWizard]);

  const handleSchedule = useCallback(
    async (scheduledAt: string) => {
      if (!campaignId) return;
      if (!messageBody.trim()) {
        toast.error('Message body cannot be empty.');
        return;
      }
      if (pollEnabled && !pollOptionsValid) {
        toast.error(
          'Fill in labels and start/end dates for every poll option before scheduling.',
        );
        return;
      }
      try {
        // Persist composed body + latest audience + schedule to the existing draft.
        await updateCampaign.mutateAsync({
          id: campaignId,
          data: {
            target_audience: audience,
            body: messageBody,
            scheduled_at: scheduledAt,
            poll_options: pollEnabled && pollOptions.length >= 2 ? pollOptions : null,
          },
        });
        await sendCampaign.mutateAsync(campaignId);
        toast.success(`Campaign scheduled for ${new Date(scheduledAt).toLocaleString()}.`);
        localStorage.removeItem(getDraftKey(userId));
        onOpenChange(false);
        resetWizard();
      } catch {
        toast.error('Failed to schedule campaign.');
      }
    },
    [campaignId, audience, messageBody, pollEnabled, pollOptions, pollOptionsValid, updateCampaign, sendCampaign, userId, onOpenChange, resetWizard],
  );

  // Reset on close — cancel pending debounce to prevent saving an empty draft
  const handleOpenChange = useCallback(
    (nextOpen: boolean) => {
      if (!nextOpen) {
        if (draftTimerRef.current) clearTimeout(draftTimerRef.current);
        resetWizard();
      }
      onOpenChange(nextOpen);
    },
    [onOpenChange, resetWizard],
  );

  const isSending =
    sendCampaign.isPending || createCampaign.isPending || updateCampaign.isPending;

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent
        className="max-w-3xl max-h-[90vh] overflow-y-auto"
        data-testid="new-campaign-modal"
      >
        <DialogHeader>
          <DialogTitle>New Text Campaign</DialogTitle>
          <DialogDescription>
            Step {step + 1} of {STEPS.length}: {STEPS[step]}
          </DialogDescription>
        </DialogHeader>

        {/* Step indicator */}
        <div className="flex gap-2 mb-4" data-testid="step-indicator">
          {STEPS.map((label, i) => (
            <div
              key={label}
              className={`flex-1 h-1.5 rounded-full ${
                i <= step ? 'bg-teal-600' : 'bg-slate-200'
              }`}
            />
          ))}
        </div>

        {/* Step content */}
        {step === 0 && (
          <AudienceBuilder
            value={audience}
            onChange={setAudience}
            preSelectedCustomerIds={preSelectedCustomerIds}
            preSelectedLeadIds={preSelectedLeadIds}
          />
        )}

        {step === 1 && (
          <MessageComposer
            value={messageBody}
            onChange={setMessageBody}
            audience={audience}
            pollEnabled={pollEnabled}
            onPollEnabledChange={setPollEnabled}
            pollOptions={pollOptions}
            onPollOptionsChange={setPollOptions}
          />
        )}

        {step === 2 && (
          <CampaignReview
            preview={preview}
            messageBody={messageBody}
            pollEnabled={pollEnabled}
            pollOptions={pollOptions}
            onSendNow={handleSendNow}
            onSchedule={handleSchedule}
            isSending={isSending}
          />
        )}

        {/* Navigation footer (steps 0 and 1 only — step 2 has its own confirm) */}
        {step < 2 && (
          <div className="flex justify-between pt-4 border-t">
            <Button
              variant="outline"
              onClick={handleBack}
              disabled={step === 0}
              data-testid="wizard-back-btn"
            >
              Back
            </Button>
            <Button
              onClick={handleNext}
              disabled={
                isSending ||
                (step === 1 && !messageBody.trim()) ||
                (step === 1 && pollEnabled && !pollOptionsValid)
              }
              data-testid="wizard-next-btn"
              title={
                step === 1 && pollEnabled && !pollOptionsValid
                  ? 'Fill in labels and dates for every poll option'
                  : undefined
              }
            >
              {isSending ? 'Saving...' : 'Next'}
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

// --- Helpers ---

function formatRelativeTime(date: Date): string {
  const now = Date.now();
  const diffMs = now - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return 'just now';
  if (diffMin < 60) return `${diffMin} minute${diffMin !== 1 ? 's' : ''} ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr} hour${diffHr !== 1 ? 's' : ''} ago`;
  const diffDay = Math.floor(diffHr / 24);
  return `${diffDay} day${diffDay !== 1 ? 's' : ''} ago`;
}
