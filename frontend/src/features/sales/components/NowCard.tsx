// ============================================================
// NowCard.tsx — stage-driven "what to do next" card
// Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 10.1–10.6, 14.1–14.5, 16.3, 16.7
// Pure component; host wires onAction to mutations.
// ============================================================

import { useState, useRef } from 'react';
import {
  Calendar, Mail, MessageSquare, Upload, CheckCircle2, XCircle,
  RotateCw, PauseCircle, PlayCircle, ArrowRight, User, Edit3, Lock, FileText,
} from 'lucide-react';
import { format } from 'date-fns';
import { Button } from '@/components/ui/button';
import { Calendar as CalendarPicker } from '@/components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import {
  Tooltip, TooltipContent, TooltipProvider, TooltipTrigger,
} from '@/components/ui/tooltip';
import { toast } from 'sonner';
import type {
  NowCardContent, NowAction, NowActionId, LucideIconName,
} from '../types/pipeline';
import { AutoNudgeSchedule } from './AutoNudgeSchedule';

const ICON_MAP: Record<LucideIconName, React.ComponentType<{ className?: string }>> = {
  Calendar, Mail, MessageSquare, Upload, CheckCircle2, XCircle,
  RotateCw, PauseCircle, PlayCircle, ArrowRight, User, Edit3, Lock, FileText,
};

interface NowCardProps {
  stageKey: string;
  content: NowCardContent;
  onAction: (id: NowActionId) => void;
  onFileDrop?: (file: File, kind: 'estimate' | 'agreement') => void;
  weekOfValue?: string | null;
  onWeekOfChange?: (weekOf: string) => void;
  estimateSentAt?: string;  // required when showNudgeSchedule
  nudgesPaused?: boolean;
}

const PILL_STYLES = {
  you:  { pill: 'bg-sky-100 text-sky-700',         border: 'border-l-sky-400'     },
  cust: { pill: 'bg-amber-100 text-amber-700',     border: 'border-l-amber-400'   },
  done: { pill: 'bg-emerald-100 text-emerald-700', border: 'border-l-emerald-400' },
} as const;

