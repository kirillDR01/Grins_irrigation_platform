import { describe, it, expect, vi, beforeEach, beforeAll } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

vi.mock('../hooks/useSchedulingChat', () => ({
  useSchedulingChat: vi.fn(),
}));

import { SchedulingChat } from './SchedulingChat';
import { useSchedulingChat } from '../hooks/useSchedulingChat';

// jsdom doesn't implement scrollIntoView
beforeAll(() => {
  window.HTMLElement.prototype.scrollIntoView = vi.fn();
});

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

const defaultHook = {
  messages: [],
  sendMessage: vi.fn(),
  isLoading: false,
  sessionId: undefined,
};

describe('SchedulingChat', () => {
  beforeEach(() => {
    vi.mocked(useSchedulingChat).mockReturnValue(defaultHook);
  });

  it('renders with data-testid="scheduling-chat"', () => {
    render(<SchedulingChat />, { wrapper });
    expect(screen.getByTestId('scheduling-chat')).toBeInTheDocument();
  });

  it('shows empty state prompt when no messages', () => {
    render(<SchedulingChat />, { wrapper });
    expect(screen.getByText(/Ask me to build or adjust the schedule/)).toBeInTheDocument();
  });

  it('renders user and assistant messages', () => {
    vi.mocked(useSchedulingChat).mockReturnValue({
      ...defaultHook,
      messages: [
        { id: '1', role: 'user', content: 'Schedule Monday' },
        { id: '2', role: 'assistant', content: 'Done! Here is the schedule.' },
      ],
    });
    render(<SchedulingChat />, { wrapper });
    expect(screen.getByTestId('chat-message-user')).toBeInTheDocument();
    expect(screen.getByTestId('chat-message-assistant')).toBeInTheDocument();
  });

  it('renders criteria tags when criteriaUsed present', () => {
    vi.mocked(useSchedulingChat).mockReturnValue({
      ...defaultHook,
      messages: [
        {
          id: '1',
          role: 'assistant',
          content: 'Scheduled using proximity.',
          criteriaUsed: [{ number: 1, name: 'Proximity' }],
        },
      ],
    });
    render(<SchedulingChat />, { wrapper });
    expect(screen.getByTestId('criteria-tag-1')).toBeInTheDocument();
  });

  it('renders publish schedule button when scheduleChanges present', () => {
    const onPublish = vi.fn();
    vi.mocked(useSchedulingChat).mockReturnValue({
      ...defaultHook,
      messages: [
        {
          id: '1',
          role: 'assistant',
          content: 'Changes proposed.',
          scheduleChanges: [
            { change_type: 'reassign', job_id: 'j1', staff_id: 's1', old_slot: null, new_slot: null, explanation: 'Better fit' },
          ],
        },
      ],
    });
    render(<SchedulingChat onPublishSchedule={onPublish} />, { wrapper });
    expect(screen.getByTestId('publish-schedule-btn')).toBeInTheDocument();
  });

  it('calls onPublishSchedule when publish button clicked', () => {
    const onPublish = vi.fn();
    const changes = [
      { change_type: 'reassign', job_id: 'j1', staff_id: 's1', old_slot: null, new_slot: null, explanation: 'Better fit' },
    ];
    vi.mocked(useSchedulingChat).mockReturnValue({
      ...defaultHook,
      messages: [{ id: '1', role: 'assistant', content: 'Done', scheduleChanges: changes }],
    });
    render(<SchedulingChat onPublishSchedule={onPublish} />, { wrapper });
    fireEvent.click(screen.getByTestId('publish-schedule-btn'));
    expect(onPublish).toHaveBeenCalledWith(changes);
  });

  it('shows loading indicator when isLoading', () => {
    vi.mocked(useSchedulingChat).mockReturnValue({ ...defaultHook, isLoading: true });
    render(<SchedulingChat />, { wrapper });
    expect(screen.getByText('Thinking…')).toBeInTheDocument();
  });

  it('send button is disabled when input is empty', () => {
    render(<SchedulingChat />, { wrapper });
    const sendBtn = screen.getByRole('button', { name: /send message/i });
    expect(sendBtn).toBeDisabled();
  });

  it('calls sendMessage when send button clicked with text', () => {
    const sendMessage = vi.fn();
    vi.mocked(useSchedulingChat).mockReturnValue({ ...defaultHook, sendMessage });
    render(<SchedulingChat />, { wrapper });
    const textarea = screen.getByRole('textbox', { name: /chat input/i });
    fireEvent.change(textarea, { target: { value: 'Schedule Monday' } });
    fireEvent.click(screen.getByRole('button', { name: /send message/i }));
    expect(sendMessage).toHaveBeenCalledWith('Schedule Monday');
  });
});
