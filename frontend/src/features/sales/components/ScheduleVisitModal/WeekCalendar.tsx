import { useEffect, useMemo, useRef, useState } from 'react';
import type { EstimateBlock, Pick } from '../../types/pipeline';
import {
  HOUR_START,
  HOUR_END,
  SLOT_MIN,
  SLOT_PX,
  HEADER_PX,
  TIMECOL_PX,
  SLOTS_PER_DAY,
  iso,
  isPastSlot,
  fmtHM,
  fmtMonD,
  fmtLongDateD,
} from '../../lib/scheduleVisitUtils';
import styles from './ScheduleVisitModal.module.css';

type Props = {
  weekStart: Date;
  now: Date;
  estimates: EstimateBlock[];
  pick: Pick | null;
  loadingWeek: boolean;
  conflicts: EstimateBlock[];
  hasConflict: boolean;
  pickCustomerName: string;
  onWeekChange: (next: Date) => void;
  onSlotClick: (date: string, slotStartMin: number) => void;
  onSlotDrag: (date: string, startMin: number, endExclusiveMin: number) => void;
  onTrack?: (event: 'pick', source: 'click' | 'drag') => void;
};

type DragState = {
  dayIdx: number;
  startSlot: number;
  curSlot: number;
  moved: boolean;
};

