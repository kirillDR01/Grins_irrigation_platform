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

  it('renders criteria badges when criteriaUsed present (Bug 4 surface)', () => {
    vi.mocked(useSchedulingChat).mockReturnValue({
      ...defaultHook,
      messages: [
        {
          id: '1',
          role: 'assistant',
          content: 'Scheduled using proximity.',
          criteriaUsed: [
            { number: 1, name: 'Proximity' },
            { number: 7, name: 'Skill match' },
          ],
        },
      ],
    });
    render(<SchedulingChat />, { wrapper });
    expect(screen.getByTestId('chat-criteria-badge-1')).toBeInTheDocument();
    expect(screen.getByTestId('chat-criteria-badge-7')).toBeInTheDocument();
  });

  it('renders the schedule summary block when scheduleSummary present (Bug 4)', () => {
    vi.mocked(useSchedulingChat).mockReturnValue({
      ...defaultHook,
      messages: [
        {
          id: '1',
          role: 'assistant',
          content: 'Here is your week.',
          scheduleSummary: 'Mon: 10 jobs, Tue: 8 jobs',
        },
      ],
    });
    render(<SchedulingChat />, { wrapper });
    const summary = screen.getByTestId('chat-schedule-summary');
    expect(summary).toBeInTheDocument();
    expect(summary).toHaveTextContent('Mon: 10 jobs, Tue: 8 jobs');
  });

  it('does not render the schedule summary block when scheduleSummary is null', () => {
    vi.mocked(useSchedulingChat).mockReturnValue({
      ...defaultHook,
      messages: [
        {
          id: '1',
          role: 'assistant',
          content: 'No solution yet.',
          scheduleSummary: null,
        },
      ],
    });
    render(<SchedulingChat />, { wrapper });
    expect(screen.queryByTestId('chat-schedule-summary')).not.toBeInTheDocument();
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
