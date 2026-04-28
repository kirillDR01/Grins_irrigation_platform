/**
 * SchedulingTray — fixed assignment bar pinned to the bottom of PickJobsPage.
 * Requirements: 8.1–8.6, 9.1–9.6, 10.1–10.6, 11.1–11.5, 15.5, 15.6
 *
 * CRITICAL: always rendered — never conditionally hidden.
 */

import { Clock, ChevronDown, ChevronUp, CalendarPlus } from 'lucide-react';
import { Input } from '@/components/ui/input';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import type { Staff } from '@/features/staff/types';
import type { JobReadyToSchedule, PerJobTimeMap } from '../types/pick-jobs';
import { computeJobTimes } from '../types/pick-jobs';

interface Props {
  selectedJobIds: Set<string>;
  /** Visible subset of selected jobs (filtered by current facets). */
  selectedJobs: JobReadyToSchedule[];
  /** Full count of selected jobs, including those hidden by filters. */
  totalSelectedCount: number;
  staff: Staff[];

  assignDate: string;
  onAssignDateChange: (s: string) => void;
  assignStaffId: string;
  onAssignStaffIdChange: (s: string) => void;
  startTime: string;
  onStartTimeChange: (s: string) => void;
  duration: number;
  onDurationChange: (n: number) => void;

  perJobTimes: PerJobTimeMap;
  onPerJobTimesChange: (f: PerJobTimeMap | ((prev: PerJobTimeMap) => PerJobTimeMap)) => void;
  showTimeAdjust: boolean;
  onShowTimeAdjustChange: (b: boolean) => void;

  isAssigning: boolean;
  onAssign: () => void;
  onClearSelection: () => void;
}

const pluralize = (word: string, n: number): string =>
  n === 1 ? word : (word === 'city' ? 'cities' : `${word}s`);

