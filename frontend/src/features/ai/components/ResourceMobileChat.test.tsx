/**
 * Tests for ResourceMobileChat component.
 * Validates: Requirements 30.6, 30.7, 30.8
 */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ResourceMobileChat } from './ResourceMobileChat';

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

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
  Send: () => <span>Send</span>,
  Loader2: () => <span>Loading</span>,
  Clock: () => <span>🕐</span>,
  ClipboardList: () => <span>📋</span>,
  Wrench: () => <span>🔧</span>,
  CalendarDays: () => <span>📅</span>,
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

describe('ResourceMobileChat', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockMutateAsync.mockResolvedValue({
      response: 'Your delay has been reported.',
      session_id: 'sess-r1',
      change_request_id: null,
    });
  });

  it('renders with data-testid', () => {
    render(<ResourceMobileChat />, { wrapper: createWrapper() });
    expect(screen.getByTestId('resource-mobile-chat')).toBeInTheDocument();
  });

  it('renders header', () => {
    render(<ResourceMobileChat />, { wrapper: createWrapper() });
    expect(screen.getByText('Field Assistant')).toBeInTheDocument();
  });

  it('renders quick-action buttons', () => {
    render(<ResourceMobileChat />, { wrapper: createWrapper() });
    expect(screen.getByTestId('quick-action-running-late')).toBeInTheDocument();
    expect(screen.getByTestId('quick-action-pre-job-info')).toBeInTheDocument();
    expect(screen.getByTestId('quick-action-log-parts')).toBeInTheDocument();
    expect(screen.getByTestId("quick-action-tomorrow's-schedule")).toBeInTheDocument();
  });

  it('sends message when quick-action is clicked', async () => {
    const user = userEvent.setup();
    render(<ResourceMobileChat />, { wrapper: createWrapper() });

    await user.click(screen.getByTestId('quick-action-running-late'));
    expect(mockMutateAsync).toHaveBeenCalledWith({
      message: 'I am running late',
      session_id: undefined,
    });
  });

  it('renders chat input', () => {
    render(<ResourceMobileChat />, { wrapper: createWrapper() });
    expect(screen.getByTestId('resource-chat-input')).toBeInTheDocument();
  });

  it('renders send button', () => {
    render(<ResourceMobileChat />, { wrapper: createWrapper() });
    expect(screen.getByTestId('resource-chat-send')).toBeInTheDocument();
  });

  it('sends typed message on submit', async () => {
    const user = userEvent.setup();
    render(<ResourceMobileChat />, { wrapper: createWrapper() });

    const input = screen.getByTestId('resource-chat-input');
    await user.type(input, 'Need help at site');
    await user.click(screen.getByTestId('resource-chat-send'));

    expect(mockMutateAsync).toHaveBeenCalledWith({
      message: 'Need help at site',
      session_id: undefined,
    });
  });

  it('displays assistant response', async () => {
    const user = userEvent.setup();
    render(<ResourceMobileChat />, { wrapper: createWrapper() });

    await user.click(screen.getByTestId('quick-action-running-late'));
    expect(await screen.findByText('Your delay has been reported.')).toBeInTheDocument();
  });

  it('displays change request status when present', async () => {
    mockMutateAsync.mockResolvedValue({
      response: 'Follow-up request submitted.',
      session_id: 'sess-r1',
      change_request_id: 'cr-123',
    });
    const user = userEvent.setup();
    render(<ResourceMobileChat />, { wrapper: createWrapper() });

    const input = screen.getByTestId('resource-chat-input');
    await user.type(input, 'Request follow-up');
    await user.click(screen.getByTestId('resource-chat-send'));

    expect(await screen.findByText(/pending admin approval/)).toBeInTheDocument();
  });
});
