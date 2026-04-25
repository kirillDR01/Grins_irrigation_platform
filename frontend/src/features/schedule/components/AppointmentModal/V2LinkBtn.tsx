/**
 * V2LinkBtn — Accent-tinted toggle button with count badge and chevron.
 * Used for "See attached photos" (blue) and "See attached notes" (amber).
 * Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 12.1, 12.6
 */

import { type ReactNode } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';

type Accent = 'blue' | 'amber';

interface V2LinkBtnProps {
  children: ReactNode;
  icon: ReactNode;
  accent: Accent;
  open: boolean;
  count?: number;
  onClick: () => void;
  'aria-label'?: string;
}

const ACCENT_MAP = {
  blue: { bg: '#DBEAFE', color: '#1D4ED8', border: '#1D4ED8' },
  amber: { bg: '#FEF3C7', color: '#B45309', border: '#B45309' },
} as const;

const CLOSED = { bg: '#FFFFFF', color: '#374151', border: '#E5E7EB' } as const;

const MONO_FONT =
  "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace";

export function V2LinkBtn({
  children,
  icon,
  accent,
  open,
  count,
  onClick,
  'aria-label': ariaLabel,
}: V2LinkBtnProps) {
  const palette = open ? ACCENT_MAP[accent] : CLOSED;
  const chevronColor = open ? ACCENT_MAP[accent].color : '#6B7280';

  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={ariaLabel}
      aria-expanded={open}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 6,
        minHeight: 44,
        padding: '0 12px',
        borderRadius: 12,
        border: `1.5px solid ${palette.border}`,
        backgroundColor: palette.bg,
        color: palette.color,
        fontSize: 14,
        fontWeight: 700,
        cursor: 'pointer',
        transition: 'background-color 150ms, color 150ms, border-color 150ms',
        lineHeight: 1,
      }}
    >
      {/* Leading icon */}
      <span
        style={{
          width: 16,
          height: 16,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
        }}
      >
        <span
          style={{
            display: 'contents',
          }}
          /* Apply size + stroke-width to child SVG via CSS */
          className="[&>svg]:w-4 [&>svg]:h-4 [&>svg]:stroke-[2.2]"
        >
          {icon}
        </span>
      </span>

      {/* Label text */}
      <span>{children}</span>

      {/* Count badge pill */}
      {count !== undefined && (
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            borderRadius: 999,
            fontSize: 11.5,
            fontWeight: 800,
            fontFamily: MONO_FONT,
            minWidth: 20,
            height: 20,
            padding: '0 6px',
            backgroundColor: open ? ACCENT_MAP[accent].color : '#F3F4F6',
            color: open ? '#FFFFFF' : '#4B5563',
            lineHeight: 1,
          }}
        >
          {count}
        </span>
      )}

      {/* Trailing chevron */}
      <span
        style={{
          width: 14,
          height: 14,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
          color: chevronColor,
        }}
      >
        {open ? (
          <ChevronUp size={14} strokeWidth={2.4} />
        ) : (
          <ChevronDown size={14} strokeWidth={2.4} />
        )}
      </span>
    </button>
  );
}
