import { useEffect, useMemo, useRef, useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
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
  fmtDur,
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

const TONES = ['toneBlue', 'toneGreen', 'toneViolet', 'toneAmber', 'toneTeal'] as const;
function pickTone(assigneeId: string | null | undefined): string | null {
  if (!assigneeId) return null;
  let h = 0;
  for (let i = 0; i < assigneeId.length; i++) h = (h * 31 + assigneeId.charCodeAt(i)) >>> 0;
  const tone = TONES[h % TONES.length];
  return tone ? styles[tone] ?? null : null;
}

function fmtMonRange(a: Date, b: Date): string {
  const sm = a.toLocaleDateString('en-US', { month: 'short' });
  const em = b.toLocaleDateString('en-US', { month: 'short' });
  const y = b.getFullYear();
  if (sm === em) return `${sm} ${a.getDate()} – ${b.getDate()}, ${y}`;
  return `${sm} ${a.getDate()} – ${em} ${b.getDate()}, ${y}`;
}

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
      if (past) return;
      setDrag({ dayIdx, startSlot: slotIdx, curSlot: slotIdx, moved: false });

      const onMove = (ev: MouseEvent) => {
        const target = (ev.target as HTMLElement | null)?.closest('[data-slot]');
        if (!target) return;
        const di = Number(target.getAttribute('data-day'));
        const si = Number(target.getAttribute('data-slot'));
        if (di !== dayIdx) return;
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

  useEffect(() => {
    return () => {
      dragRef.current = null;
    };
  }, []);

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

  const colLeftPct = (i: number) =>
    `calc(${TIMECOL_PX}px + ${i} * ((100% - ${TIMECOL_PX}px) / 7))`;
  const colWidthPct = `calc((100% - ${TIMECOL_PX}px) / 7)`;
  const todayIdx = days.findIndex((d) => iso(d) === iso(now));
  const NOW_MIN = now.getHours() * 60 + now.getMinutes();
  const showNowLine =
    todayIdx >= 0 && NOW_MIN >= HOUR_START * 60 && NOW_MIN <= HOUR_END * 60;

  const blockTop = (startMin: number) =>
    HEADER_PX + ((startMin - HOUR_START * 60) / SLOT_MIN) * SLOT_PX;
  const blockHeight = (durMin: number) => (durMin / SLOT_MIN) * SLOT_PX - 3;

  const lastDay = days[6] ?? days[0] ?? weekStart;

  return (
    <div className={styles.wkcal} data-testid="schedule-visit-calendar">
      <header className={styles.wkcalHead}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, minWidth: 0 }}>
          <span className={styles.wkLabel}>Week of {fmtMonD(weekStart)}</span>
          <span className={styles.wkRange}>{fmtMonRange(weekStart, lastDay)}</span>
        </div>
        <div className={styles.wkcalNav}>
          <button
            type="button"
            className={styles.navIcon}
            onClick={goPrev}
            data-testid="schedule-visit-week-prev"
            aria-label="Previous week"
          >
            <ChevronLeft size={14} strokeWidth={2.5} />
          </button>
          <button
            type="button"
            className={styles.navToday}
            onClick={goToday}
            data-testid="schedule-visit-week-today"
          >
            Today
          </button>
          <button
            type="button"
            className={styles.navIcon}
            onClick={goNext}
            data-testid="schedule-visit-week-next"
            aria-label="Next week"
          >
            <ChevronRight size={14} strokeWidth={2.5} />
          </button>
        </div>
      </header>

      <div className={styles.wkcalGrid} aria-busy={loadingWeek}>
        <div className={styles.wkcalCorner} />
        {days.map((d, i) => {
          const isWeekend = d.getDay() === 0 || d.getDay() === 6;
          const isToday = iso(d) === iso(now);
          return (
            <div
              key={`h${i}`}
              className={[
                styles.wkcalDaycolHead,
                isToday ? styles.today : '',
                isWeekend ? styles.weekend : '',
              ].filter(Boolean).join(' ')}
            >
              <div className={styles.dow}>
                {d.toLocaleDateString('en-US', { weekday: 'short' })}
              </div>
              <div className={styles.dnum}>{d.getDate()}</div>
            </div>
          );
        })}

        {Array.from({ length: SLOTS_PER_DAY }).flatMap((_, s) => {
          const mins = HOUR_START * 60 + s * SLOT_MIN;
          const isHour = mins % 60 === 0;
          const cells: React.ReactNode[] = [
            <div
              key={`tg${s}`}
              className={`${styles.wkcalTimecell}${isHour ? ' ' + styles.hour : ''}`}
            >
              {isHour ? (() => {
                const h = Math.floor(mins / 60);
                const ap = h >= 12 ? 'p' : 'a';
                const h12 = ((h + 11) % 12) + 1;
                return `${h12} ${ap}`;
              })() : ''}
            </div>,
          ];
          days.forEach((d, di) => {
            const past = isPastSlot(d, mins, now);
            const isWeekend = d.getDay() === 0 || d.getDay() === 6;
            cells.push(
              <div
                key={`c${s}-${di}`}
                data-day={di}
                data-slot={s}
                data-testid={`schedule-visit-slot-${di}-${s}`}
                className={[
                  styles.wkcalSlot,
                  isHour ? styles.hour : '',
                  isWeekend ? styles.weekend : '',
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

        {showNowLine && (
          <div
            className={styles.wkcalNow}
            style={{
              top: `${HEADER_PX + ((NOW_MIN - HOUR_START * 60) / SLOT_MIN) * SLOT_PX}px`,
              left: colLeftPct(todayIdx),
              width: colWidthPct,
            }}
          />
        )}

        {days.map((d, di) => {
          const dISO = iso(d);
          return estimates
            .filter((e) => e.date === dISO)
            .map((e) => {
              const toneCls = pickTone(e.assignedToUserId);
              return (
                <div
                  key={e.id}
                  className={[
                    styles.wkcalEvt,
                    toneCls ?? '',
                    conflictIds.has(e.id) ? styles.conflict : '',
                  ].filter(Boolean).join(' ')}
                  title={`${e.customerName} · ${fmtHM(e.startMin)}–${fmtHM(e.endMin)} · ${e.jobSummary}`}
                  style={{
                    top: `${blockTop(e.startMin)}px`,
                    height: `${blockHeight(e.endMin - e.startMin)}px`,
                    left: `calc(${colLeftPct(di)} + 3px)`,
                    width: `calc(${colWidthPct} - 6px)`,
                  }}
                >
                  <div className={styles.evtName}>{e.customerName}</div>
                  <div className={styles.evtMeta}>
                    {fmtHM(e.startMin)} · {e.jobSummary}
                  </div>
                </div>
              );
            });
        })}

        {pick &&
          (() => {
            const di = days.findIndex((d) => iso(d) === pick.date);
            if (di < 0) return null;
            return (
              <div
                data-testid="schedule-visit-pick"
                className={`${styles.wkcalPick}${hasConflict ? ' ' + styles.warn : ''}`}
                style={{
                  top: `${blockTop(pick.start)}px`,
                  height: `${blockHeight(pick.end - pick.start)}px`,
                  left: `calc(${colLeftPct(di)} + 3px)`,
                  width: `calc(${colWidthPct} - 6px)`,
                }}
              >
                <div>{pickCustomerName}</div>
                <div style={{ fontFamily: 'JetBrains Mono, ui-monospace, monospace', fontSize: 10.5, fontWeight: 600, opacity: 0.9, marginTop: 1 }}>
                  {fmtHM(pick.start)} – {fmtHM(pick.end)}
                </div>
                <span className={styles.pickDur}>{fmtDur(pick.end - pick.start)}</span>
              </div>
            );
          })()}

        {drag &&
          (() => {
            const s1 = Math.min(drag.startSlot, drag.curSlot);
            const s2 = Math.max(drag.startSlot, drag.curSlot) + 1;
            return (
              <div
                className={styles.wkcalDrag}
                style={{
                  top: `${HEADER_PX + s1 * SLOT_PX}px`,
                  height: `${(s2 - s1) * SLOT_PX - 3}px`,
                  left: `calc(${colLeftPct(drag.dayIdx)} + 3px)`,
                  width: `calc(${colWidthPct} - 6px)`,
                }}
              />
            );
          })()}
      </div>

      <footer className={styles.wkcalLegend}>
        <span>
          <span className={styles.legendSw} />
          Existing estimate
        </span>
        <span>
          <span className={`${styles.legendSw} ${styles.legendSwConflict}`} />
          Conflict
        </span>
        <span>
          <span className={`${styles.legendSw} ${styles.pick}`} />
          Your pick
        </span>
        <span className={styles.legendHint}>
          <span className={styles.kbd}>Click</span> pin start ·{' '}
          <span className={styles.kbd}>Drag</span> set range
        </span>
      </footer>
    </div>
  );
}
