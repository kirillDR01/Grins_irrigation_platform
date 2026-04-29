/**
 * ResourceMobileChat — Mobile-optimized AI chat for Resource role.
 * Quick-action buttons for common field operations.
 */

import { useState } from 'react';
import { useSchedulingChat } from '../hooks/useSchedulingChat';

const QUICK_ACTIONS = [
  { label: 'Running late', message: "I'm running late on my current job." },
  { label: 'Pre-job info', message: 'Give me pre-job info for my next job.' },
  { label: 'Log parts', message: 'I need to log parts used on this job.' },
  { label: "Tomorrow's schedule", message: "What's my schedule for tomorrow?" },
] as const;

export function ResourceMobileChat() {
  const [input, setInput] = useState('');
  const { messages, sendMessage, isLoading } = useSchedulingChat();

  const handleQuickAction = (message: string) => {
    sendMessage(message);
  };

  const handleSend = () => {
    const text = input.trim();
    if (!text || isLoading) return;
    setInput('');
    sendMessage(text);
  };

  return (
    <div
      className="flex flex-col bg-white"
      data-testid="resource-mobile-chat"
    >
      {/* Quick actions */}
      <div className="px-4 py-3 border-b border-gray-200">
        <p className="text-xs font-medium text-gray-500 mb-2">Quick Actions</p>
        <div className="grid grid-cols-2 gap-2">
          {QUICK_ACTIONS.map((action) => (
            <button
              key={action.label}
              onClick={() => handleQuickAction(action.message)}
              disabled={isLoading}
              className="py-2 px-3 bg-gray-100 hover:bg-gray-200 disabled:opacity-50 text-gray-800 text-sm font-medium rounded-lg transition-colors text-left"
            >
              {action.label}
            </button>
          ))}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3 max-h-64">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}
          >
            <div
              className={`max-w-[90%] rounded-lg px-3 py-2 text-sm ${
                msg.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-900'
              }`}
            >
              <p className="whitespace-pre-wrap">{msg.content}</p>
              {/* Change request status */}
              {msg.changeRequestId && (
                <p className="mt-1 text-xs opacity-75">
                  Request #{msg.changeRequestId.slice(0, 8)} submitted
                </p>
              )}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex items-start">
            <div className="bg-gray-100 rounded-lg px-3 py-2 text-sm text-gray-500 animate-pulse">
              …
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="px-4 py-3 border-t border-gray-200">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Message…"
            className="flex-1 rounded-full border border-gray-300 px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            aria-label="Chat input"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 text-white text-sm font-medium rounded-full transition-colors"
            aria-label="Send"
          >
            →
          </button>
        </div>
      </div>
    </div>
  );
}