export function NowCard({
  stageKey, content, onAction, onFileDrop,
  weekOfValue, onWeekOfChange, estimateSentAt, nudgesPaused,
}: NowCardProps) {
  const tone = content.pill.tone;
  return (
    <div
      data-testid="now-card"
      data-stage={stageKey}
      className={`bg-white rounded-2xl border border-slate-200 border-l-4 shadow-sm p-6 space-y-4 ${PILL_STYLES[tone].border}`}
    >
      <div>
        <span
          className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${PILL_STYLES[tone].pill}`}
          data-testid="now-card-pill"
          data-tone={tone}
        >
          {content.pill.label}
        </span>
      </div>

      <h3
        className="text-lg font-semibold text-slate-900"
        style={{ textWrap: 'pretty' } as React.CSSProperties}
        data-testid="now-card-title"
      >
        {content.title}
      </h3>

      <p
        className="text-sm text-slate-600 leading-relaxed"
        dangerouslySetInnerHTML={{ __html: sanitizeCopy(content.copyHtml) }}
      />

      {content.dropzone && (
        <Dropzone
          kind={content.dropzone.kind}
          filled={content.dropzone.filled}
          onDrop={onFileDrop}
        />
      )}

      {content.showNudgeSchedule && estimateSentAt && (
        <AutoNudgeSchedule estimateSentAt={estimateSentAt} paused={nudgesPaused} />
      )}

      {content.showWeekOfPicker && (
        <WeekOfPicker value={weekOfValue} onChange={onWeekOfChange} />
      )}

      <div className="flex flex-wrap items-center gap-2 pt-1">
        {content.actions.map((a) => (
          <ActionButton key={a.testId} action={a} onAction={onAction} />
        ))}
      </div>

      {content.lockBanner && (
        <div
          className="flex items-start gap-2 bg-red-50 border border-red-200 text-red-700 rounded-md px-3 py-2 text-sm"
          data-testid="now-card-lock-banner"
        >
          <Lock className="h-4 w-4 shrink-0 mt-0.5" />
          <span dangerouslySetInnerHTML={{ __html: sanitizeCopy(content.lockBanner.textHtml) }} />
        </div>
      )}
    </div>
  );
}

// ────────── Action button ──────────

function ActionButton({
  action, onAction,
}: {
  action: NowAction;
  onAction: (id: NowActionId) => void;
}) {
  if (action.kind === 'locked') {
    return (
      <TooltipProvider delayDuration={200}>
        <Tooltip>
          <TooltipTrigger asChild>
            <span>
              <Button
                size="sm"
                variant="outline"
                disabled
                data-testid={action.testId}
                className="gap-1.5"
              >
                <Lock className="h-3.5 w-3.5" />
                {action.label}
              </Button>
            </span>
          </TooltipTrigger>
          <TooltipContent>{action.reason}</TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }
  const Icon = action.icon ? ICON_MAP[action.icon] : null;
  const variant = action.kind === 'primary' ? 'default'
    : action.kind === 'outline' ? 'outline'
    : action.kind === 'ghost' ? 'ghost'
    : 'outline';
  const extraClass = action.kind === 'danger'
    ? 'text-red-600 border-red-300 hover:bg-red-50'
    : '';
  return (
    <Button
      size="sm"
      variant={variant as 'default' | 'outline' | 'ghost'}
      disabled={action.disabled}
      onClick={() => onAction(action.onClickId)}
      data-testid={action.testId}
      className={`gap-1.5 ${extraClass}`}
    >
      {Icon && <Icon className="h-3.5 w-3.5" />}
      {action.label}
    </Button>
  );
}

// ────────── Dropzone ──────────

function Dropzone({
  kind, filled, onDrop,
}: {
  kind: 'estimate' | 'agreement';
  filled: boolean;
  onDrop?: (file: File, kind: 'estimate' | 'agreement') => void;
}) {
  const [over, setOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = (files: FileList | null) => {
    if (!files || !files[0]) return;
    const f = files[0];
    if (f.type !== 'application/pdf') {
      toast.error('PDF only.');
      return;
    }
    onDrop?.(f, kind);
  };

  if (filled) {
    const name = kind === 'agreement' ? 'signed_agreement.pdf' : 'estimate.pdf';
    return (
      <div
        className="flex items-center gap-3 rounded-lg border border-slate-200 bg-white p-3"
        data-testid="now-card-dropzone-filled"
      >
        <FileText className="h-5 w-5 text-slate-400 shrink-0" />
        <div className="min-w-0">
          <div className="text-sm font-medium text-slate-800 truncate">{name}</div>
          <div className="text-xs text-slate-500">
            click to preview · <u className="cursor-pointer">replace</u> · <u className="cursor-pointer">remove</u>
          </div>
        </div>
      </div>
    );
  }

  const label = kind === 'agreement' ? 'signed agreement PDF' : 'estimate PDF';
  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf"
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
      />
      <div
        role="button"
        tabIndex={0}
        onClick={() => inputRef.current?.click()}
        onDragEnter={(e) => { e.preventDefault(); setOver(true); }}
        onDragOver={(e) => { e.preventDefault(); setOver(true); }}
        onDragLeave={(e) => {
          if (!e.currentTarget.contains(e.relatedTarget as Node | null)) {
            setOver(false);
          }
        }}
        onDrop={(e) => {
          e.preventDefault();
          setOver(false);
          handleFiles(e.dataTransfer.files);
        }}
        className={[
          'rounded-lg border-2 border-dashed py-8 px-4 text-center cursor-pointer transition-colors',
          over
            ? 'border-sky-500 bg-sky-100'
            : 'border-slate-300 hover:border-sky-400 hover:bg-sky-50',
        ].join(' ')}
        data-testid="now-card-dropzone-empty"
      >
        <div className="text-2xl text-slate-400 mb-1">↓</div>
        <div className="text-sm font-medium text-slate-700">Drag the {label} here</div>
        <div className="text-xs text-slate-500 mt-0.5">
          or <u>click to browse</u> · PDF only
        </div>
      </div>
    </>
  );
}

// ────────── Week-Of picker ──────────

function WeekOfPicker({
  value, onChange,
}: {
  value?: string | null;
  onChange?: (w: string) => void;
}) {
  const weeks = generateWeeks(5);
  return (
    <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 space-y-2">
      <div className="text-sm font-medium text-slate-700">
        <Calendar className="inline h-4 w-4 mr-1 -mt-0.5" />
        Rough <b>Week Of</b> for this job
      </div>
      <div className="flex flex-wrap gap-1.5">
        {weeks.map(w => (
          <button
            key={w}
            type="button"
            onClick={() => onChange?.(w)}
            data-testid={`now-card-weekof-${w.replace(/\s+/g, '-')}`}
            className={[
              'text-xs px-2.5 py-1 rounded-full border transition-colors',
              w === value
                ? 'bg-slate-900 text-white border-slate-900'
                : 'bg-white border-slate-200 text-slate-700 hover:bg-slate-50',
            ].join(' ')}
          >
            Week of {w}
          </button>
        ))}
        <Popover>
          <PopoverTrigger asChild>
            <button
              type="button"
              data-testid="now-card-weekof-pick"
              className="text-xs px-2.5 py-1 rounded-full border border-dashed border-slate-300 text-slate-500 hover:bg-slate-50"
            >
              + pick date…
            </button>
          </PopoverTrigger>
          <PopoverContent className="w-auto p-0" align="start">
            <CalendarPicker
              mode="single"
              selected={undefined}
              onSelect={(d) => {
                if (d) onChange?.(format(d, 'MMM d'));
              }}
            />
          </PopoverContent>
        </Popover>
      </div>
      <p className="text-xs text-slate-500">
        Used only as a target — pin the exact day + crew later in the Jobs tab.
      </p>
    </div>
  );
}

export function generateWeeks(n: number): string[] {
  const out: string[] = [];
  const d = new Date();
  // Monday of this week
  const diff = (d.getDay() + 6) % 7;
  d.setDate(d.getDate() - diff);
  const fmt = new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric' });
  for (let i = 0; i < n; i++) {
    out.push(fmt.format(d));
    d.setDate(d.getDate() + 7);
  }
  return out;
}

// ────────── Tiny HTML allowlist: only <em>, <b> ──────────

export function sanitizeCopy(html: string): string {
  // Remove any tag not in allowlist. Attributes also stripped.
  return html
    .replace(/<(\/?)(?!em\b|b\b)[a-z][a-z0-9]*[^>]*>/gi, '')
    .replace(/<(em|b)(\s[^>]*)?>/gi, '<$1>');
}
