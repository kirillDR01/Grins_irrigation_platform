/**
 * Tests for SchedulingChat component.
 * Validates: Requirements 30.6, 30.7, 30.8
 */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { SchedulingChat } from './SchedulingChat';

const mockMutateAsync = vi.fn();

vi.mock('../hooks/useSchedulingChat', () => ({
  useSchedulingChat: vi.fn(() => ({
    mutateAsync: mockMutateAsync,
    isPending: false,
    error: null,
  })),
}));

// Mock scrollIntoView for jsdom
Element.prototype.scrollIntoView = vi.fn();

// Mock lucide-react icons to avoid SVG rendering issues
vi.mock('lucide-react', () => ({
  Send: () => <span data-testid="icon-send">Send</span>,
  Loader2: () => <span data-testid="icon-loader">Loading</span>,
  Sparkles: () => <span data-testid="icon-sparkles">✨</span>,
  CalendarCheck: () => <span data-testid="icon-calendar">📅</span>,
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

describe('SchedulingChat', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockMutateAsync.mockResolvedValue({
      response: 'I can help with that schedule.',
      session_id: 'sess-1',
      schedule_changes: null,
      clarifying_questions: null,
      change_request_id: null,
      criteria_used: [1, 3],
    });
  });

  it('renders with data-testid', () => {
    render(<SchedulingChat />, { wrapper: createWrapper() });
    expect(screen.getByTestId('scheduling-chat')).toBeInTheDocument();
  });

  it('renders chat input field', () => {
    render(<SchedulingChat />, { wrapper: createWrapper() });
    expect(screen.getByTestId('scheduling-chat-input')).toBeInTheDocument();
  });

  it('renders send button', () => {
    render(<SchedulingChat />, { wrapper: createWrapper() });
    expect(screen.getByTestId('scheduling-chat-send')).toBeInTheDocument();
  });

  it('renders header with assistant title', () => {
    render(<SchedulingChat />, { wrapper: createWrapper() });
    expect(screen.getByText('AI Scheduling Assistant')).toBeInTheDocument();
  });

  it('renders model badge', () => {
    render(<SchedulingChat />, { wrapper: createWrapper() });
    expect(screen.getByText('GPT-4o')).toBeInTheDocument();
  });

  it('displays placeholder text in input', () => {
    render(<SchedulingChat />, { wrapper: createWrapper() });
    expect(screen.getByPlaceholderText('Ask the scheduling assistant...')).toBeInTheDocument();
  });

  it('sends message and displays user message', async () => {
    const user = userEvent.setup();
    render(<SchedulingChat />, { wrapper: createWrapper() });

    const input = screen.getByTestId('scheduling-chat-input');
    await user.type(input, 'Build schedule for next week');
    await user.click(screen.getByTestId('scheduling-chat-send'));

    expect(screen.getByText('Build schedule for next week')).toBeInTheDocument();
    expect(mockMutateAsync).toHaveBeenCalledWith({
      message: 'Build schedule for next week',
      session_id: undefined,
    });
  });

  it('displays assistant response after sending', async () => {
    const user = userEvent.setup();
    render(<SchedulingChat />, { wrapper: createWrapper() });

    const input = screen.getByTestId('scheduling-chat-input');
    await user.type(input, 'Hello');
    await user.click(screen.getByTestId('scheduling-chat-send'));

    expect(await screen.findByText('I can help with that schedule.')).toBeInTheDocument();
  });

  it('send button is disabled when input is empty', () => {
    render(<SchedulingChat />, { wrapper: createWrapper() });
    expect(screen.getByTestId('scheduling-chat-send')).toBeDisabled();
  });
});
