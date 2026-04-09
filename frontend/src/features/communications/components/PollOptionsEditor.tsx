/**
 * PollOptionsEditor — Toggle + editable list of 2–5 poll options with date pickers.
 *
 * Renders a live preview of the numbered options block that will be appended
 * to the campaign message body, and reports the rendered text so the parent
 * can feed it into the segment counter.
 *
 * Validates: Requirements 12.1, 12.2, 12.3, 12.4, 12.5, 12.6
 */

import { useCallback } from 'react';
import { format } from 'date-fns';
import { CalendarIcon, Plus, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Calendar } from '@/components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { cn } from '@/lib/utils';
import type { PollOption } from '../types/campaign';
import { defaultPollLabel, renderPollOptionsBlock } from '../utils/pollOptions';

// --- Constants ---

const DIGIT_KEYS = ['1', '2', '3', '4', '5'] as const;
const MIN_OPTIONS = 2;
const MAX_OPTIONS = 5;

// --- Props ---

export interface PollOptionsEditorProps {
  enabled: boolean;
  onEnabledChange: (enabled: boolean) => void;
  options: PollOption[];
  onOptionsChange: (options: PollOption[]) => void;
}

export function PollOptionsEditor({
  enabled,
  onEnabledChange,
  options,
  onOptionsChange,
}: PollOptionsEditorProps) {
  // --- Toggle handler ---
  const handleToggle = useCallback(
    (checked: boolean) => {
      onEnabledChange(checked);
      if (checked && options.length === 0) {
        onOptionsChange([
          { key: '1', label: '', start_date: '', end_date: '' },
          { key: '2', label: '', start_date: '', end_date: '' },
        ]);
      }
    },
    [options.length, onEnabledChange, onOptionsChange],
  );

  // --- Mutators ---
  const updateOption = useCallback(
    (index: number, patch: Partial<PollOption>) => {
      const next = options.map((o, i) => (i === index ? { ...o, ...patch } : o));
      onOptionsChange(next);
    },
    [options, onOptionsChange],
  );

  const addOption = useCallback(() => {
    if (options.length >= MAX_OPTIONS) return;
    const nextKey = DIGIT_KEYS[options.length];
    onOptionsChange([
      ...options,
      { key: nextKey, label: '', start_date: '', end_date: '' },
    ]);
  }, [options, onOptionsChange]);

  const removeOption = useCallback(
    (index: number) => {
      if (options.length <= MIN_OPTIONS) return;
      const next = options
        .filter((_, i) => i !== index)
        .map((o, i) => ({ ...o, key: DIGIT_KEYS[i] }));
      onOptionsChange(next);
    },
    [options, onOptionsChange],
  );

  // --- Date validation errors ---
  const dateErrors = options
    .map((o) =>
      o.start_date && o.end_date && o.end_date < o.start_date
        ? `Option ${o.key}: end date must be on or after start date`
        : null,
    )
    .filter(Boolean) as string[];

  // --- Preview text ---
  const previewBlock = enabled ? renderPollOptionsBlock(options) : '';

  return (
    <div data-testid="poll-options-editor" className="space-y-4">
      {/* Toggle */}
      <div className="flex items-center gap-3">
        <Switch
          checked={enabled}
          onCheckedChange={handleToggle}
          data-testid="poll-toggle"
        />
        <Label className="text-sm font-medium text-slate-700 cursor-pointer">
          Collect poll responses
        </Label>
      </div>

      {enabled && (
        <>
          {/* Option rows */}
          <div className="space-y-3">
            {options.map((option, index) => (
              <div
                key={option.key}
                className="flex items-start gap-2 rounded-lg border border-slate-200 p-3"
                data-testid={`poll-option-row-${option.key}`}
              >
                {/* Key badge */}
                <span className="mt-2 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-teal-100 text-xs font-semibold text-teal-700">
                  {option.key}
                </span>

                {/* Fields */}
                <div className="flex-1 space-y-2">
                  {/* Label */}
                  <Input
                    value={option.label}
                    onChange={(e) => updateOption(index, { label: e.target.value })}
                    placeholder={defaultPollLabel(option.start_date) || 'Option label'}
                    maxLength={120}
                    data-testid={`poll-option-label-${option.key}`}
                  />

                  {/* Date pickers row */}
                  <div className="flex gap-2">
                    <DatePickerField
                      value={option.start_date}
                      onChange={(d) => {
                        const patch: Partial<PollOption> = { start_date: d };
                        if (!option.label && d) {
                          patch.label = defaultPollLabel(d);
                        }
                        updateOption(index, patch);
                      }}
                      placeholder="Start date"
                      testId={`poll-option-start-${option.key}`}
                    />
                    <DatePickerField
                      value={option.end_date}
                      onChange={(d) => updateOption(index, { end_date: d })}
                      placeholder="End date"
                      testId={`poll-option-end-${option.key}`}
                    />
                  </div>
                </div>

                {/* Remove button */}
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={() => removeOption(index)}
                  disabled={options.length <= MIN_OPTIONS}
                  data-testid={`poll-option-remove-${option.key}`}
                  className="mt-1 shrink-0 text-slate-400 hover:text-red-500"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            ))}
          </div>

          {/* Add option button */}
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={addOption}
            disabled={options.length >= MAX_OPTIONS}
            data-testid="poll-add-option-btn"
            className="gap-1"
          >
            <Plus className="h-3 w-3" />
            Add option
          </Button>

          {/* Date validation errors */}
          {dateErrors.length > 0 && (
            <Alert variant="destructive" data-testid="poll-date-errors">
              <AlertDescription>
                {dateErrors.map((e, i) => (
                  <div key={i}>{e}</div>
                ))}
              </AlertDescription>
            </Alert>
          )}

          {/* Live preview */}
          {previewBlock && (
            <div data-testid="poll-preview" className="space-y-1">
              <Label className="text-xs font-medium text-slate-500">
                Options preview (appended to message)
              </Label>
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 font-mono text-sm text-slate-700 whitespace-pre-wrap">
                {previewBlock.trim()}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

// --- Inline date picker field ---

function DatePickerField({
  value,
  onChange,
  placeholder,
  testId,
}: {
  value: string;
  onChange: (iso: string) => void;
  placeholder: string;
  testId: string;
}) {
  const dateValue = value ? new Date(value + 'T00:00:00') : undefined;

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          type="button"
          variant="outline"
          className={cn(
            'flex-1 justify-start text-left font-normal text-sm h-9',
            !value && 'text-slate-400',
          )}
          data-testid={testId}
        >
          <CalendarIcon className="mr-2 h-3.5 w-3.5" />
          {dateValue ? format(dateValue, 'MMM d, yyyy') : placeholder}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0" align="start">
        <Calendar
          mode="single"
          selected={dateValue}
          onSelect={(date) => {
            if (date) onChange(format(date, 'yyyy-MM-dd'));
          }}
        />
      </PopoverContent>
    </Popover>
  );
}
