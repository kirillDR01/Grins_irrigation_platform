import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bell, CheckCircle2, XCircle, CalendarX, Clock } from 'lucide-react';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { useAuth } from '@/features/auth';
import {
  useUnreadCount,
  useRecentAdminNotifications,
  useMarkNotificationRead,
} from '../hooks/useAdminNotifications';
import { subjectRouteFor } from '../utils/subjectRoute';
import type { AdminNotification, AdminNotificationEventType } from '../types';

function eventIcon(eventType: string) {
  switch (eventType as AdminNotificationEventType) {
    case 'estimate_approved':
      return <CheckCircle2 className="h-4 w-4 text-emerald-600" />;
    case 'estimate_rejected':
      return <XCircle className="h-4 w-4 text-rose-600" />;
    case 'appointment_cancelled':
      return <CalendarX className="h-4 w-4 text-amber-600" />;
    case 'late_reschedule':
      return <Clock className="h-4 w-4 text-amber-600" />;
    default:
      return <Bell className="h-4 w-4 text-slate-500" />;
  }
}

function timeAgo(iso: string): string {
  const now = Date.now();
  const then = new Date(iso).getTime();
  const seconds = Math.max(0, Math.floor((now - then) / 1000));
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export function NotificationBell() {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();

  // Only admins see the bell. Hooks always run (rules-of-hooks);
  // we gate render below.
  const isAdmin = user?.role === 'admin';
  const { data: unreadData } = useUnreadCount({ enabled: isAdmin });
  const { data: listData } = useRecentAdminNotifications({
    enabled: isAdmin && open,
  });
  const markRead = useMarkNotificationRead();

  if (!isAdmin) {
    return null;
  }

  const unread = unreadData?.unread ?? 0;
  const showBadge = unread > 0;
  const items: AdminNotification[] = listData?.items ?? [];

  const handleItemClick = async (item: AdminNotification) => {
    setOpen(false);
    try {
      if (!item.read_at) {
        await markRead.mutateAsync(item.id);
      }
    } catch {
      // Non-blocking — still navigate.
    }
    navigate(subjectRouteFor(item.subject_resource_type, item.subject_resource_id));
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          type="button"
          className="relative p-2 rounded-lg hover:bg-slate-100 transition-colors"
          data-testid="notification-bell"
          aria-label="Notifications"
        >
          <Bell className="h-5 w-5 text-slate-600" />
          {showBadge && (
            <span
              className="absolute -top-1 -right-1 h-4 w-4 rounded-full bg-rose-500 border-2 border-white flex items-center justify-center"
              data-testid="notification-badge"
            >
              <span
                className="text-[10px] font-medium text-white"
                data-testid="notification-count"
              >
                {unread > 9 ? '9+' : unread}
              </span>
            </span>
          )}
        </button>
      </PopoverTrigger>
      <PopoverContent className="w-80 p-0" align="end">
        <div className="p-3 border-b border-slate-100">
          <h4 className="font-semibold text-slate-800">Notifications</h4>
        </div>
        <div className="max-h-80 overflow-y-auto" data-testid="notification-list">
          {items.length > 0 ? (
            items.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => void handleItemClick(item)}
                className={
                  'w-full text-left flex items-start gap-3 p-3 hover:bg-slate-50 transition-colors border-b border-slate-50 last:border-b-0 ' +
                  (item.read_at ? 'opacity-60' : '')
                }
                data-testid="notification-item"
              >
                <div className="p-2 rounded-full bg-slate-100 shrink-0">
                  {eventIcon(item.event_type)}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-slate-800 truncate">
                    {item.summary}
                  </p>
                  <p className="text-xs text-slate-500 mt-0.5">
                    {timeAgo(item.created_at)}
                  </p>
                </div>
              </button>
            ))
          ) : (
            <div className="p-4 text-center text-sm text-slate-500">
              No new notifications
            </div>
          )}
        </div>
      </PopoverContent>
    </Popover>
  );
}
