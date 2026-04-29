/**
 * SchedulingChat — Persistent AI scheduling assistant sidebar for Admin role.
 * Renders alongside ScheduleOverviewEnhanced in a two-column layout.
 */

import { useState, useRef, useEffect } from 'react';
import { useSchedulingChat } from '../hooks/useSchedulingChat';
import type { ChatMessage } from '../hooks/useSchedulingChat';
import type { ScheduleChange } from '../types/aiScheduling';

interface SchedulingChatProps {
  /** Called when AI publishes schedule changes */
  onPublishSchedule?: (changes: ScheduleChange[]) => void;
}

function CriteriaTag({ number, name }: { number: number; name: string }) {
  return (
    <span
      className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 mr-1 mb-1 cursor-pointer hover:bg-blue-200"
      data-testid={`criteria-tag-${number}`}
      title={name}
    >
      Criteria #{number}
    </span>
  );
}

function MessageBubble({
  message,
  onPublish,
}: {
  message: ChatMessage;
  onPublish?: (changes: ScheduleChange[]) => void;
}) {
  const isUser = message.role === 'user';

  return (
    <div
      className={`flex flex-col mb-4 ${isUser ? 'items-end' : 'items-start'}`}
      data-testid={`chat-message-${message.role}`}
    >
      <span className="text-xs text-gray-500 mb-1 px-1">
        {isUser ? message.userName ?? 'You' : 'AI ASSISTANT'}
      </span>
      <div
        className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
          isUser
            ? 'bg-blue-600 text-white'
            : 'bg-gray-100 text-gray-900'
        }`}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>

        {/* Criteria tags */}
        {message.criteriaUsed && message.criteriaUsed.length > 0 && (
          <div className="mt-2 flex flex-wrap">
            {message.criteriaUsed.map((c) => (
              <CriteriaTag key={c.number} number={c.number} name={c.name} />
            ))}
          </div>
        )}

        {/* Clarifying questions */}
        {message.clarifyingQuestions && message.clarifyingQuestions.length > 0 && (
          <ol className="mt-2 list-decimal list-inside space-y-1 text-sm">
            {message.clarifyingQuestions.map((q, i) => (
              <li key={i}>{q}</li>
            ))}
          </ol>
        )}

        {/* Schedule summary */}
        {message.scheduleSummary && (
          <div className="mt-2 p-2 bg-white rounded border border-gray-200 text-xs text-gray-700">
            <p className="font-medium mb-1">Schedule Summary</p>
            <p>{message.scheduleSummary}</p>
          </div>
        )}

        {/* Schedule changes with publish button */}
        {message.scheduleChanges && message.scheduleChanges.length > 0 && (
          <div className="mt-2">
            <div className="p-2 bg-white rounded border border-gray-200 text-xs text-gray-700 mb-2">
              <p className="font-medium mb-1">
                {message.scheduleChanges.length} schedule change
                {message.scheduleChanges.length !== 1 ? 's' : ''} proposed
              </p>
              {message.scheduleChanges.slice(0, 3).map((change, i) => (
                <p key={i} className="text-gray-600">
                  • {change.explanation}
                </p>
              ))}
              {message.scheduleChanges.length > 3 && (
                <p className="text-gray-500">
                  +{message.scheduleChanges.length - 3} more…
                </p>
              )}
            </div>
            {onPublish && (
              <button
                onClick={() => onPublish(message.scheduleChanges!)}
                className="w-full py-1.5 px-3 bg-green-600 hover:bg-green-700 text-white text-xs font-medium rounded transition-colors"
                data-testid="publish-schedule-btn"
              >
                Publish Schedule →
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export function SchedulingChat({ onPublishSchedule }: SchedulingChatProps) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { messages, sendMessage, isLoading, sessionId } = useSchedulingChat();

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = () => {
    const text = input.trim();
    if (!text || isLoading) return;
    setInput('');
    sendMessage(text);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div
      className="flex flex-col h-full bg-white border-l border-gray-200"
      data-testid="scheduling-chat"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 flex-shrink-0">
        <h2 className="text-sm font-semibold text-gray-900">
          AI Scheduling Assistant
        </h2>
        <span className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full font-medium">
          Opus 4.6
        </span>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-1">
        {messages.length === 0 && (
          <p className="text-sm text-gray-400 text-center mt-8">
            Ask me to build or adjust the schedule…
          </p>
        )}
        {messages.map((msg) => (
          <MessageBubble
            key={msg.id}
            message={msg}
            onPublish={onPublishSchedule}
          />
        ))}
        {isLoading && (
          <div className="flex items-start mb-4" data-testid="chat-message-assistant">
            <div className="bg-gray-100 rounded-lg px-3 py-2 text-sm text-gray-500 animate-pulse">
              Thinking…
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="flex-shrink-0 border-t border-gray-200 px-4 py-3">
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a scheduling command…"
            rows={2}
            className="flex-1 resize-none rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            aria-label="Chat input"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            className="self-end px-3 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 text-white text-sm font-medium rounded-md transition-colors"
            aria-label="Send message"
          >
            Send
          </button>
        </div>
        {sessionId && (
          <p className="text-xs text-gray-400 mt-1">Session: {sessionId.slice(0, 8)}…</p>
        )}
      </div>
    </div>
  );
}
