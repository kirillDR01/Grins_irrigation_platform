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
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Send, Trash2, Loader2, Sparkles } from 'lucide-react';

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
    <div 
      className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden flex flex-col h-[600px]"
      data-testid="ai-chat"
    >
      {/* Chat Header */}
      <div className="p-4 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-teal-500" />
          <h3 className="font-bold text-slate-800 text-lg">AI Assistant</h3>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-slate-500" data-testid="message-count">
            {messageCount} / 50 messages
          </span>
          <Button
            variant="ghost"
            size="sm"
            onClick={clearChat}
            disabled={messages.length === 0}
            className="text-slate-400 hover:text-slate-600"
            data-testid="ai-chat-clear"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4" data-testid="message-history">
        {/* Error Display */}
        {error && (
          <Alert variant="destructive" data-testid="ai-chat-error">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Example Queries */}
        {messages.length === 0 && (
          <div className="space-y-3" data-testid="example-queries">
            <p className="text-sm text-slate-500">Try asking:</p>
            <div className="grid gap-2">
              {EXAMPLE_QUERIES.map((query, index) => (
                <Button
                  key={index}
                  variant="outline"
                  size="sm"
                  onClick={() => handleExampleClick(query)}
                  className="justify-start text-left h-auto py-2 text-slate-600 hover:bg-slate-50 hover:text-slate-800"
                  data-testid={`example-query-${index}`}
                >
                  {query}
                </Button>
              ))}
            </div>
          </div>
        )}

        {/* Message History */}
        {messages.map((message, index) => (
          <div
            key={index}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            data-testid={message.role === 'user' ? 'user-message' : 'ai-message'}
          >
            {message.role === 'assistant' && (
              <div className="w-8 h-8 rounded-full bg-teal-100 text-teal-600 flex items-center justify-center mr-2 flex-shrink-0">
                <Sparkles className="h-4 w-4" />
              </div>
            )}
            <div
              className={`max-w-[80%] px-4 py-3 ${
                message.role === 'user'
                  ? 'bg-teal-500 text-white rounded-2xl rounded-br-md ml-auto'
                  : 'bg-slate-100 text-slate-700 rounded-2xl rounded-bl-md'
              }`}
            >
              <p className="text-sm whitespace-pre-wrap">{message.content}</p>
              <p className={`text-xs mt-1 ${message.role === 'user' ? 'text-teal-100' : 'text-slate-400'}`}>
                {message.timestamp.toLocaleTimeString()}
              </p>
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start" data-testid="ai-chat-loading">
            <div className="w-8 h-8 rounded-full bg-teal-100 text-teal-600 flex items-center justify-center mr-2 flex-shrink-0">
              <Sparkles className="h-4 w-4" />
            </div>
            <div className="bg-slate-100 rounded-2xl rounded-bl-md px-4 py-3">
              <Loader2 className="h-4 w-4 animate-spin text-teal-500" />
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Container */}
      <div className="p-4 border-t border-slate-100 bg-white">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask me anything about your business..."
            disabled={isLoading}
            className="flex-1 bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-slate-700 placeholder-slate-400 focus:ring-2 focus:ring-teal-100 focus:border-teal-500 focus:outline-none"
            data-testid="ai-chat-input"
          />
          <Button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="bg-teal-500 hover:bg-teal-600 text-white p-3 rounded-xl"
            data-testid="ai-send-btn"
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </form>
      </div>
    </div>
  );
}
