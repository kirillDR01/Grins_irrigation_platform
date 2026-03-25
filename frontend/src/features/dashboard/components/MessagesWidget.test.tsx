/**
 * Tests for MessagesWidget component.
 * Validates: Requirements 4.1, 4.3
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MessagesWidget } from './MessagesWidget';

const mockNavigate = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...actual, useNavigate: () => mockNavigate };
});

vi.mock('../hooks', () => ({
  useUnaddressedCount: vi.fn(),
}));

import { useUnaddressedCount } from '../hooks';
const mockUseUnaddressedCount = useUnaddressedCount as ReturnType<typeof vi.fn>;

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>{children}</BrowserRouter>
      </QueryClientProvider>
    );
  };
}

describe('MessagesWidget', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders with unaddressed count', () => {
    mockUseUnaddressedCount.mockReturnValue({
      data: { count: 5 },
      isLoading: false,
    });

    render(<MessagesWidget />, { wrapper: createWrapper() });

    const widget = screen.getByTestId('messages-widget');
    expect(widget).toBeInTheDocument();
    expect(widget).toHaveTextContent('5');
    expect(widget).toHaveTextContent('5 unaddressed');
  });

  it('renders zero count with appropriate message', () => {
    mockUseUnaddressedCount.mockReturnValue({
      data: { count: 0 },
      isLoading: false,
    });

    render(<MessagesWidget />, { wrapper: createWrapper() });

    const widget = screen.getByTestId('messages-widget');
    expect(widget).toHaveTextContent('0');
    expect(widget).toHaveTextContent('No unaddressed messages');
    expect(screen.queryByTestId('messages-badge')).not.toBeInTheDocument();
  });

  it('shows badge when count > 0', () => {
    mockUseUnaddressedCount.mockReturnValue({
      data: { count: 12 },
      isLoading: false,
    });

    render(<MessagesWidget />, { wrapper: createWrapper() });

    const badge = screen.getByTestId('messages-badge');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent('12');
  });

  it('caps badge display at 99+', () => {
    mockUseUnaddressedCount.mockReturnValue({
      data: { count: 150 },
      isLoading: false,
    });

    render(<MessagesWidget />, { wrapper: createWrapper() });

    const badge = screen.getByTestId('messages-badge');
    expect(badge).toHaveTextContent('99+');
  });

  it('shows dash while loading', () => {
    mockUseUnaddressedCount.mockReturnValue({
      data: undefined,
      isLoading: true,
    });

    render(<MessagesWidget />, { wrapper: createWrapper() });

    const widget = screen.getByTestId('messages-widget');
    expect(widget).toHaveTextContent('—');
  });

  it('navigates to /communications on click', () => {
    mockUseUnaddressedCount.mockReturnValue({
      data: { count: 3 },
      isLoading: false,
    });

    render(<MessagesWidget />, { wrapper: createWrapper() });

    fireEvent.click(screen.getByTestId('messages-widget'));
    expect(mockNavigate).toHaveBeenCalledWith('/communications');
  });

  it('navigates to /communications on Enter key', () => {
    mockUseUnaddressedCount.mockReturnValue({
      data: { count: 3 },
      isLoading: false,
    });

    render(<MessagesWidget />, { wrapper: createWrapper() });

    fireEvent.keyDown(screen.getByTestId('messages-widget'), { key: 'Enter' });
    expect(mockNavigate).toHaveBeenCalledWith('/communications');
  });

  it('navigates to /communications on Space key', () => {
    mockUseUnaddressedCount.mockReturnValue({
      data: { count: 3 },
      isLoading: false,
    });

    render(<MessagesWidget />, { wrapper: createWrapper() });

    fireEvent.keyDown(screen.getByTestId('messages-widget'), { key: ' ' });
    expect(mockNavigate).toHaveBeenCalledWith('/communications');
  });
});
