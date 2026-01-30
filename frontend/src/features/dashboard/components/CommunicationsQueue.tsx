import { Send } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card';
import { Button } from '@/shared/components/ui/button';
import { Badge } from '@/shared/components/ui/badge';

interface QueueItem {
  id: string;
  customerId: string;
  customerName: string;
  customerInitials: string;
  messagePreview: string;
  type: 'SMS' | 'Email';
  time: string;
}

interface CommunicationsQueueProps {
  items?: QueueItem[];
  onSendAll?: () => void;
  onSendItem?: (id: string) => void;
}

export function CommunicationsQueue({
  items = [],
  onSendAll,
  onSendItem,
}: CommunicationsQueueProps) {
  return (
    <Card data-testid="communications-queue">
      <CardHeader className="flex flex-row items-center justify-between">
        <div className="flex items-center gap-2">
          <Send className="w-5 h-5 text-slate-600" />
          <CardTitle>Communications Queue</CardTitle>
          {items.length > 0 && (
            <Badge className="bg-teal-100 text-teal-700" data-testid="queue-count">
              {items.length}
            </Badge>
          )}
        </div>
        {items.length > 0 && (
          <Button
            onClick={onSendAll}
            data-testid="send-all-btn"
            className="bg-teal-500 hover:bg-teal-600 text-white"
          >
            Send All
          </Button>
        )}
      </CardHeader>
      <CardContent>
        {items.length === 0 ? (
          <div className="text-center py-8 text-slate-400">
            <Send className="w-12 h-12 mx-auto mb-2 text-slate-300" />
            <p className="text-sm">No messages in queue</p>
          </div>
        ) : (
          <div className="space-y-3">
            {items.map((item) => (
              <div
                key={item.id}
                data-testid="queue-item"
                className="flex items-center gap-4 p-3 bg-slate-50 rounded-lg hover:bg-slate-100 transition-colors"
              >
                <div className="w-10 h-10 rounded-full bg-teal-100 text-teal-700 flex items-center justify-center font-semibold text-sm">
                  {item.customerInitials}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-slate-700">{item.customerName}</div>
                  <div className="text-sm text-slate-500 truncate">{item.messagePreview}</div>
                </div>
                <Badge
                  variant={item.type === 'SMS' ? 'default' : 'secondary'}
                  className="shrink-0"
                >
                  {item.type}
                </Badge>
                <div className="text-xs text-slate-400 shrink-0">{item.time}</div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onSendItem?.(item.id)}
                  data-testid="send-item-btn"
                  className="shrink-0"
                >
                  <Send className="w-4 h-4" />
                </Button>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
