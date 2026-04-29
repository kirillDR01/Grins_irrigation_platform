import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

vi.mock('../hooks/useSchedulingChat', () => ({
  useSchedulingChat: vi.fn(),
}));

import { ResourceMobileChat } from './ResourceMobileChat';
import { useSchedulingChat } from '../hooks/useSchedulingChat';

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

describe('ResourceMobileChat', () => {
  beforeEach(() => {
    vi.mocked(useSchedulingChat).mockReturnValue(defaultHook);
  });

  it('renders with data-testid="resource-mobile-chat"', () => {
    render(<ResourceMobileChat />, { wrapper });
    expect(screen.getByTestId('resource-mobile-chat')).toBeInTheDocument();
  });

  it('renders all 4 quick action buttons', () => {
    render(<ResourceMobileChat />, { wrapper });
    expect(screen.getByText('Running late')).toBeInTheDocument();
    expect(screen.getByText('Pre-job info')).toBeInTheDocument();
    expect(screen.getByText('Log parts')).toBeInTheDocument();
    expect(screen.getByText("Tomorrow's schedule")).toBeInTheDocument();
  });

  it('calls sendMessage with correct text when quick action clicked', () => {
    const sendMessage = vi.fn();
    vi.mocked(useSchedulingChat).mockReturnValue({ ...defaultHook, sendMessage });
    render(<ResourceMobileChat />, { wrapper });
    fireEvent.click(screen.getByText('Running late'));
    expect(sendMessage).toHaveBeenCalledWith("I'm running late on my current job.");
  });

  it('renders assistant message content', () => {
    vi.mocked(useSchedulingChat).mockReturnValue({
      ...defaultHook,
      messages: [
        { id: '1', role: 'user', content: 'Hello' },
        { id: '2', role: 'assistant', content: 'Noted, notifying customer.' },
      ],
    });
    render(<ResourceMobileChat />, { wrapper });
    expect(screen.getByText('Noted, notifying customer.')).toBeInTheDocument();
  });

  it('shows change request id when present in message', () => {
    vi.mocked(useSchedulingChat).mockReturnValue({
      ...defaultHook,
      messages: [
        { id: '1', role: 'assistant', content: 'Request submitted.', changeRequestId: 'cr-abc123' },
      ],
    });
    render(<ResourceMobileChat />, { wrapper });
    expect(screen.getByText(/Request #cr-abc1/)).toBeInTheDocument();
  });

  it('shows loading indicator when isLoading', () => {
    vi.mocked(useSchedulingChat).mockReturnValue({ ...defaultHook, isLoading: true });
    render(<ResourceMobileChat />, { wrapper });
    expect(screen.getByText('…')).toBeInTheDocument();
  });

  it('disables quick action buttons when loading', () => {
    vi.mocked(useSchedulingChat).mockReturnValue({ ...defaultHook, isLoading: true });
    render(<ResourceMobileChat />, { wrapper });
    const btn = screen.getByText('Running late');
    expect(btn).toBeDisabled();
  });

  it('calls sendMessage when text input submitted', () => {
    const sendMessage = vi.fn();
    vi.mocked(useSchedulingChat).mockReturnValue({ ...defaultHook, sendMessage });
    render(<ResourceMobileChat />, { wrapper });
    const input = screen.getByRole('textbox', { name: /chat input/i });
    fireEvent.change(input, { target: { value: 'Custom message' } });
    fireEvent.click(screen.getByRole('button', { name: /send/i }));
    expect(sendMessage).toHaveBeenCalledWith('Custom message');
  });
});
