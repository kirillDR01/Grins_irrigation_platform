import { cn } from '@/shared/utils/cn';

export type TagTone = 'neutral' | 'blue' | 'green' | 'amber' | 'violet';

const toneStyles: Record<TagTone, string> = {
  neutral: 'bg-gray-100 text-gray-700 border-gray-300',
  blue: 'bg-blue-50 text-blue-700 border-blue-300',
  green: 'bg-green-50 text-green-700 border-green-300',
  amber: 'bg-amber-50 text-amber-700 border-amber-300',
  violet: 'bg-violet-50 text-violet-700 border-violet-300',
};

interface TagChipProps {
  label: string;
  tone: TagTone;
  onRemove?: () => void;
  removeDisabled?: boolean;
  removeDisabledTooltip?: string;
  className?: string;
}

export function TagChip({
  label,
  tone,
  onRemove,
  removeDisabled,
  removeDisabledTooltip,
  className,
}: TagChipProps) {
  const isRemovable = onRemove !== undefined;

  return (
    <span
      className={cn(
        'inline-flex items-center border rounded-full whitespace-nowrap',
        'text-[12.5px] font-extrabold tracking-[-0.1px]',
        isRemovable ? 'pl-[10px] pr-[6px] py-[5px]' : 'px-[10px] py-[5px]',
        toneStyles[tone],
        className,
      )}
    >
      {label}
      {isRemovable && (
        <button
          type="button"
          onClick={removeDisabled ? undefined : onRemove}
          disabled={removeDisabled}
          aria-label={`Remove tag: ${label}`}
          title={removeDisabled ? removeDisabledTooltip : undefined}
          className={cn(
            'ml-[6px] w-[18px] h-[18px] rounded-full flex items-center justify-center',
            'bg-black/[0.08] flex-shrink-0',
            removeDisabled
              ? 'cursor-not-allowed opacity-50'
              : 'hover:bg-black/[0.15] cursor-pointer',
          )}
        >
          <svg
            width="11"
            height="11"
            viewBox="0 0 11 11"
            fill="none"
            stroke="currentColor"
            strokeWidth="3"
            strokeLinecap="round"
          >
            <line x1="2" y1="2" x2="9" y2="9" />
            <line x1="9" y1="2" x2="2" y2="9" />
          </svg>
        </button>
      )}
    </span>
  );
}
