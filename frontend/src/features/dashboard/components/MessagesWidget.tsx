/**
 * MessagesWidget — displays unaddressed communication count on the dashboard.
 * Clicking navigates to /communications.
 *
 * Validates: Requirements 4.1, 4.3
 */

import { useNavigate } from 'react-router-dom';
import { MessageSquare } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { useUnaddressedCount } from '../hooks';

export function MessagesWidget() {
  const navigate = useNavigate();
  const { data, isLoading } = useUnaddressedCount();

  const count = data?.count ?? 0;

  const handleClick = () => {
    navigate('/communications');
  };

  return (
    <Card
      data-testid="messages-widget"
      className={cn(
        'relative cursor-pointer transition-all hover:shadow-md',
        count > 0 && 'border-violet-200'
      )}
      onClick={handleClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          handleClick();
        }
      }}
    >
      <CardContent className="p-6">
        <div className="absolute top-4 right-4 p-3 rounded-xl bg-violet-50">
          <MessageSquare className="h-5 w-5 text-violet-500" />
        </div>
        <div className="space-y-2">
          <p className="text-sm font-semibold uppercase tracking-wider text-slate-400">
            Messages
          </p>
          <div className="text-3xl font-bold text-slate-800">
            {isLoading ? '—' : count}
          </div>
          <p className="text-xs text-slate-400">
            {count === 0 ? 'No unaddressed messages' : `${count} unaddressed`}
          </p>
        </div>
        {count > 0 && (
          <span
            data-testid="messages-badge"
            className="absolute top-3 right-3 flex h-5 w-5 items-center justify-center rounded-full bg-violet-500 text-[10px] font-bold text-white"
          >
            {count > 99 ? '99+' : count}
          </span>
        )}
      </CardContent>
    </Card>
  );
}
