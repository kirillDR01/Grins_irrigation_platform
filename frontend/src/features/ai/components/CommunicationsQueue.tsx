/**
 * Communications Queue component.
 * Displays messages grouped by status with bulk actions.
 */

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Send, Pause, RefreshCw, Search, Clock, CheckCircle, XCircle, AlertCircle, MessageSquare } from 'lucide-react';
import { useCommunications } from '../hooks/useCommunications';
import { AILoadingState } from './AILoadingState';
import { AIErrorState } from './AIErrorState';

export function CommunicationsQueue() {
  const [searchQuery, setSearchQuery] = useState('');
  const [messageTypeFilter, setMessageTypeFilter] = useState<string>('all');
  
  const { 
    queue, 
    isLoading, 
    error, 
    sendAll, 
    pauseAll, 
    retry,
    isSending 
  } = useCommunications({ search: searchQuery, messageType: messageTypeFilter });

  if (isLoading) return <AILoadingState />;
  if (error) return <AIErrorState error={error} onRetry={() => window.location.reload()} />;

  const pending = queue?.filter(m => m.delivery_status === 'pending') ?? [];
  const scheduled = queue?.filter(m => m.delivery_status === 'scheduled') ?? [];
  const sent = queue?.filter(m => m.delivery_status === 'sent') ?? [];
  const failed = queue?.filter(m => m.delivery_status === 'failed') ?? [];

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'pending': return <Clock className="h-4 w-4 text-yellow-600" />;
      case 'scheduled': return <Clock className="h-4 w-4 text-blue-600" />;
      case 'sent': return <CheckCircle className="h-4 w-4 text-green-600" />;
      case 'failed': return <XCircle className="h-4 w-4 text-red-600" />;
      default: return <AlertCircle className="h-4 w-4 text-gray-600" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending': return 'bg-yellow-100 text-yellow-800';
      case 'scheduled': return 'bg-blue-100 text-blue-800';
      case 'sent': return 'bg-green-100 text-green-800';
      case 'failed': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <Card data-testid="communications-queue">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Communications Queue</CardTitle>
          <div className="flex gap-2">
            {pending.length > 0 && (
              <Button
                data-testid="send-all-btn"
                onClick={sendAll}
                disabled={isSending}
                size="sm"
              >
                <Send className="h-4 w-4 mr-2" />
                Send All ({pending.length})
              </Button>
            )}
            {scheduled.length > 0 && (
              <Button
                data-testid="pause-all-btn"
                onClick={pauseAll}
                variant="outline"
                size="sm"
              >
                <Pause className="h-4 w-4 mr-2" />
                Pause All
              </Button>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Filters */}
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              data-testid="message-search"
              placeholder="Search by customer name or phone..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>
          <Select value={messageTypeFilter} onValueChange={setMessageTypeFilter}>
            <SelectTrigger data-testid="message-filter" className="w-[200px]">
              <SelectValue placeholder="Filter by type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Types</SelectItem>
              <SelectItem value="confirmation">Confirmation</SelectItem>
              <SelectItem value="reminder">Reminder</SelectItem>
              <SelectItem value="on_the_way">On The Way</SelectItem>
              <SelectItem value="arrival">Arrival</SelectItem>
              <SelectItem value="completion">Completion</SelectItem>
              <SelectItem value="invoice">Invoice</SelectItem>
              <SelectItem value="payment_reminder">Payment Reminder</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Pending Messages */}
        {pending.length > 0 && (
          <div data-testid="pending-messages" className="space-y-2">
            <h3 className="font-semibold text-sm flex items-center gap-2">
              <Clock className="h-4 w-4 text-yellow-600" />
              Pending ({pending.length})
            </h3>
            <div className="space-y-2">
              {pending.map((message) => (
                <div
                  key={message.id}
                  data-testid={`message-${message.id}`}
                  className="p-3 border rounded-lg space-y-2"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <Badge className={getStatusColor(message.delivery_status)}>
                          {message.message_type}
                        </Badge>
                        <span className="text-sm font-medium">{message.recipient_phone}</span>
                      </div>
                      <p className="text-sm text-muted-foreground mt-1">{message.message_content}</p>
                    </div>
                    <Button
                      data-testid={`send-${message.id}`}
                      size="sm"
                      variant="outline"
                      onClick={() => {/* TODO: Send individual message */}}
                    >
                      <Send className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Scheduled Messages */}
        {scheduled.length > 0 && (
          <div data-testid="scheduled-messages" className="space-y-2">
            <h3 className="font-semibold text-sm flex items-center gap-2">
              <Clock className="h-4 w-4 text-blue-600" />
              Scheduled ({scheduled.length})
            </h3>
            <div className="space-y-2">
              {scheduled.map((message) => (
                <div
                  key={message.id}
                  data-testid={`message-${message.id}`}
                  className="p-3 border rounded-lg space-y-2"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <Badge className={getStatusColor(message.delivery_status)}>
                          {message.message_type}
                        </Badge>
                        <span className="text-sm font-medium">{message.recipient_phone}</span>
                        {message.scheduled_for && (
                          <span className="text-xs text-muted-foreground">
                            Scheduled: {new Date(message.scheduled_for).toLocaleString()}
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground mt-1">{message.message_content}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Sent Messages */}
        {sent.length > 0 && (
          <div data-testid="sent-messages" className="space-y-2">
            <h3 className="font-semibold text-sm flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-green-600" />
              Sent Today ({sent.length})
            </h3>
            <div className="space-y-2">
              {sent.slice(0, 5).map((message) => (
                <div
                  key={message.id}
                  data-testid={`message-${message.id}`}
                  className="p-3 border rounded-lg space-y-2 bg-muted/30"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <Badge className={getStatusColor(message.delivery_status)}>
                          {message.message_type}
                        </Badge>
                        <span className="text-sm font-medium">{message.recipient_phone}</span>
                        <span className="text-xs text-muted-foreground">
                          {new Date(message.created_at).toLocaleTimeString()}
                        </span>
                      </div>
                      <p className="text-sm text-muted-foreground mt-1">{message.message_content}</p>
                    </div>
                    {getStatusIcon(message.delivery_status)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Failed Messages */}
        {failed.length > 0 && (
          <div data-testid="failed-messages" className="space-y-2">
            <h3 className="font-semibold text-sm flex items-center gap-2">
              <XCircle className="h-4 w-4 text-red-600" />
              Failed ({failed.length})
            </h3>
            <div className="space-y-2">
              {failed.map((message) => (
                <div
                  key={message.id}
                  data-testid={`message-${message.id}`}
                  className="p-3 border border-red-200 rounded-lg space-y-2 bg-red-50"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <Badge className={getStatusColor(message.delivery_status)}>
                          {message.message_type}
                        </Badge>
                        <span className="text-sm font-medium">{message.recipient_phone}</span>
                      </div>
                      <p className="text-sm text-muted-foreground mt-1">{message.message_content}</p>
                    </div>
                    <Button
                      data-testid={`retry-${message.id}`}
                      size="sm"
                      variant="outline"
                      onClick={() => retry(message.id)}
                    >
                      <RefreshCw className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Empty State */}
        {queue?.length === 0 && (
          <div className="text-center py-8 text-muted-foreground">
            <MessageSquare className="h-12 w-12 mx-auto mb-2 opacity-50" />
            <p>No messages in queue</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
