// WeekCalendar.tsx
// 7-day grid: 6 AM – 8 PM, 30-min slots. Read-only existing estimate blocks +
// one editable "pick" block. Click to pin a start, drag to set a range.
//
// This scaffold is the React shape — the rendering logic mirrors the
// reference HTML's `buildGrid` / `paintOverlays`. Lift implementations from
// the reference verbatim (it's vanilla JS, no port hazards).

import React, { useEffect, useMemo, useRef, useState } from 'react';
import type { EstimateBlock, Pick } from './data-shapes';
import { SLOT_SIZE_MIN } from './useScheduleVisit';

const HOUR_START = 6;
const HOUR_END = 20;
const SLOT_PX = 22;
const SLOTS_PER_DAY = ((HOUR_END - HOUR_START) * 60) / SLOT_SIZE_MIN;

type Props = {
  weekStart: Date;
  now: Date;
  estimates: EstimateBlock[];
  pick: Pick | null;
  loadingWeek: boolean;
  conflicts: EstimateBlock[];
  onWeekChange: (next: Date) => void;
  onSlotClick: (date: string, slotStartMin: number) => void;
  onSlotDrag: (date: string, startMin: number, endExclusiveMin: number) => void;
};

export function WeekCalendar({
  weekStart,
  now,
  estimates,
  pick,
  loadingWeek,
  conflicts,
  onWeekChange,
  onSlotClick,
  onSlotDrag,
}: Props) {
  const days = useMemo(
    () =>
      Array.from({ length: 7 }, (_, i) => {
        const d = new Date(weekStart);
        d.setDate(d.getDate() + i);
        return d;
      }),
    [weekStart],
  );

  const conflictIds = useMemo(() => new Set(conflicts.map((c) => c.id)), [conflicts]);

  // Drag state lives here — calendar-local interaction concern.
  const [drag, setDrag] = useState<null | {
    dayIdx: number;
    startSlot: number;
    curSlot: number;
    moved: boolean;
  }>(null);

  const gridRef = useRef<HTMLDivElement>(null);

  // Mouse handlers — see SPEC.md §5/§6.2 for constraints.
  const onMouseDown = (dayIdx: number, slotIdx: number) => (e: React.MouseEvent) => {
    e.preventDefault();
    setDrag({ dayIdx, startSlot: slotIdx, curSlot: slotIdx, moved: false });

    const onMove = (ev: MouseEvent) => {
      const target = (ev.target as HTMLElement)?.closest('[data-slot]');
      if (!target) return;
      const di = Number(target.getAttribute('data-day'));
      const si = Number(target.getAttribute('data-slot'));
      if (di !== dayIdx) return; // §6.2: drag locked to origin column
      setDrag((d) =>
        d && d.curSlot !== si ? { ...d, curSlot: si, moved: true } : d,
      );
    };

    const onUp = () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
      setDrag((d) => {
        if (!d) return null;
        const dayDate = new Date(weekStart);
        dayDate.setDate(dayDate.getDate() + d.dayIdx);
        const isoDate = iso(dayDate);
        const s1 = Math.min(d.startSlot, d.curSlot);
        const s2 = Math.max(d.startSlot, d.curSlot) + 1;
        const startMin = HOUR_START * 60 + s1 * SLOT_SIZE_MIN;
        const endMin = HOUR_START * 60 + s2 * SLOT_SIZE_MIN;
        if (d.moved) onSlotDrag(isoDate, startMin, endMin);
        else onSlotClick(isoDate, startMin);
        return null;
      });
    };

    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
  };

  const goPrev = () => {
    const d = new Date(weekStart);
    d.setDate(d.getDate() - 7);
    onWeekChange(d);
  };
  const goNext = () => {
    const d = new Date(weekStart);
    d.setDate(d.getDate() + 7);
    onWeekChange(d);
  };
  const goToday = () => onWeekChange(startOfWeek(now));

  return (
    <div className="wkcal">
      <header className="wkcal-head">
        <div>
          <span className="wk-label">Week of {fmtMonD(weekStart)}</span>
          <span className="wk-range">
            {fmtLong(weekStart)} – {fmtLong(days[6])}
          </span>
        </div>
        <div className="wkcal-nav">
          <button onClick={goPrev}>← Prev week</button>
          <button onClick={goToday} className="today">Today</button>
          <button onClick={goNext}>Next week →</button>
        </div>
      </header>

      <div ref={gridRef} className="wkcal-grid" aria-busy={loadingWeek}>
        {/* Render-only — see reference HTML's buildGrid for the exact DOM.   */}
        {/* Implementation guidance:                                          */}
        {/*   1. corner cell + 7 day-headers in row 1                         */}
        {/*   2. 28 rows of [time-gutter, 7 slots] (SLOTS_PER_DAY = 28)       */}
        {/*   3. absolutely-positioned <EstimateBlockView>s + <PickView>      */}
        {/*      layered on top, positioned by minute math.                   */}
        {/* Keep slot cells as <div data-day data-slot> so the global drag    */}
        {/* listener (above) can read them.                                   */}
        <CalendarBody
          days={days}
          now={now}
          estimates={estimates}
          conflictIds={conflictIds}
          pick={pick}
          drag={drag}
          onMouseDown={onMouseDown}
        />
      </div>

      <footer className="wkcal-legend">
        <span><span className="sw" />Existing estimate (read-only)</span>
        <span><span className="sw pick" />Your pick</span>
        <span style={{ marginLeft: 'auto', color: 'var(--ink-faint)' }}>
          Click to pin · Drag to set range · 6 AM – 8 PM · 30-min slots
        </span>
      </footer>
    </div>
  );
}

