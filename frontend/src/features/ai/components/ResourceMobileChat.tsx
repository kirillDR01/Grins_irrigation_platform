/**
 * ResourceMobileChat Component
 *
 * Mobile-optimized chat for the Resource (technician) role.
 * Provides quick-action buttons for common field operations,
 * displays pre-job checklists and change request status inline.
 */

import { useState, useRef, useEffect, useCallback } from 'react';
import {
  Send,
  Loader2,
  Clock,
  ClipboardList,
  Wrench,
  CalendarDays,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useSchedulingChat } from '../hooks/useSchedulingChat';
import { PreJobChecklist } from './PreJobChecklist';

// ── Quick actions ──────────────────────────────────────────────────────

const QUICK_ACTIONS = [
  { label: 'Running late', icon: Clock, message: 'I am running late' },
  {
    label: 'Pre-job info',
    icon: ClipboardList,
    message: 'Get pre-job info for my next job',
  },
  { label: 'Log parts', icon: Wrench, message: 'I need to log parts used' },
  {
    label: "Tomorrow's schedule",
    icon: CalendarDays,
    message: "Show me tomorrow's schedule",
  },
] as const;

// ── Local message type ─────────────────────────────────────────────────

interface MobileChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  changeRequestId?: string | null;
  /** If the response contains a pre-job checklist payload */
  preJobChecklist?: {
    job_type: string;
    customer_name: string;
    customer_address: string;
    required_equipment: string[];
    known_issues: string[];
    gate_code: string | null;
    special_instructions: string | null;
    estimated_duration: number;
  } | null;
}

export function ResourceMobileChat() {
  const [messages, setMessages] = useState<MobileChatMessage[]>([]);
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
            changeRequestId: res.change_request_id,
          },
        ]);
      } catch {
        // error surfaced via chatMutation.error
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
      className="flex flex-col h-full bg-white"
      data-testid="resource-mobile-chat"
    >
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-100 bg-slate-50/60">
        <h3 className="font-bold text-slate-800 text-base">Field Assistant</h3>
      </div>

      {/* Quick actions */}
      <div className="flex gap-2 px-4 py-3 overflow-x-auto border-b border-slate-100">
        {QUICK_ACTIONS.map((action) => (
          <Button
            key={action.label}
            variant="outline"
            size="sm"
            className="flex-shrink-0 gap-1 text-xs"
            onClick={() => handleSend(action.message)}
            disabled={chatMutation.isPending}
            data-testid={`quick-action-${action.label.toLowerCase().replace(/\s+/g, '-')}`}
          >
            <action.icon className="h-3.5 w-3.5" />
            {action.label}
          </Button>
        ))}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
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
          >
            <div
              className={`max-w-[90%] rounded-2xl px-3 py-2 ${
                msg.role === 'user'
                  ? 'bg-teal-500 text-white rounded-br-md'
                  : 'bg-slate-100 text-slate-700 rounded-bl-md'
              }`}
            >
              <p className="text-sm whitespace-pre-wrap">{msg.content}</p>

              {/* Inline pre-job checklist */}
              {msg.preJobChecklist && (
                <div className="mt-2">
                  <PreJobChecklist checklist={msg.preJobChecklist} />
                </div>
              )}

              {/* Change request status */}
              {msg.changeRequestId && (
                <div className="mt-2 rounded-lg bg-amber-50 border border-amber-200 px-2 py-1 text-xs text-amber-700">
                  Change request submitted — pending admin approval
                </div>
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
            <div className="bg-slate-100 rounded-2xl rounded-bl-md px-3 py-2">
              <Loader2 className="h-4 w-4 animate-spin text-teal-500" />
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-3 border-t border-slate-100">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about your schedule..."
            disabled={chatMutation.isPending}
            className="flex-1 bg-slate-50 border border-slate-200 rounded-xl px-3 py-2.5 text-sm text-slate-700 placeholder-slate-400 focus:ring-2 focus:ring-teal-100 focus:border-teal-500 focus:outline-none"
            data-testid="resource-chat-input"
          />
          <Button
            type="submit"
            disabled={!input.trim() || chatMutation.isPending}
            className="bg-teal-500 hover:bg-teal-600 text-white p-2.5 rounded-xl"
            data-testid="resource-chat-send"
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
