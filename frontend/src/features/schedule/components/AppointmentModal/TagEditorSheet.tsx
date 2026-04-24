/**
 * Tag editor sheet for managing customer tags.
 * Tags are customer-scoped — changes apply across all jobs.
 * Requirements: 13.1–13.12
 */

import { useState, useRef } from 'react';
import { toast } from 'sonner';
import { SheetContainer } from '@/shared/components/SheetContainer';
import { TagChip } from '@/shared/components/TagChip';
import { useCustomerTags, useSaveCustomerTags } from '../../hooks/useCustomerTags';
import type { CustomerTag, TagTone } from '../../types';

const SUGGESTED_LABELS = [
  'Repeat customer',
  'Commercial',
  'Difficult access',
  'Dog on property',
  'Prefers text',
  'Gate code needed',
  'Corner lot',
];

const DEFAULT_TONE: TagTone = 'neutral';

interface TagEditorSheetProps {
  customerId: string;
  customerName: string;
  onClose: () => void;
}

export function TagEditorSheet({ customerId, customerName, onClose }: TagEditorSheetProps) {
  const { data: serverTags = [] } = useCustomerTags(customerId);
  const saveTags = useSaveCustomerTags();

  // Draft state: start from server tags
  const [draftTags, setDraftTags] = useState<CustomerTag[]>(() => serverTags);
  const [customInput, setCustomInput] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  // Sync draft when server tags load (only on first load)
  const [synced, setSynced] = useState(false);
  if (!synced && serverTags.length > 0) {
    setDraftTags(serverTags);
    setSynced(true);
  }

  const manualTags = draftTags.filter((t) => t.source === 'manual');
  const systemTags = draftTags.filter((t) => t.source === 'system');
  const appliedLabels = new Set(draftTags.map((t) => t.label.toLowerCase()));

  const suggestions = SUGGESTED_LABELS.filter(
    (s) => !appliedLabels.has(s.toLowerCase()),
  );

  function addTag(label: string, tone: TagTone = DEFAULT_TONE) {
    if (!label.trim()) return;
    const trimmed = label.trim().slice(0, 32);
    if (appliedLabels.has(trimmed.toLowerCase())) return;
    const newTag: CustomerTag = {
      id: `draft-${Date.now()}`,
      customer_id: customerId,
      label: trimmed,
      tone,
      source: 'manual',
      created_at: new Date().toISOString(),
    };
    setDraftTags((prev) => [...prev, newTag]);
  }

  function removeTag(id: string) {
    setDraftTags((prev) => prev.filter((t) => t.id !== id));
  }

  function handleCustomAdd() {
    if (!customInput.trim()) return;
    addTag(customInput);
    setCustomInput('');
    inputRef.current?.focus();
  }

  async function handleSave() {
    const manualPayload = draftTags
      .filter((t) => t.source === 'manual')
      .map((t) => ({ label: t.label, tone: t.tone }));

    try {
      await saveTags.mutateAsync({ customerId, data: { tags: manualPayload } });
      onClose();
    } catch {
      toast.error("Couldn't save tags — try again");
    }
  }

  const footer = (
    <div className="flex gap-3">
      <button
        type="button"
        onClick={onClose}
        className="flex-1 h-11 rounded-[12px] border-[1.5px] border-[#E5E7EB] bg-white text-[15px] font-semibold text-[#374151]"
      >
        Cancel
      </button>
      <button
        type="button"
        onClick={handleSave}
        disabled={saveTags.isPending}
        className="flex-1 h-11 rounded-[12px] bg-[#0B1220] text-white text-[15px] font-semibold disabled:opacity-50"
      >
        {saveTags.isPending ? 'Saving…' : 'Save tags · applies everywhere'}
      </button>
    </div>
  );

  return (
    <SheetContainer
      title="Edit tags"
      subtitle={`Tags apply to ${customerName} across every job — past and future`}
      onClose={onClose}
      footer={footer}
    >
      {/* Info banner */}
      <div className="mb-4 rounded-[10px] bg-[#DBEAFE] px-4 py-3 text-[13px] font-medium text-[#1E40AF]">
        Tags are saved to the customer profile and appear on all their appointments.
      </div>

      {/* Current tags */}
      <section className="mb-5">
        <p className="text-[11px] font-extrabold tracking-[0.06em] text-[#6B7280] uppercase mb-2">
          Current tags
        </p>
        <div className="min-h-[48px] rounded-[10px] bg-[#F9FAFB] border border-[#E5E7EB] p-3 flex flex-wrap gap-2">
          {systemTags.map((tag) => (
            <TagChip
              key={tag.id}
              label={tag.label}
              tone={tag.tone}
              onRemove={() => {}}
              removeDisabled
              removeDisabledTooltip="System tags cannot be removed"
            />
          ))}
          {manualTags.map((tag) => (
            <TagChip
              key={tag.id}
              label={tag.label}
              tone={tag.tone}
              onRemove={() => removeTag(tag.id)}
            />
          ))}
          {draftTags.length === 0 && (
            <span className="text-[13px] text-[#9CA3AF]">No tags yet</span>
          )}
        </div>

        {/* Custom tag input */}
        <div className="mt-2 flex gap-2">
          <input
            ref={inputRef}
            type="text"
            value={customInput}
            onChange={(e) => setCustomInput(e.target.value.slice(0, 32))}
            onKeyDown={(e) => e.key === 'Enter' && handleCustomAdd()}
            placeholder="Add custom tag…"
            maxLength={32}
            className="flex-1 h-10 rounded-[10px] border-[1.5px] border-dashed border-[#D1D5DB] bg-white px-3 text-[13.5px] font-semibold text-[#374151] placeholder:text-[#9CA3AF] focus:outline-none focus:border-[#6366F1]"
          />
          <button
            type="button"
            onClick={handleCustomAdd}
            disabled={!customInput.trim()}
            className="h-10 px-4 rounded-[10px] bg-[#0B1220] text-white text-[13.5px] font-semibold disabled:opacity-40"
          >
            Add
          </button>
        </div>
      </section>

      {/* Suggested tags */}
      {suggestions.length > 0 && (
        <section>
          <p className="text-[11px] font-extrabold tracking-[0.06em] text-[#6B7280] uppercase mb-2">
            Suggested
          </p>
          <div className="flex flex-wrap gap-2">
            {suggestions.map((label) => (
              <button
                key={label}
                type="button"
                onClick={() => addTag(label)}
                className="inline-flex items-center px-[10px] py-[5px] rounded-full border border-[#D1D5DB] bg-white text-[12.5px] font-extrabold text-[#374151] hover:bg-[#F3F4F6] transition-colors"
              >
                + {label}
              </button>
            ))}
          </div>
        </section>
      )}
    </SheetContainer>
  );
}
