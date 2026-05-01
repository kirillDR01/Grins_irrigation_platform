/**
 * NowLine — vertical "now" indicator overlaid on the day-mode time axis.
 *
 * Updates every 60s. Renders nothing when the current time is outside the
 * visible window (DAY_START_MIN..DAY_END_MIN); the parent passes `date`
 * and only mounts <NowLine> when that date equals today.
 */

import { useEffect, useState, type CSSProperties } from 'react';
import { DAY_END_MIN, DAY_START_MIN, minutesToPercent } from './utils';

export interface NowLineProps {
  /**
   * Optional override (used by tests) — in minutes-since-midnight.
   * When omitted the component reads from `new Date()` and reschedules
   * itself every 60 seconds.
   */
  nowMinutes?: number;
}

function currentMinutes(): number {
  const d = new Date();
  return d.getHours() * 60 + d.getMinutes();
}

export function NowLine({ nowMinutes }: NowLineProps) {
  const [tickMinutes, setTickMinutes] = useState<number>(
    () => nowMinutes ?? currentMinutes()
  );

  useEffect(() => {
    if (nowMinutes !== undefined) return;
    const id = window.setInterval(() => {
      setTickMinutes(currentMinutes());
    }, 60_000);
    return () => window.clearInterval(id);
  }, [nowMinutes]);

  const minutes = nowMinutes ?? tickMinutes;
  if (minutes < DAY_START_MIN || minutes > DAY_END_MIN) {
    return null;
  }

  const leftPct = minutesToPercent(minutes);
  const style: CSSProperties = {
    left: `${leftPct}%`,
  };

  return (
    <div
      data-testid="now-line"
      aria-hidden
      className="pointer-events-none absolute top-0 bottom-0 w-px bg-rose-500 z-20"
      style={style}
    >
      <div className="absolute -top-1 -left-[3px] h-1.5 w-1.5 rounded-full bg-rose-500" />
    </div>
  );
}