export function SchedulingTray(p: Props) {
  const n = p.totalSelectedCount;
  const isActive = n > 0;
  const hiddenCount = n - p.selectedJobs.length;

  // Cascade times so auto-mode jobs flow from last override's end.
  const computedTimes = computeJobTimes(p.selectedJobs, p.startTime, p.duration, p.perJobTimes);

  const overlapWarning = Object.entries(p.perJobTimes).some(
    ([, t]) => t.end && t.start && t.end <= t.start,
  );
  const disableAssign = n === 0 || !p.assignStaffId || p.isAssigning || overlapWarning;

  const helper =
    n === 0 ? 'Pick jobs above to continue' :
    !p.assignStaffId ? 'Pick a staff member to continue' :
    overlapWarning ? 'Selected job times overlap — review per-job adjustments' :
    null;

  // Derive summary: cities count and total hours from the visible selected jobs.
  // (Hidden-by-filter jobs are not on hand to compute against; the count pill
  // still uses totalSelectedCount and we surface the discrepancy via hiddenCount.)
  const cities = new Set(p.selectedJobs.map(j => j.city).filter(Boolean));
  const citiesCount = cities.size;
  const totalMinutes = p.selectedJobs.reduce(
    (sum, j) => sum + (j.estimated_duration_minutes ?? p.duration),
    0,
  );
  const totalHoursStr = (totalMinutes / 60).toFixed(1).replace(/\.0$/, '');

  return (
    <section
      aria-label="Scheduling assignment"
      data-testid="scheduling-tray"
      className="pjp-sched-bar"
      data-empty={!isActive}
    >
      <div className="pjp-sched-bar-inner">

        {/* Header */}
        <div className="pjp-bar-header">
          <h3 className="pjp-bar-title" aria-live="polite">
            {isActive ? (
              <>
                Schedule{' '}
                <span className="pjp-bar-num pjp-mono" data-testid="tray-selected-count">{n}</span>{' '}
                job{n !== 1 ? 's' : ''}
              </>
            ) : (
              <>
                <span data-testid="tray-selected-count" style={{ display: 'none' }}>0</span>
                Schedule jobs <span className="pjp-bar-muted">— pick some above</span>
              </>
            )}
          </h3>
          {isActive && (
            <button
              type="button"
              className="pjp-bar-clear"
              onClick={p.onClearSelection}
              data-testid="tray-clear-selection"
            >
              Clear selection
            </button>
          )}
        </div>

        {hiddenCount > 0 && (
          <p className="pjp-bar-hidden-note">
            {hiddenCount} selected job{hiddenCount !== 1 ? 's are' : ' is'} hidden by current filters.
          </p>
        )}

        {/* Field row */}
        <div className="pjp-bar-fields">
          <div className="pjp-field">
            <span className="pjp-field-label">Date</span>
            <Input
              type="date"
              value={p.assignDate}
              onChange={e => p.onAssignDateChange(e.target.value)}
              data-testid="tray-date"
            />
          </div>
          <div className="pjp-field">
            <span className="pjp-field-label">Staff member</span>
            <Select value={p.assignStaffId} onValueChange={p.onAssignStaffIdChange}>
              <SelectTrigger data-testid="tray-staff">
                <SelectValue placeholder="Select staff…" />
              </SelectTrigger>
              <SelectContent>
                {p.staff.map(s => (
                  <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="pjp-field">
            <span className="pjp-field-label">Start time</span>
            <Input
              type="time"
              value={p.startTime}
              onChange={e => p.onStartTimeChange(e.target.value)}
              data-testid="tray-start-time"
            />
          </div>
          <div className="pjp-field">
            <span className="pjp-field-label">Default duration (min)</span>
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

        {/* Per-job time adjustments */}
        {isActive && (
          <>
            <button
              type="button"
              className={`pjp-pjt-toggle${p.showTimeAdjust ? ' open' : ''}`}
              onClick={() => p.onShowTimeAdjustChange(!p.showTimeAdjust)}
              data-testid="tray-time-adjust-toggle"
            >
              <Clock className="h-3 w-3" />
              Per-job time adjustments
              <span className="pjp-pjt-badge pjp-mono">{p.selectedJobs.length}</span>
              {p.showTimeAdjust ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            </button>

            {p.showTimeAdjust && (
              <div data-testid="tray-time-adjust-table" className="pjp-pjt-table">
                <div className="pjp-pjt-row pjp-pjt-head">
                  <div>Customer</div>
                  <div>Job type</div>
                  <div>Start</div>
                  <div>End</div>
                </div>
                {p.selectedJobs.map((j, i) => {
                  const computed = computedTimes[j.job_id] ?? { start: p.startTime, end: '' };
                  const override = p.perJobTimes[j.job_id];
                  return (
                    <div key={j.job_id} className="pjp-pjt-row">
                      <div className="pjp-pjt-cust">
                        <span className="pjp-dot blue">{i + 1}</span>
                        <div>
                          <div className="pjp-pjt-name">{j.customer_name}</div>
                          {j.city && <div className="pjp-pjt-jt">{j.city}</div>}
                        </div>
                      </div>
                      <div className="pjp-pjt-jt">{j.job_type}</div>
                      <div>
                        <Input
                          type="time"
                          value={override?.start ?? computed.start}
                          onChange={e => p.onPerJobTimesChange(prev => ({
                            ...prev,
                            [j.job_id]: { ...(prev[j.job_id] ?? { start: '', end: '' }), start: e.target.value },
                          }))}
                        />
                      </div>
                      <div>
                        <Input
                          type="time"
                          value={override?.end ?? computed.end}
                          onChange={e => p.onPerJobTimesChange(prev => ({
                            ...prev,
                            [j.job_id]: { ...(prev[j.job_id] ?? { start: '', end: '' }), end: e.target.value },
                          }))}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </>
        )}

        {/* Footer */}
        <div className="pjp-bar-footer">
          <div className="pjp-footer-meta">
            <span className="pjp-count-pill pjp-mono" aria-hidden="true">{n}</span>
            {isActive ? (
              <span className="pjp-footer-summary">
                {n} {pluralize('job', n)} selected
                {citiesCount > 0 && <> · {citiesCount} {pluralize('city', citiesCount)}</>}
                {totalMinutes > 0 && <> · ~{totalHoursStr}h total</>}
              </span>
            ) : (
              <span className="pjp-footer-helper">{helper ?? `${n} job${n !== 1 ? 's' : ''} selected`}</span>
            )}
            {isActive && helper && (
              <span className="pjp-footer-helper">{helper}</span>
            )}
          </div>
          <button
            type="button"
            onClick={p.onAssign}
            disabled={disableAssign}
            data-testid="tray-assign-btn"
            className="pjp-bar-assign-cta"
          >
            <CalendarPlus className="h-4 w-4" />
            {p.isAssigning
              ? 'Assigning…'
              : n > 0 ? `Assign ${n} Job${n !== 1 ? 's' : ''}` : 'Assign'}
          </button>
        </div>
      </div>
    </section>
  );
}
