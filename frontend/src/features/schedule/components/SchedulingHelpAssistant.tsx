/**
 * SchedulingHelpAssistant Component
 * 
 * Collapsible help panel for scheduling questions
 * Uses existing AI chat infrastructure with scheduling-specific sample questions
 */

import { useState, useRef, useEffect } from 'react';
import { useAIChat } from '@/features/ai/hooks/useAIChat';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Send, Trash2, Loader2, ChevronDown, ChevronUp, Sparkles, Lightbulb } from 'lucide-react';

const SAMPLE_QUESTIONS = [
  'How should I handle jobs that need special equipment?',
  'What\'s the best way to group jobs by location?',
  'How do I schedule around staff availability constraints?',
  'What should I do if a job can\'t be assigned?',
  'How can I optimize routes for multiple staff members?',
];

export function SchedulingHelpAssistant() {
  const [input, setInput] = useState('');
  const [isExpanded, setIsExpanded] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { messages, isLoading, error, sendMessage, clearChat } = useAIChat();

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (isExpanded) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isExpanded]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    await sendMessage(input);
    setInput('');
  };

  const handleSampleClick = async (question: string) => {
    if (isLoading) return;
    await sendMessage(question);
  };

  return (
    <Card data-testid="scheduling-help-panel" className="w-full bg-white rounded-2xl shadow-sm border border-slate-100">
      <CardHeader 
        className="cursor-pointer p-4 border-b border-slate-100 bg-teal-50 hover:bg-teal-100 transition-colors" 
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-teal-600" />
            <CardTitle className="text-lg font-bold text-slate-800">Scheduling Help</CardTitle>
          </div>
          <div className="flex items-center gap-2">
            {messages.length > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  clearChat();
                }}
                disabled={messages.length === 0}
                data-testid="help-clear-btn"
                className="text-slate-400 hover:text-slate-600"
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            )}
            <Button 
              variant="ghost" 
              size="sm" 
              data-testid="help-toggle-btn"
              className="text-slate-400 hover:text-slate-600"
            >
              {isExpanded ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>
      </CardHeader>

      {isExpanded && (
        <CardContent className="space-y-4 p-4">
          {/* Error Display */}
          {error && (
            <Alert variant="destructive" data-testid="help-error" className="bg-red-50 border-red-100">
              <AlertDescription className="text-red-600">{error}</AlertDescription>
            </Alert>
          )}

          {/* Sample Questions */}
          {messages.length === 0 && (
            <div className="space-y-2" data-testid="sample-questions">
              <p className="text-sm text-slate-500">Common scheduling questions:</p>
              <div className="grid gap-2">
                {SAMPLE_QUESTIONS.map((question, index) => (
                  <button
                    key={index}
                    onClick={() => handleSampleClick(question)}
                    disabled={isLoading}
                    className="p-3 bg-slate-50 rounded-lg hover:bg-slate-100 cursor-pointer text-left text-sm text-slate-700 transition-colors flex items-start gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                    data-testid={`suggestion-item`}
                  >
                    <Lightbulb className="h-4 w-4 text-amber-500 flex-shrink-0 mt-0.5" />
                    <span>{question}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Message History */}
          {messages.length > 0 && (
            <div className="space-y-4 max-h-96 overflow-y-auto" data-testid="help-message-history">
              {messages.map((message, index) => (
                <div
                  key={index}
                  className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  data-testid={`help-message-${message.role}`}
                >
                  <div
                    className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                      message.role === 'user'
                        ? 'bg-teal-500 text-white rounded-br-md'
                        : 'bg-slate-100 text-slate-700 rounded-bl-md'
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
                <div className="flex justify-start" data-testid="help-loading">
                  <div className="bg-slate-100 rounded-2xl rounded-bl-md px-4 py-3">
                    <Loader2 className="h-4 w-4 animate-spin text-teal-500" />
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
              placeholder="Ask a scheduling question..."
              disabled={isLoading}
              data-testid="help-input"
              className="flex-1 bg-slate-50 border-slate-200 rounded-xl focus:ring-2 focus:ring-teal-100 focus:border-teal-500"
            />
            <Button
              type="submit"
              disabled={!input.trim() || isLoading}
              data-testid="help-submit-btn"
              className="bg-teal-500 hover:bg-teal-600 text-white p-3 rounded-xl"
            >
              {isLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </Button>
          </form>
        </CardContent>
      )}
    </Card>
  );
}
