/**
 * AIQueryChat Component
 * 
 * Interactive chat interface for AI business queries
 * Displays message history, handles streaming responses,
 * and provides example query suggestions
 */

import { useState, useRef, useEffect } from 'react';
import { useAIChat } from '../hooks/useAIChat';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Send, Trash2, Loader2 } from 'lucide-react';

const EXAMPLE_QUERIES = [
  'How many jobs do we have scheduled today?',
  'What is our revenue this month?',
  'Show me customers with overdue invoices',
  'Which staff member has the most jobs this week?',
];

export function AIQueryChat() {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { messages, isLoading, error, messageCount, sendMessage, clearChat } = useAIChat();

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    await sendMessage(input);
    setInput('');
  };

  const handleExampleClick = (query: string) => {
    setInput(query);
  };

  return (
    <Card data-testid="ai-query-chat">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>AI Assistant</CardTitle>
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground" data-testid="message-count">
              {messageCount} / 50 messages
            </span>
            <Button
              variant="ghost"
              size="sm"
              onClick={clearChat}
              disabled={messages.length === 0}
              data-testid="ai-chat-clear"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Error Display */}
        {error && (
          <Alert variant="destructive" data-testid="ai-chat-error">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Example Queries */}
        {messages.length === 0 && (
          <div className="space-y-2" data-testid="example-queries">
            <p className="text-sm text-muted-foreground">Try asking:</p>
            <div className="grid gap-2">
              {EXAMPLE_QUERIES.map((query, index) => (
                <Button
                  key={index}
                  variant="outline"
                  size="sm"
                  onClick={() => handleExampleClick(query)}
                  className="justify-start text-left h-auto py-2"
                  data-testid={`example-query-${index}`}
                >
                  {query}
                </Button>
              ))}
            </div>
          </div>
        )}

        {/* Message History */}
        {messages.length > 0 && (
          <div className="space-y-4 max-h-96 overflow-y-auto" data-testid="message-history">
            {messages.map((message, index) => (
              <div
                key={index}
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                data-testid={`message-${message.role}`}
              >
                <div
                  className={`max-w-[80%] rounded-lg px-4 py-2 ${
                    message.role === 'user'
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-muted'
                  }`}
                >
                  <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                  <p className="text-xs opacity-70 mt-1">
                    {message.timestamp.toLocaleTimeString()}
                  </p>
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="flex justify-start" data-testid="ai-chat-loading">
                <div className="bg-muted rounded-lg px-4 py-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}

        {/* Chat Input */}
        <form onSubmit={handleSubmit} className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask me anything about your business..."
            disabled={isLoading}
            data-testid="ai-chat-input"
          />
          <Button
            type="submit"
            disabled={!input.trim() || isLoading}
            data-testid="ai-chat-submit"
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
