import { Mail, MessageSquare, Phone } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { OptOutBadge } from '@/shared/components';
import { useCustomerSentMessages } from '../hooks';

const channelIcons: Record<string, React.ReactNode> = {
  sms: <MessageSquare className="h-4 w-4 text-teal-500" />,
  email: <Mail className="h-4 w-4 text-blue-500" />,
  phone: <Phone className="h-4 w-4 text-violet-500" />,
};

const statusColors: Record<string, string> = {
  sent: 'bg-emerald-100 text-emerald-700',
  delivered: 'bg-emerald-100 text-emerald-700',
  failed: 'bg-red-100 text-red-700',
  pending: 'bg-amber-100 text-amber-700',
  queued: 'bg-blue-100 text-blue-700',
};

interface CustomerMessagesProps {
  customerId: string;
}

export function CustomerMessages({ customerId }: CustomerMessagesProps) {
  const { data: rawMessages, isLoading, error } = useCustomerSentMessages(customerId);
  // API may return paginated {items: [...]} or plain array
  const messages = Array.isArray(rawMessages) ? rawMessages : (rawMessages as any)?.items ?? [];

  const header = (
    <div className="mb-3">
      <OptOutBadge customerId={customerId} />
    </div>
  );

  if (isLoading) {
    return (
      <div className="space-y-3" data-testid="messages-loading">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-16 w-full rounded-lg" />
        ))}
      </div>
    );
  }

  if (error) {
    return <p className="text-red-600 text-sm" data-testid="messages-error">Failed to load messages.</p>;
  }

  if (!messages || messages.length === 0) {
    return (
      <div className="text-center py-8" data-testid="messages-empty">
        <MessageSquare className="h-10 w-10 text-slate-300 mx-auto mb-2" />
        <p className="text-sm text-slate-500">No messages sent to this customer</p>
      </div>
    );
  }

  // Sort by date descending
  const sorted = [...messages].sort(
    (a, b) => new Date(b.sent_at || b.created_at).getTime() - new Date(a.sent_at || a.created_at).getTime()
  );

  return (
    <div data-testid="customer-messages" className="space-y-3">
      {header}
      {sorted.map((msg) => {
        const channel = msg.message_type?.includes('sms') || msg.recipient_phone ? 'sms' : 'email';
        return (
          <div
            key={msg.id}
            className="p-4 rounded-lg border border-slate-100 bg-white space-y-2"
            data-testid={`message-${msg.id}`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {channelIcons[channel] || channelIcons.email}
                <span className="text-xs font-medium text-slate-500 uppercase">
                  {msg.message_type?.replace(/_/g, ' ') || channel}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <Badge
                  className={`text-xs capitalize ${statusColors[msg.status] || 'bg-slate-100 text-slate-600'}`}
                  data-testid={`message-status-${msg.status}`}
                >
                  {msg.status}
                </Badge>
                <span className="text-xs text-slate-400">
                  {new Date(msg.sent_at || msg.created_at).toLocaleString()}
                </span>
              </div>
            </div>
            <p className="text-sm text-slate-700 whitespace-pre-wrap">{msg.content}</p>
            {msg.recipient_phone && (
              <p className="text-xs text-slate-400">To: {msg.recipient_phone}</p>
            )}
            {msg.recipient_email && (
              <p className="text-xs text-slate-400">To: {msg.recipient_email}</p>
            )}
          </div>
        );
      })}
    </div>
  );
}
