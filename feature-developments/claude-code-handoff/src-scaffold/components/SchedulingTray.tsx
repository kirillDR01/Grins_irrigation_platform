/**
 * SCAFFOLD — SchedulingTray (persistent)
 *
 * Drop into: frontend/src/features/schedule/components/SchedulingTray.tsx
 * See SPEC §6.3 for full rules.
 *
 * CRITICAL: this component is always rendered. It has two visual states —
 * idle (no selection) and active (≥1 selected). Do not add any
 * conditional `if (!selection.size) return null`.
 */

import { Clock, ChevronDown, ChevronUp, CalendarPlus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import type {
  JobReadyToSchedule, PerJobTimeMap, Staff,
} from '../types/pick-jobs';

interface Props {
  selectedJobIds: Set<string>;
  selectedJobs:   JobReadyToSchedule[]; // visible + selected
  totalSelectedCount: number;           // includes hidden-by-filter selections
  staff: Staff[];

  assignDate:         string;
  onAssignDateChange: (s: string) => void;
  assignStaffId:      string;
  onAssignStaffIdChange: (s: string) => void;
  startTime:          string;
  onStartTimeChange:  (s: string) => void;
  duration:           number;
  onDurationChange:   (n: number) => void;

  perJobTimes:        PerJobTimeMap;
  onPerJobTimesChange: (f: PerJobTimeMap | ((prev: PerJobTimeMap) => PerJobTimeMap)) => void;
  showTimeAdjust:     boolean;
  onShowTimeAdjustChange: (b: boolean) => void;

  isAssigning:     boolean;
  onAssign:        () => void;
  onClearSelection: () => void;
}

export function SchedulingTray(p: Props) {
  const n        = p.totalSelectedCount;
  const isActive = n > 0;
  const hiddenCount = n - p.selectedJobs.length;

  // TODO: compute per-job cascade times (port from JobPickerPopup.computeJobTimes)
  const computedTimes: Record<string, { start: string; end: string }> = {};

  const overlapWarning = Object.entries(p.perJobTimes).some(([, t]) => t.end && t.start && t.end <= t.start);
  const disableAssign = n === 0 || !p.assignStaffId || p.isAssigning || overlapWarning;

  const helper =
    n === 0             ? 'Pick jobs above to continue' :
    !p.assignStaffId    ? 'Pick a staff member to continue' :
    overlapWarning      ? 'Selected job times overlap — review per-job adjustments' :
    null;

  return (
    <section
      aria-label="Scheduling assignment"
      className="border-t border-border bg-card shadow-[0_-4px_12px_rgba(0,0,0,0.04)]"
    >
      <div className="mx-auto max-w-screen-2xl px-6 py-4 space-y-3">

        {/* Header ────────────────────────────────────────────── */}
        <div className="flex items-center justify-between">
          <div aria-live="polite" className="text-base font-semibold">
            {isActive
              ? <>Schedule <span className="text-teal-700">{n}</span> job{n !== 1 ? 's' : ''}</>
              : <span className="font-normal text-muted-foreground">No jobs selected yet — pick some above</span>}
          </div>
          {isActive && (
            <button
              type="button"
              className="text-xs text-teal-600 hover:text-teal-700"
              onClick={p.onClearSelection}
              data-testid="tray-clear-selection"
            >
              Clear selection
            </button>
          )}
        </div>

        {hiddenCount > 0 && (
          <p className="text-xs text-muted-foreground">
            {hiddenCount} selected job{hiddenCount !== 1 ? 's are' : ' is'} hidden by current filters.
          </p>
        )}

        {/* Fields ────────────────────────────────────────────── */}
        <div className="grid grid-cols-2 lg:grid-cols-[200px_260px_160px_160px_1fr] gap-3 items-end">
          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">Date</Label>
            <Input
              type="date"
              value={p.assignDate}
              onChange={e => p.onAssignDateChange(e.target.value)}
              data-testid="tray-date"
            />
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">Staff member</Label>
            <Select value={p.assignStaffId} onValueChange={p.onAssignStaffIdChange}>
              <SelectTrigger data-testid="tray-staff"><SelectValue placeholder="Select staff…" /></SelectTrigger>
              <SelectContent>
                {p.staff.map(s => <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">Start time</Label>
            <Input
              type="time"
              value={p.startTime}
              onChange={e => p.onStartTimeChange(e.target.value)}
              data-testid="tray-start-time"
            />
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">Default duration (min)</Label>
            <Input
              type="number"
              min={15}
              step={15}
              value={p.duration}
              onChange={e => p.onDurationChange(Number(e.target.value) || 60)}
              data-testid="tray-duration"
            />
          </div>
        </div>

        {/* Per-job adjustments toggle — hidden in idle state */}
        {isActive && (
          <>
            <button
              type="button"
              className="flex items-center gap-1 text-xs text-teal-600 hover:text-teal-700"
              onClick={() => p.onShowTimeAdjustChange(!p.showTimeAdjust)}
              data-testid="tray-time-adjust-toggle"
            >
              <Clock className="h-3 w-3" />
              Per-job time adjustments
              {p.showTimeAdjust ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            </button>

            {p.showTimeAdjust && (
              <div
                data-testid="tray-time-adjust-table"
                className="rounded-lg border border-border max-h-[150px] overflow-y-auto"
              >
                <table className="w-full text-xs">
                  <thead className="bg-slate-50 sticky top-0">
                    <tr className="text-left text-muted-foreground">
                      <th className="p-2">Customer</th>
                      <th className="p-2">Job type</th>
                      <th className="p-2">Start</th>
                      <th className="p-2">End</th>
                    </tr>
                  </thead>
                  <tbody>
                    {p.selectedJobs.map(j => {
                      const t = computedTimes[j.job_id] ?? { start: p.startTime, end: '' };
                      return (
                        <tr key={j.job_id} className="border-t border-slate-100">
                          <td className="p-2 text-foreground">{j.customer_name}</td>
                          <td className="p-2 text-muted-foreground">{j.job_type}</td>
                          <td className="p-2">
                            <Input
                              type="time"
                              value={p.perJobTimes[j.job_id]?.start ?? t.start}
                              onChange={e => p.onPerJobTimesChange(prev => ({
                                ...prev,
                                [j.job_id]: { ...(prev[j.job_id] ?? { start: '', end: '' }), start: e.target.value },
                              }))}
                              className="h-7 text-xs w-[100px]"
                            />
                          </td>
                          <td className="p-2">
                            <Input
                              type="time"
                              value={p.perJobTimes[j.job_id]?.end ?? t.end}
                              onChange={e => p.onPerJobTimesChange(prev => ({
                                ...prev,
                                [j.job_id]: { ...(prev[j.job_id] ?? { start: '', end: '' }), end: e.target.value },
                              }))}
                              className="h-7 text-xs w-[100px]"
                            />
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}

        {/* Assign action ─────────────────────────────────────── */}
        <div className="flex items-center justify-between">
          <p className="text-xs text-muted-foreground">{helper ?? `${n} job${n !== 1 ? 's' : ''} selected`}</p>
          <Button
            onClick={p.onAssign}
            disabled={disableAssign}
            data-testid="tray-assign-btn"
            className="bg-teal-500 hover:bg-teal-600 text-white"
          >
            <CalendarPlus className="mr-2 h-4 w-4" />
            {p.isAssigning
              ? 'Assigning…'
              : n > 0 ? `Assign ${n} Job${n !== 1 ? 's' : ''}` : 'Assign'}
          </Button>
        </div>
      </div>
    </section>
  );
}
