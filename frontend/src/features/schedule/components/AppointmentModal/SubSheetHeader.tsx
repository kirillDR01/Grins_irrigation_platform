import type { ReactNode } from 'react';
import { ChevronLeft } from 'lucide-react';

interface SubSheetHeaderProps {
  title: string;
  onBack: () => void;
  rightAction?: ReactNode;
}

export function SubSheetHeader({ title, onBack, rightAction }: SubSheetHeaderProps) {
  return (
    <div
      data-testid="subsheet-header"
      className="sticky top-0 z-10 bg-white border-b border-slate-100 px-4 py-3 flex items-center gap-2 flex-shrink-0"
    >
      <button
        type="button"
        onClick={onBack}
        aria-label="Back"
        data-testid="subsheet-back-btn"
        className="h-11 w-11 -ml-2 flex items-center justify-center rounded-full hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-teal-500"
      >
        <ChevronLeft className="h-5 w-5 text-slate-700" strokeWidth={2.2} />
      </button>
      <h2 className="text-base font-semibold text-slate-800 flex-1 truncate">{title}</h2>
      {rightAction && <div className="flex-shrink-0">{rightAction}</div>}
    </div>
  );
}
