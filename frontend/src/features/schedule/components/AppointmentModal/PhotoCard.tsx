/**
 * PhotoCard — 180px-wide card for the horizontal photo strip.
 * Displays a 134px image area with caption + date below.
 * Requirements: 4.7, 12.4
 */

import { format } from 'date-fns';

const MONO_FONT =
  "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace";

interface PhotoCardProps {
  src: string;
  alt: string;
  caption?: string | null;
  date?: string | null;
  onClick?: () => void;
}

export function PhotoCard({ src, alt, caption, date, onClick }: PhotoCardProps) {
  const formattedDate = date
    ? format(new Date(date), 'MMM d, yyyy')
    : null;

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick?.();
        }
      }}
      aria-label={caption || alt}
      style={{
        width: 180,
        flexShrink: 0,
        borderRadius: 12,
        border: '1.5px solid #E5E7EB',
        overflow: 'hidden',
        backgroundColor: '#FFFFFF',
        cursor: 'pointer',
        outline: 'none',
      }}
    >
      {/* Image area — 134px tall */}
      <img
        src={src}
        alt={alt}
        loading="lazy"
        style={{
          width: '100%',
          height: 134,
          objectFit: 'cover',
          display: 'block',
        }}
      />

      {/* Caption row */}
      <div
        style={{
          padding: '8px 10px',
          display: 'flex',
          flexDirection: 'column',
          gap: 2,
        }}
      >
        {caption && (
          <span
            style={{
              fontSize: 12,
              fontWeight: 700,
              color: '#1F2937',
              lineHeight: 1.3,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {caption}
          </span>
        )}
        {formattedDate && (
          <span
            style={{
              fontSize: 10.5,
              fontWeight: 600,
              fontFamily: MONO_FONT,
              color: '#6B7280',
              lineHeight: 1.3,
            }}
          >
            {formattedDate}
          </span>
        )}
      </div>
    </div>
  );
}
