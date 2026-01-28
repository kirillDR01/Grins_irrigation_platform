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
import { Send, Trash2, Loader2, ChevronDown, ChevronUp, HelpCircle } from 'lucide-react';

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
    <Card data-testid="scheduling-help-panel" className="w-full">
      <CardHeader className="cursor-pointer" onClick={() => setIsExpanded(!isExpanded)}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <HelpCircle className="h-5 w-5 text-muted-foreground" />
            <CardTitle className="text-lg">Scheduling Help</CardTitle>
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
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            )}
            <Button variant="ghost" size="sm" data-testid="help-toggle-btn">
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
        <CardContent className="space-y-4">
          {/* Error Display */}
          {error && (
            <Alert variant="destructive" data-testid="help-error">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {/* Sample Questions */}
          {messages.length === 0 && (
            <div className="space-y-2" data-testid="sample-questions">
              <p className="text-sm text-muted-foreground">Common scheduling questions:</p>
              <div className="grid gap-2">
                {SAMPLE_QUESTIONS.map((question, index) => (
                  <Button
                    key={index}
                    variant="outline"
                    size="sm"
                    onClick={() => handleSampleClick(question)}
                    disabled={isLoading}
                    className="justify-start text-left h-auto py-2"
                    data-testid={`sample-question-${index}`}
                  >
                    {question}
                  </Button>
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
                <div className="flex justify-start" data-testid="help-loading">
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
              placeholder="Ask a scheduling question..."
              disabled={isLoading}
              data-testid="help-input"
            />
            <Button
              type="submit"
              disabled={!input.trim() || isLoading}
              data-testid="help-submit-btn"
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
