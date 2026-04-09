/**
 * MessageComposer — Step 2 of the campaign wizard.
 *
 * Template textarea with merge-field insertion, dual GSM-7/UCS-2 character
 * counter, segment count badge, merge-field linter, and live preview panel
 * using real recipient data from the audience preview endpoint.
 *
 * Validates: Requirements 15.8, 15.9, 15.10, 34, 43
 */

import { useState, useCallback, useMemo, useEffect, useRef } from 'react';
import { AlertTriangle, Plus, Eye } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { useAudiencePreview } from '../hooks';
import type { TargetAudience, AudiencePreviewRecipient, PollOption } from '../types/campaign';
import {
  SENDER_PREFIX,
  STOP_FOOTER,
  ALLOWED_MERGE_FIELDS,
  countSegments,
  findInvalidMergeFields,
  renderTemplate,
} from '../utils/segmentCounter';
import { renderPollOptionsBlock } from '../utils/pollOptions';
import { PollOptionsEditor } from './PollOptionsEditor';

// --- Props ---

export interface MessageComposerProps {
  /** Current message body from parent form */
  value: string;
  /** Callback when body changes */
  onChange: (body: string) => void;
  /** Current audience (for live preview) */
  audience: TargetAudience;
  /** Whether poll options editor is enabled */
  pollEnabled?: boolean;
  /** Callback when poll toggle changes */
  onPollEnabledChange?: (enabled: boolean) => void;
  /** Current poll options */
  pollOptions?: PollOption[];
  /** Callback when poll options change */
  onPollOptionsChange?: (options: PollOption[]) => void;
}