export function WeekCalendar({
  weekStart,
  now,
  estimates,
  pick,
  loadingWeek,
  conflicts,
  hasConflict,
  pickCustomerName,
  onWeekChange,
  onSlotClick,
  onSlotDrag,
  onTrack,
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
  const conflictIds = useMemo(
    () => new Set(conflicts.map((c) => c.id)),
    [conflicts],
  );
  const [drag, setDrag] = useState<DragState | null>(null);
  const dragRef = useRef<DragState | null>(null);
  useEffect(() => {
    dragRef.current = drag;
  }, [drag]);

  // ── Mouse handlers (lifted from reference HTML) ──
  const onSlotMouseDown =
    (dayIdx: number, slotIdx: number) => (e: React.MouseEvent) => {
      e.preventDefault();
      const dayDate = days[dayIdx];
      if (!dayDate) return;
      const past = isPastSlot(
        dayDate,
        HOUR_START * 60 + slotIdx * SLOT_MIN,
        now,
      );
      if (past) return; // SPEC §6.3: disallow drag from past slots
      setDrag({ dayIdx, startSlot: slotIdx, curSlot: slotIdx, moved: false });

      const onMove = (ev: MouseEvent) => {
        const target = (ev.target as HTMLElement | null)?.closest('[data-slot]');
        if (!target) return;
        const di = Number(target.getAttribute('data-day'));
        const si = Number(target.getAttribute('data-slot'));
        if (di !== dayIdx) return; // SPEC §6.2: drag locked to origin column
        // SPEC §6.3: clip drag end to today/start-of-day
        const dd = days[dayIdx];
        if (!dd) return;
        if (isPastSlot(dd, HOUR_START * 60 + si * SLOT_MIN, now)) return;
        setDrag((d) =>
          d && d.curSlot !== si ? { ...d, curSlot: si, moved: true } : d,
        );
      };

      const onUp = () => {
        document.removeEventListener('mousemove', onMove);
        document.removeEventListener('mouseup', onUp);
        const d = dragRef.current;
        if (!d) return;
        const dDate = new Date(weekStart);
        dDate.setDate(dDate.getDate() + d.dayIdx);
        const isoDate = iso(dDate);
        const s1 = Math.min(d.startSlot, d.curSlot);
        const s2 = Math.max(d.startSlot, d.curSlot) + 1;
        const startMin = HOUR_START * 60 + s1 * SLOT_MIN;
        const endMin = HOUR_START * 60 + s2 * SLOT_MIN;
        if (d.moved) {
          onSlotDrag(isoDate, startMin, endMin);
          onTrack?.('pick', 'drag');
        } else {
          onSlotClick(isoDate, startMin);
          onTrack?.('pick', 'click');
        }
        setDrag(null);
      };

      document.addEventListener('mousemove', onMove);
      document.addEventListener('mouseup', onUp);
    };

  // Defensive cleanup on unmount: null out the ref so a stray onUp is a no-op.
  useEffect(() => {
    return () => {
      dragRef.current = null;
    };
  }, []);

  // ── Nav handlers (don't touch `pick` per SPEC §3) ──
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
  const goToday = () => {
    const t = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const day = t.getDay();
    const diff = day === 0 ? -6 : 1 - day;
    t.setDate(t.getDate() + diff);
    onWeekChange(t);
  };

  // ── Overlay positioning math (reference HTML) ──
  const colLeftPct = (i: number) =>
    `calc(${TIMECOL_PX}px + ${i} * ((100% - ${TIMECOL_PX}px) / 7))`;
  const colWidthPct = `calc((100% - ${TIMECOL_PX}px) / 7)`;
  const todayIdx = days.findIndex((d) => iso(d) === iso(now));
  const NOW_MIN = now.getHours() * 60 + now.getMinutes();
  const showNowLine =
    todayIdx >= 0 && NOW_MIN >= HOUR_START * 60 && NOW_MIN <= HOUR_END * 60;

  const blockTop = (startMin: number) =>
    HEADER_PX + ((startMin - HOUR_START * 60) / SLOT_MIN) * SLOT_PX;
  const blockHeight = (durMin: number) => (durMin / SLOT_MIN) * SLOT_PX - 2;

  const lastDay = days[6] ?? days[0] ?? weekStart;

  return (
    <div className={styles.wkcal} data-testid="schedule-visit-calendar">
      <header className={styles.wkcalHead}>
        <div>
          <span className={styles.wkLabel}>Week of {fmtMonD(weekStart)}</span>
          <span className={styles.wkRange}>
            {fmtLongDateD(weekStart)} – {fmtLongDateD(lastDay)}
          </span>
        </div>
        <div className={styles.wkcalNav}>
          <button onClick={goPrev} data-testid="schedule-visit-week-prev">
            ← Prev week
          </button>
          <button onClick={goToday} data-testid="schedule-visit-week-today">
            Today
          </button>
          <button onClick={goNext} data-testid="schedule-visit-week-next">
            Next week →
          </button>
        </div>
      </header>

      <div className={styles.wkcalGrid} aria-busy={loadingWeek}>
        {/* Row 1: corner + 7 day-headers */}
        <div className={styles.wkcalCorner} />
        {days.map((d, i) => (
          <div
            key={`h${i}`}
            className={`${styles.wkcalDaycolHead}${
              iso(d) === iso(now) ? ' ' + styles.today : ''
            }`}
          >
            <div className={styles.dow}>
              {d.toLocaleDateString('en-US', { weekday: 'short' })}
            </div>
            <div className={styles.dnum}>{d.getDate()}</div>
          </div>
        ))}

        {/* 28 rows of [time-gutter, 7 slots] */}
        {Array.from({ length: SLOTS_PER_DAY }).flatMap((_, s) => {
          const mins = HOUR_START * 60 + s * SLOT_MIN;
          const isHour = mins % 60 === 0;
          const cells: React.ReactNode[] = [
            <div
              key={`tg${s}`}
              className={`${styles.wkcalTimecell}${
                isHour ? ' ' + styles.hour : ''
              }`}
            >
              {isHour ? fmtHM(mins) : ''}
            </div>,
          ];
          days.forEach((d, di) => {
            const past = isPastSlot(d, mins, now);
            cells.push(
              <div
                key={`c${s}-${di}`}
                data-day={di}
                data-slot={s}
                data-testid={`schedule-visit-slot-${di}-${s}`}
                className={[
                  styles.wkcalSlot,
                  isHour ? styles.hour : '',
                  past ? styles.past : '',
                ]
                  .filter(Boolean)
                  .join(' ')}
                onMouseDown={past ? undefined : onSlotMouseDown(di, s)}
              />,
            );
          });
          return cells;
        })}

        {/* Now-line */}
        {showNowLine && (
          <div
            className={styles.wkcalNow}
            style={{
              top: `${
                HEADER_PX + ((NOW_MIN - HOUR_START * 60) / SLOT_MIN) * SLOT_PX
              }px`,
              left: colLeftPct(todayIdx),
              width: colWidthPct,
            }}
          />
        )}

        {/* Estimate blocks */}
        {days.map((d, di) => {
          const dISO = iso(d);
          return estimates
            .filter((e) => e.date === dISO)
            .map((e) => (
              <div
                key={e.id}
                className={`${styles.wkcalEvt}${
                  conflictIds.has(e.id) ? ' ' + styles.conflict : ''
                }`}
                title={`${e.customerName} · ${fmtHM(e.startMin)}–${fmtHM(
                  e.endMin,
                )} · ${e.jobSummary}`}
                style={{
                  top: `${blockTop(e.startMin)}px`,
                  height: `${blockHeight(e.endMin - e.startMin)}px`,
                  left: `calc(${colLeftPct(di)} + 2px)`,
                  width: `calc(${colWidthPct} - 4px)`,
                }}
              >
                <div className={styles.evtName}>{e.customerName}</div>
                <div className={styles.evtMeta}>
                  {fmtHM(e.startMin)} · {e.jobSummary}
                </div>
              </div>
            ));
        })}

        {/* Pick block */}
        {pick &&
          (() => {
            const di = days.findIndex((d) => iso(d) === pick.date);
            if (di < 0) return null;
            return (
              <div
                data-testid="schedule-visit-pick"
                className={`${styles.wkcalPick}${
                  hasConflict ? ' ' + styles.warn : ''
                }`}
                style={{
                  top: `${blockTop(pick.start)}px`,
                  height: `${blockHeight(pick.end - pick.start)}px`,
                  left: `calc(${colLeftPct(di)} + 2px)`,
                  width: `calc(${colWidthPct} - 4px)`,
                }}
              >
                <div>
                  {pickCustomerName} · {fmtHM(pick.start)}
                </div>
                <span className={styles.pickDur}>
                  {(() => {
                    const m = pick.end - pick.start;
                    if (m < 60) return `${m} min`;
                    const h = Math.floor(m / 60),
                      r = m % 60;
                    return r === 0 ? `${h} hr` : `${h}h ${r}m`;
                  })()}
                </span>
              </div>
            );
          })()}

        {/* Drag ghost */}
        {drag &&
          (() => {
            const s1 = Math.min(drag.startSlot, drag.curSlot);
            const s2 = Math.max(drag.startSlot, drag.curSlot) + 1;
            return (
              <div
                className={styles.wkcalDrag}
                style={{
                  top: `${HEADER_PX + s1 * SLOT_PX}px`,
                  height: `${(s2 - s1) * SLOT_PX - 2}px`,
                  left: `calc(${colLeftPct(drag.dayIdx)} + 2px)`,
                  width: `calc(${colWidthPct} - 4px)`,
                }}
              />
            );
          })()}
      </div>

      <footer className={styles.wkcalLegend}>
        <span>
          <span className={styles.legendSw} />
          Existing estimate (read-only)
        </span>
        <span>
          <span className={`${styles.legendSw} ${styles.pick}`} />
          Your pick
        </span>
        <span style={{ marginLeft: 'auto', color: '#8a8a8a' }}>
          Click to pin · Drag to set range · 6 AM – 8 PM · 30-min slots
        </span>
      </footer>
    </div>
  );
}
