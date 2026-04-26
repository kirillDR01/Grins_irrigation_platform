import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useStaff } from '@/features/staff/hooks/useStaff';
import type { Pick } from '../../types/pipeline';

// Radix Select v2.2.6 disallows empty-string values, so use a sentinel for "Unassigned".
// Map null ↔ UNASSIGNED at the boundary; the rest of the codebase only sees null or a real UUID.
const UNASSIGNED = '__none__';

type Props = {
  pick: Pick | null;
  durationMin: 30 | 60 | 90 | 120;
  assignedToUserId: string | null;
  internalNotes: string;
  onDateChange: (iso: string) => void;
  onStartChange: (mins: number) => void;
  onDurationChange: (m: 30 | 60 | 90 | 120) => void;
  onAssigneeChange: (id: string | null) => void;
  onNotesChange: (s: string) => void;
};

export function ScheduleFields({
  pick,
  durationMin,
  assignedToUserId,
  internalNotes,
  onDateChange,
  onStartChange,
  onDurationChange,
  onAssigneeChange,
  onNotesChange,
}: Props) {
  const { data: staffData } = useStaff({ is_active: true });
  const dateValue = pick?.date ?? '';
  const timeValue = pick
    ? `${String(Math.floor(pick.start / 60)).padStart(2, '0')}:${String(
        pick.start % 60,
      ).padStart(2, '0')}`
    : '';

  return (
    <div className="space-y-3.5 mt-4">
      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label
            htmlFor="schedule-visit-date"
            className="text-xs uppercase tracking-wider text-slate-500 font-bold"
          >
            Date
          </Label>
          <Input
            id="schedule-visit-date"
            data-testid="schedule-visit-date"
            type="date"
            className="font-mono font-semibold"
            value={dateValue}
            onChange={(e) => onDateChange(e.target.value)}
          />
        </div>
        <div>
          <Label
            htmlFor="schedule-visit-start-time"
            className="text-xs uppercase tracking-wider text-slate-500 font-bold"
          >
            Start time
          </Label>
          <Input
            id="schedule-visit-start-time"
            data-testid="schedule-visit-start-time"
            type="time"
            step={1800}
            className="font-mono font-semibold"
            value={timeValue}
            onChange={(e) => {
              const parts = e.target.value.split(':').map(Number);
              const hh = parts[0];
              const mm = parts[1] ?? 0;
              if (hh !== undefined && !Number.isNaN(hh)) {
                onStartChange(hh * 60 + mm);
              }
            }}
          />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label
            htmlFor="schedule-visit-assignee"
            className="text-xs uppercase tracking-wider text-slate-500 font-bold"
          >
            Assigned to
          </Label>
          <Select
            value={assignedToUserId ?? UNASSIGNED}
            onValueChange={(v) =>
              onAssigneeChange(v === UNASSIGNED ? null : v)
            }
          >
            <SelectTrigger
              id="schedule-visit-assignee"
              data-testid="schedule-visit-assignee"
            >
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={UNASSIGNED}>— Unassigned —</SelectItem>
              {(staffData?.items ?? []).map((s) => (
                <SelectItem key={s.id} value={s.id}>
                  {s.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div>
          <Label
            htmlFor="schedule-visit-duration"
            className="text-xs uppercase tracking-wider text-slate-500 font-bold"
          >
            Duration
          </Label>
          <Select
            value={String(durationMin)}
            onValueChange={(v) =>
              onDurationChange(Number(v) as 30 | 60 | 90 | 120)
            }
          >
            <SelectTrigger
              id="schedule-visit-duration"
              data-testid="schedule-visit-duration"
              className="font-mono font-semibold"
            >
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="30">30 min</SelectItem>
              <SelectItem value="60">1 hr</SelectItem>
              <SelectItem value="90">1.5 hr</SelectItem>
              <SelectItem value="120">2 hr</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>
      <div>
        <Label
          htmlFor="schedule-visit-notes"
          className="text-xs uppercase tracking-wider text-slate-500 font-bold"
        >
          Internal notes (optional)
        </Label>
        <Textarea
          id="schedule-visit-notes"
          data-testid="schedule-visit-notes"
          value={internalNotes}
          placeholder="Gate code 4412. Large corner lot, sketched zones in intake call…"
          onChange={(e) => onNotesChange(e.target.value)}
          rows={3}
        />
      </div>
    </div>
  );
}
