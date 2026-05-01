import { Calendar } from 'lucide-react';
import { format } from 'date-fns';

interface TechHeaderProps {
  userName: string;
  jobCount: number;
  date: Date;
}

export function TechHeader({ userName, jobCount, date }: TechHeaderProps) {
  return (
    <div className="bg-slate-900 text-white px-5 pt-4 pb-4">
      <div>
        <p className="text-xs text-slate-300 font-medium">Good morning</p>
        <p className="text-xl font-bold mt-0.5">{userName}</p>
      </div>
      <div className="flex items-end justify-between mt-3">
        <div className="flex items-center gap-2 text-slate-200">
          <Calendar className="w-4 h-4" />
          <span className="text-sm font-medium">
            {format(date, 'EEE, LLL d')}
          </span>
        </div>
        <div className="text-right">
          <p className="text-lg font-bold font-mono leading-none">{jobCount}</p>
          <p className="text-[10px] tracking-wider text-slate-300 font-semibold mt-1">
            JOBS
          </p>
        </div>
      </div>
    </div>
  );
}
