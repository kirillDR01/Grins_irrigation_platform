/**
 * SchedulingChat Component
 *
 * Persistent right sidebar panel for AI scheduling assistant.
 * Supports inline criteria tag badges, clarifying questions with
 * quick-response buttons, and a "Publish Schedule" action when
 * the AI generates or modifies schedules.
 */

import { useState, useRef, useEffect, useCallback } from 'react';
import { Send, Loader2, Sparkles, CalendarCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  useSchedulingChat,
  type ScheduleChange,
} from '../hooks/useSchedulingChat';

// ── Criteria name map ──────────────────────────────────────────────────

const CRITERIA_NAMES: Record<number, string> = {
  1: 'Proximity',
  2: 'Drive Time',
  3: 'Zones',
  4: 'Traffic',
  5: 'Access',
  6: 'Skills',
  7: 'Equipment',
  8: 'Availability',
  9: 'Workload',
  10: 'Performance',
  11: 'Time Window',
  12: 'Duration',
  13: 'Priority',
  14: 'CLV',
  15: 'Relationship',
  16: 'Utilization',
  17: 'Forecast',
  18: 'Seasonal',
  19: 'Cancellation',
  20: 'Backlog',
  21: 'Compliance',
  22: 'Revenue/Hr',
  23: 'SLA',
  24: 'Overtime',
  25: 'Pricing',
  26: 'Weather',
  27: 'Complexity',
  28: 'Lead Timing',
  29: 'Start Location',
  30: 'Dependencies',
};

// ── Local message type ─────────────────────────────────────────────────

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  criteriaUsed?: number[];
  scheduleChanges?: ScheduleChange[] | null;
  clarifyingQuestions?: string[] | null;
}

// ── Props ──────────────────────────────────────────────────────────────

interface SchedulingChatProps {
  onPublishSchedule?: (changes: ScheduleChange[]) => void;
}

export function SchedulingChat({ onPublishSchedule }: SchedulingChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const chatMutation = useSchedulingChat();

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || chatMutation.isPending) return;

      setInput('');
      setMessages((prev) => [
        ...prev,
        { role: 'user', content: trimmed, timestamp: new Date() },
      ]);

      try {
        const res = await chatMutation.mutateAsync({
          message: trimmed,
          session_id: sessionId ?? undefined,
        });

        if (res.session_id) setSessionId(res.session_id);

        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: res.response,
            timestamp: new Date(),
            criteriaUsed: res.criteria_used,
            scheduleChanges: res.schedule_changes,
            clarifyingQuestions: res.clarifying_questions,
          },
        ]);
      } catch {
        // error is surfaced via chatMutation.error
      }
    },
    [chatMutation, sessionId]
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleSend(input);
  };

  return (
    <div
      className="flex flex-col h-full border-l border-slate-200 bg-white"
      data-testid="scheduling-chat"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100 bg-slate-50/60">
        <div className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-teal-500" />
          <h3 className="font-bold text-slate-800">AI Scheduling Assistant</h3>
        </div>
        <span className="rounded-full bg-teal-100 px-2 py-0.5 text-xs font-medium text-teal-700">
          GPT-4o
        </span>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {chatMutation.error && (
          <Alert variant="destructive">
            <AlertDescription>
              {chatMutation.error instanceof Error
                ? chatMutation.error.message
                : 'Failed to send message'}
            </AlertDescription>
          </Alert>
        )}

        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            data-testid={`chat-message-${msg.role}`}
          >
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-3 ${
                msg.role === 'user'
                  ? 'bg-teal-500 text-white rounded-br-md'
                  : 'bg-slate-100 text-slate-700 rounded-bl-md'
              }`}
            >
              <p className="text-sm whitespace-pre-wrap">{msg.content}</p>

              {/* Criteria tags */}
              {msg.criteriaUsed && msg.criteriaUsed.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {msg.criteriaUsed.map((num) => (
                    <span
                      key={num}
                      className="inline-flex items-center rounded-full bg-teal-50 border border-teal-200 px-2 py-0.5 text-xs font-medium text-teal-700"
                      data-testid={`criteria-tag-${num}`}
                    >
                      #{num} {CRITERIA_NAMES[num] ?? `Criterion ${num}`}
                    </span>
                  ))}
                </div>
              )}

              {/* Clarifying questions */}
              {msg.clarifyingQuestions && msg.clarifyingQuestions.length > 0 && (
                <div className="mt-3 space-y-1">
                  {msg.clarifyingQuestions.map((q, qi) => (
                    <Button
                      key={qi}
                      variant="outline"
                      size="sm"
                      className="w-full justify-start text-left text-xs"
                      onClick={() => handleSend(q)}
                    >
                      {qi + 1}. {q}
                    </Button>
                  ))}
                </div>
              )}

              {/* Publish Schedule button */}
              {msg.scheduleChanges && msg.scheduleChanges.length > 0 && (
                <Button
                  size="sm"
                  className="mt-3 bg-teal-600 hover:bg-teal-700 text-white gap-1"
                  data-testid="publish-schedule-btn"
                  onClick={() => onPublishSchedule?.(msg.scheduleChanges!)}
                >
                  <CalendarCheck className="h-3.5 w-3.5" />
                  Publish Schedule
                </Button>
              )}

              <p
                className={`text-xs mt-1 ${msg.role === 'user' ? 'text-teal-100' : 'text-slate-400'}`}
              >
                {msg.timestamp.toLocaleTimeString()}
              </p>
            </div>
          </div>
        ))}

        {chatMutation.isPending && (
          <div className="flex justify-start">
            <div className="bg-slate-100 rounded-2xl rounded-bl-md px-4 py-3">
              <Loader2 className="h-4 w-4 animate-spin text-teal-500" />
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-slate-100">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask the scheduling assistant..."
            disabled={chatMutation.isPending}
            className="flex-1 bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm text-slate-700 placeholder-slate-400 focus:ring-2 focus:ring-teal-100 focus:border-teal-500 focus:outline-none"
            data-testid="scheduling-chat-input"
          />
          <Button
            type="submit"
            disabled={!input.trim() || chatMutation.isPending}
            className="bg-teal-500 hover:bg-teal-600 text-white p-3 rounded-xl"
            data-testid="scheduling-chat-send"
          >
            {chatMutation.isPending ? (
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