export function MessageComposer({
  value,
  onChange,
  audience,
  pollEnabled = false,
  onPollEnabledChange,
  pollOptions = [],
  onPollOptionsChange,
}: MessageComposerProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [previewRecipients, setPreviewRecipients] = useState<AudiencePreviewRecipient[]>([]);
  const audiencePreviewMutation = useAudiencePreview();

  // Fetch first 3 recipients for live preview
  useEffect(() => {
    const hasAudience =
      audience.customers?.ids_include?.length ||
      audience.leads?.ids_include?.length ||
      audience.ad_hoc?.recipients?.length;

    if (hasAudience) {
      audiencePreviewMutation.mutate(audience, {
        onSuccess: (data) => setPreviewRecipients(data.matches.slice(0, 3)),
      });
    }
  }, [audience]); // eslint-disable-line react-hooks/exhaustive-deps

  // --- Poll options block for segment counting ---
  const pollBlock = useMemo(
    () => (pollEnabled ? renderPollOptionsBlock(pollOptions) : ''),
    [pollEnabled, pollOptions],
  );

  // --- Segment counting (includes poll options block) ---
  const { encoding, segments, chars } = useMemo(
    () => countSegments(value + pollBlock),
    [value, pollBlock],
  );

  // --- Merge-field linting ---
  const invalidFields = useMemo(() => findInvalidMergeFields(value), [value]);

  // --- Empty merge field warning ---
  const emptyFirstNameCount = useMemo(() => {
    if (!value.includes('{first_name}')) return 0;
    return previewRecipients.filter((r) => !r.first_name).length;
  }, [value, previewRecipients]);

  // --- Insert merge field at cursor ---
  const insertMergeField = useCallback(
    (field: string) => {
      const ta = textareaRef.current;
      if (!ta) {
        onChange(value + `{${field}}`);
        return;
      }
      const start = ta.selectionStart;
      const end = ta.selectionEnd;
      const token = `{${field}}`;
      const newValue = value.slice(0, start) + token + value.slice(end);
      onChange(newValue);
      requestAnimationFrame(() => {
        ta.focus();
        ta.setSelectionRange(start + token.length, start + token.length);
      });
    },
    [value, onChange],
  );

  // --- Rendered previews ---
  const renderedPreviews = useMemo(() => {
    return previewRecipients.map((r) => {
      const context: Record<string, string> = {
        first_name: r.first_name ?? '',
        last_name: r.last_name ?? '',
        next_appointment_date: '',
      };
      const rendered = renderTemplate(value, context);
      return {
        recipient: r,
        message: `${SENDER_PREFIX}${rendered}${pollBlock}${STOP_FOOTER}`,
      };
    });
  }, [value, previewRecipients, pollBlock]);

  return (
    <div data-testid="message-composer" className="space-y-4">
      {/* Merge field buttons */}
      <div>
        <Label className="text-sm font-medium text-slate-700 mb-2 block">
          Insert merge field
        </Label>
        <div className="flex gap-2 flex-wrap">
          {ALLOWED_MERGE_FIELDS.map((field) => (
            <Button
              key={field}
              type="button"
              variant="outline"
              size="sm"
              onClick={() => insertMergeField(field)}
              data-testid={`insert-${field}`}
              className="gap-1 text-xs"
            >
              <Plus className="h-3 w-3" />
              {`{${field}}`}
            </Button>
          ))}
        </div>
      </div>

      {/* Textarea */}
      <Textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Type your message here... Use {first_name} to personalize."
        rows={5}
        data-testid="message-body-input"
        className="font-mono text-sm"
      />

      {/* Invalid merge field warning */}
      {invalidFields.length > 0 && (
        <Alert variant="destructive" data-testid="invalid-merge-fields">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            Unknown merge field{invalidFields.length > 1 ? 's' : ''}:{' '}
            {invalidFields.map((f) => `{${f}}`).join(', ')}. Allowed:{' '}
            {ALLOWED_MERGE_FIELDS.map((f) => `{${f}}`).join(', ')}.
          </AlertDescription>
        </Alert>
      )}

      {/* Poll options editor */}
      {onPollEnabledChange && onPollOptionsChange && (
        <>
          <Separator />
          <PollOptionsEditor
            enabled={pollEnabled}
            onEnabledChange={onPollEnabledChange}
            options={pollOptions}
            onOptionsChange={onPollOptionsChange}
          />
        </>
      )}

      {/* Character counter + segment badge */}
      <div
        className="flex items-center justify-between text-sm"
        data-testid="segment-info"
      >
        <span className="text-slate-500">
          {chars} characters ({encoding})
          {' · '}
          Includes prefix + STOP footer
        </span>
        <Badge
          variant={segments > 1 ? 'warning' : 'default'}
          data-testid="segment-badge"
        >
          {segments} segment{segments !== 1 ? 's' : ''}
        </Badge>
      </div>

      {segments > 1 && (
        <Alert data-testid="segment-warning">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            This message will send as {segments} SMS segments per recipient — cost
            multiplies by {segments}.
          </AlertDescription>
        </Alert>
      )}

      {/* Empty merge field warning */}
      {emptyFirstNameCount > 0 && (
        <Alert data-testid="empty-merge-warning">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            {emptyFirstNameCount} recipient{emptyFirstNameCount > 1 ? 's have' : ' has'}{' '}
            no first_name — their message will say &quot;Hi ,&quot;
          </AlertDescription>
        </Alert>
      )}

      {/* Live preview panel */}
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <Eye className="h-4 w-4 text-slate-400" />
          <Label className="text-sm font-medium text-slate-700">
            Live preview ({renderedPreviews.length} recipient{renderedPreviews.length !== 1 ? 's' : ''})
          </Label>
        </div>

        {renderedPreviews.length > 0 ? (
          <div className="space-y-2" data-testid="preview-panel">
            {renderedPreviews.map((p, i) => (
              <div
                key={i}
                className="rounded-lg border border-slate-200 bg-slate-50 p-3"
                data-testid={`preview-message-${i}`}
              >
                <p className="text-xs text-slate-400 mb-1">
                  To: {p.recipient.phone_masked} ({p.recipient.source_type})
                </p>
                <p className="text-sm text-slate-700 whitespace-pre-wrap break-words font-mono">
                  {p.message}
                </p>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-slate-400 italic" data-testid="preview-empty">
            Select recipients in Step 1 to see a live preview.
          </p>
        )}
      </div>
    </div>
  );
}
