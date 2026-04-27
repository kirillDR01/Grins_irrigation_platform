// ScheduleFields.tsx
// Date / Start time / Assignee / Duration / Notes fields.
// Pure controlled component — all values come from `useScheduleVisit`.

import React from 'react';
import type { Pick } from './data-shapes';
// import { TextField, Select, DateInput, TimeInput, TextArea } from '@/components';

type Props = {
  pick: Pick | null;
  durationMin: 30 | 60 | 90 | 120;
  assignedTo: string;
  internalNotes: string;
  onDateChange: (iso: string) => void;
  onStartChange: (mins: number) => void;
  onDurationChange: (min: 30 | 60 | 90 | 120) => void;
  onAssigneeChange: (id: string) => void;
  onNotesChange: (s: string) => void;
};

const ASSIGNEES = [
  { id: 'me', label: 'Kirill (me)' },
  { id: 'mike', label: 'Mike R.' },
  { id: 'team', label: 'Team — any avail.' },
];

export function ScheduleFields({
  pick,
  durationMin,
  assignedTo,
  internalNotes,
  onDateChange,
  onStartChange,
  onDurationChange,
  onAssigneeChange,
  onNotesChange,
}: Props) {
  const dateValue = pick?.date ?? '';
  const timeValue = pick
    ? `${String(Math.floor(pick.start / 60)).padStart(2, '0')}:${String(pick.start % 60).padStart(2, '0')}`
    : '';

  return (
    <>
      <div className="two-col">
        <Field label="Date">
          <input
            type="date"
            value={dateValue}
            onChange={(e) => onDateChange(e.target.value)}
          />
        </Field>
        <Field label="Start time">
          <input
            type="time"
            value={timeValue}
            step={1800}
            onChange={(e) => {
              const [hh, mm] = e.target.value.split(':').map(Number);
              if (!Number.isNaN(hh)) onStartChange(hh * 60 + mm);
            }}
          />
        </Field>
      </div>

      <div className="two-col">
        <Field label="Assigned to">
          <select
            value={assignedTo}
            onChange={(e) => onAssigneeChange(e.target.value)}
          >
            {ASSIGNEES.map((a) => (
              <option key={a.id} value={a.id}>
                {a.label}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Duration">
          <select
            value={durationMin}
            onChange={(e) =>
              onDurationChange(Number(e.target.value) as 30 | 60 | 90 | 120)
            }
          >
            <option value={30}>30 min</option>
            <option value={60}>1 hr</option>
            <option value={90}>1.5 hr</option>
            <option value={120}>2 hr</option>
          </select>
        </Field>
      </div>

      <Field label="Internal notes (optional)">
        <textarea
          value={internalNotes}
          placeholder="Gate code 4412. Large corner lot, sketched zones in intake call…"
          onChange={(e) => onNotesChange(e.target.value)}
        />
      </Field>
    </>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="fl">{label}</label>
      {children}
    </div>
  );
}
