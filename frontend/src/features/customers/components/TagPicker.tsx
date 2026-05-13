/**
 * TagPicker — combobox autocomplete + inline-create tag editor for a customer.
 *
 * Replaces the hardcoded SUGGESTED_LABELS list previously used inside
 * TagEditorSheet. Wired into every tag surface (Customer, Job, Sales,
 * Appointment, Lead post-conversion) so all surfaces share one widget.
 *
 * Behavior:
 * - Reads existing tags from useCustomerTags(customerId).
 * - Manual tags are removable; system tags are protected.
 * - Typing in the CommandInput filters available tags. If no exact match
 *   exists, an inline "Create '<input>'" item appears (only when input
 *   length <= 32).
 * - Optimistically applies adds/removes and PUTs the new manual-tag set.
 *   On error, reverts and toasts.
 */

import { useState, useMemo } from 'react';
import { Plus } from 'lucide-react';
import { toast } from 'sonner';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import {
  Command,
  CommandEmpty,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command';
import { TagChip } from '@/shared/components/TagChip';
import {
  useCustomerTags,
  useSaveCustomerTags,
} from '@/features/schedule/hooks/useCustomerTags';
import type { CustomerTag, TagTone } from '@/features/schedule/types';

const MAX_LABEL_LEN = 32;
const DEFAULT_TONE: TagTone = 'neutral';

interface TagPickerProps {
  customerId: string;
  /** Optional controlled value. If omitted, falls back to useCustomerTags. */
  value?: CustomerTag[];
  /** Optional change callback for controlled use. If omitted, TagPicker
   *  saves directly via useSaveCustomerTags. */
  onChange?: (next: CustomerTag[]) => void;
  disabled?: boolean;
  className?: string;
}

export function TagPicker({
  customerId,
  value,
  onChange,
  disabled = false,
  className,
}: TagPickerProps) {
  const { data: serverTags = [] } = useCustomerTags(customerId);
  const saveTags = useSaveCustomerTags();

  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');

  const tags = value ?? serverTags;
  const manualTags = useMemo(
    () => tags.filter((t) => t.source === 'manual'),
    [tags],
  );
  const systemTags = useMemo(
    () => tags.filter((t) => t.source === 'system'),
    [tags],
  );

  const selectedLabels = useMemo(
    () => new Set(tags.map((t) => t.label.toLowerCase())),
    [tags],
  );

  // Suggestion list = tags this customer doesn't already have, filtered by
  // typed search. Since the canonical store is per-customer, this list
  // effectively represents the customer's existing manual tags minus what's
  // currently applied — which when starting fresh is empty. Therefore
  // inline-create is the dominant flow; the suggestion list will be sparse.
  // (Future enhancement: pull from a tenant-wide tag suggestion endpoint.)
  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return [] as CustomerTag[];
    return tags.filter(
      (t) =>
        t.label.toLowerCase().includes(q) &&
        !selectedLabels.has(t.label.toLowerCase()),
    );
  }, [tags, search, selectedLabels]);

  const trimmedSearch = search.trim();
  const exactMatch = useMemo(
    () =>
      tags.some(
        (t) => t.label.toLowerCase() === trimmedSearch.toLowerCase(),
      ),
    [tags, trimmedSearch],
  );
  const showCreate =
    trimmedSearch.length > 0 &&
    trimmedSearch.length <= MAX_LABEL_LEN &&
    !exactMatch;

  function commitManualTags(nextManual: CustomerTag[]) {
    const nextAll = [...systemTags, ...nextManual];
    if (onChange) {
      onChange(nextAll);
      return;
    }
    const payload = nextManual.map((t) => ({ label: t.label, tone: t.tone }));
    saveTags.mutate(
      { customerId, data: { tags: payload } },
      {
        onError: () => {
          toast.error("Couldn't save tag — try again");
        },
      },
    );
  }

  function addTag(label: string, tone: TagTone = DEFAULT_TONE) {
    if (disabled) return;
    const trimmed = label.trim().slice(0, MAX_LABEL_LEN);
    if (!trimmed) return;
    if (selectedLabels.has(trimmed.toLowerCase())) return;
    const draftTag: CustomerTag = {
      id: `draft-${Date.now()}`,
      customer_id: customerId,
      label: trimmed,
      tone,
      source: 'manual',
      created_at: new Date().toISOString(),
    };
    commitManualTags([...manualTags, draftTag]);
    setSearch('');
    setOpen(false);
  }

  function removeTag(id: string) {
    if (disabled) return;
    commitManualTags(manualTags.filter((t) => t.id !== id));
  }

  return (
    <div className={className} data-testid="tag-picker">
      <div className="flex flex-wrap items-center gap-2">
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
            onRemove={disabled ? undefined : () => removeTag(tag.id)}
          />
        ))}
        {tags.length === 0 && (
          <span className="text-[13px] text-slate-400">No tags yet</span>
        )}

        <Popover
          open={open}
          onOpenChange={(next) => {
            setOpen(next);
            if (!next) setSearch('');
          }}
        >
          <PopoverTrigger asChild>
            <button
              type="button"
              disabled={disabled}
              data-testid="tag-picker-add-button"
              className="inline-flex items-center gap-1 px-[10px] py-[5px] rounded-full border border-dashed border-slate-300 bg-white text-[12.5px] font-extrabold text-slate-600 hover:bg-slate-50 disabled:opacity-40"
            >
              <Plus className="h-3 w-3" />
              Add tag
            </button>
          </PopoverTrigger>
          <PopoverContent
            align="start"
            className="w-[280px] p-0"
            data-testid="tag-picker-popover"
          >
            <Command shouldFilter={false}>
              <CommandInput
                value={search}
                onValueChange={(v) => setSearch(v.slice(0, MAX_LABEL_LEN))}
                placeholder="Search or create tag…"
                data-testid="tag-picker-input"
              />
              <CommandList>
                {!showCreate && filtered.length === 0 && (
                  <CommandEmpty>No tags</CommandEmpty>
                )}
                {filtered.map((tag) => (
                  <CommandItem
                    key={tag.id}
                    value={tag.label}
                    onSelect={() => addTag(tag.label, tag.tone)}
                    data-testid={`tag-picker-suggestion-${tag.label}`}
                  >
                    {tag.label}
                  </CommandItem>
                ))}
                {showCreate && (
                  <CommandItem
                    value={`__create_${trimmedSearch}`}
                    onSelect={() => addTag(trimmedSearch)}
                    data-testid="tag-picker-create-item"
                  >
                    Create &ldquo;{trimmedSearch}&rdquo;
                  </CommandItem>
                )}
              </CommandList>
            </Command>
          </PopoverContent>
        </Popover>
      </div>
    </div>
  );
}