// ----------------------------------------------------------------------------
// Sketch of the body — replace with the reference's render logic, then
// extract into its own file if it grows.

function CalendarBody(props: {
  days: Date[];
  now: Date;
  estimates: EstimateBlock[];
  conflictIds: Set<string>;
  pick: Pick | null;
  drag: { dayIdx: number; startSlot: number; curSlot: number; moved: boolean } | null;
  onMouseDown: (dayIdx: number, slotIdx: number) => (e: React.MouseEvent) => void;
}) {
  const { days, now, estimates, conflictIds, pick, drag, onMouseDown } = props;
  const cells: React.ReactNode[] = [];

  // header row
  cells.push(<div key="corner" className="wkcal-corner" />);
  days.forEach((d, i) => {
    const isToday = sameYMD(d, now);
    cells.push(
      <div key={`h${i}`} className={`wkcal-daycol-head${isToday ? ' today' : ''}`}>
        <div className="dow">{d.toLocaleDateString('en-US', { weekday: 'short' })}</div>
        <div className="dnum">{d.getDate()}</div>
      </div>,
    );
  });

  // slot rows
  for (let s = 0; s < SLOTS_PER_DAY; s++) {
    const mins = HOUR_START * 60 + s * SLOT_SIZE_MIN;
    const isHour = mins % 60 === 0;
    cells.push(
      <div key={`tg${s}`} className={`wkcal-timecell${isHour ? ' hour' : ''}`}>
        {isHour ? fmtHM(mins) : ''}
      </div>,
    );
    days.forEach((d, di) => {
      const past = isPastSlot(d, mins, now);
      cells.push(
        <div
          key={`c${s}-${di}`}
          data-day={di}
          data-slot={s}
          className={`wkcal-slot${isHour ? ' hour' : ''}${past ? ' past' : ''}`}
          onMouseDown={past ? undefined : onMouseDown(di, s)}
        />,
      );
    });
  }

  // overlays — see reference for exact positioning math
  // TODO: render <EstimateBlockView>, <PickView>, <NowLine>, <DragGhost>
  return <>{cells}</>;
}

// ---- helpers ----
function iso(d: Date) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}
function sameYMD(a: Date, b: Date) {
  return iso(a) === iso(b);
}
function startOfWeek(d: Date) {
  const nd = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const day = nd.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  nd.setDate(nd.getDate() + diff);
  return nd;
}
function isPastSlot(day: Date, slotMin: number, now: Date) {
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  if (day < today) return true;
  if (sameYMD(day, now) && slotMin < now.getHours() * 60 + now.getMinutes()) return true;
  return false;
}
function fmtHM(mins: number) {
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  const ap = h >= 12 ? 'PM' : 'AM';
  const h12 = ((h + 11) % 12) + 1;
  return `${h12}:${String(m).padStart(2, '0')} ${ap}`;
}
function fmtMonD(d: Date) {
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}
function fmtLong(d: Date) {
  return d.toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}
