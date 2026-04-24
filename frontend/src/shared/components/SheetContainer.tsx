import type { ReactNode } from 'react';
import { cn } from '@/shared/utils/cn';

interface SheetContainerProps {
  title: string;
  subtitle?: string;
  onClose: () => void;
  onBack?: () => void;
  footer?: ReactNode;
  children: ReactNode;
  className?: string;
}

export function SheetContainer({
  title,
  subtitle,
  onClose,
  onBack,
  footer,
  children,
  className,
}: SheetContainerProps) {
  return (
    <div
      className={cn(
        'flex flex-col w-[560px] bg-white rounded-t-[20px] border border-[#E5E7EB]',
        'shadow-[0_-4px_24px_rgba(0,0,0,0.12)]',
        className,
      )}
    >
      {/* Grab handle */}
      <div className="flex justify-center pt-3 pb-1 flex-shrink-0">
        <div className="w-11 h-[5px] rounded-[3px] bg-[#E5E7EB]" />
      </div>

      {/* Header */}
      <div className="flex items-center gap-2 px-5 py-3 flex-shrink-0">
        {onBack && (
          <button
            type="button"
            onClick={onBack}
            aria-label="Go back"
            className="w-11 h-11 flex items-center justify-center rounded-[12px] border-[1.5px] border-[#E5E7EB] bg-white flex-shrink-0"
          >
            <svg
              width="18"
              height="18"
              viewBox="0 0 18 18"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polyline points="11 4 6 9 11 14" />
            </svg>
          </button>
        )}
        <div className="flex-1 min-w-0">
          <h2 className="text-[22px] font-extrabold tracking-[-0.5px] text-[#0B1220] leading-tight">
            {title}
          </h2>
          {subtitle && (
            <p className="text-[13.5px] font-semibold text-[#4B5563] mt-0.5">{subtitle}</p>
          )}
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close"
          className="w-11 h-11 flex items-center justify-center rounded-[12px] border-[1.5px] border-[#E5E7EB] bg-white flex-shrink-0"
        >
          <svg
            width="18"
            height="18"
            viewBox="0 0 18 18"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
          >
            <line x1="4" y1="4" x2="14" y2="14" />
            <line x1="14" y1="4" x2="4" y2="14" />
          </svg>
        </button>
      </div>

      {/* Scrollable body */}
      <div className="flex-1 overflow-auto px-5 py-2">{children}</div>

      {/* Sticky footer */}
      {footer && (
        <div className="flex-shrink-0 bg-[#F9FAFB] border-t border-[#E5E7EB] px-5 py-4">
          {footer}
        </div>
      )}
    </div>
  );
}
