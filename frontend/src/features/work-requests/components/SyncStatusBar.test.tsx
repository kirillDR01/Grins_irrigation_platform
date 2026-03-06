import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SyncStatusBar } from './SyncStatusBar';
import { workRequestApi } from '../api/workRequestApi';

vi.mock('../api/workRequestApi', () => ({
  workRequestApi: {
    getSyncStatus: vi.fn(),
  },
}));

const mockedApi = vi.mocked(workRequestApi);

function renderWithProviders() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <SyncStatusBar />
    </QueryClientProvider>
  );
}

describe('SyncStatusBar', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders nothing when status is not loaded', () => {
    mockedApi.getSyncStatus.mockReturnValue(new Promise(() => {})); // never resolves
    const { container } = renderWithProviders();
    expect(container.querySelector('[data-testid="sync-status-bar"]')).toBeNull();
  });

  it('shows running state with green indicator', async () => {
    mockedApi.getSyncStatus.mockResolvedValue({
      is_running: true,
      last_sync: null,
      last_error: null,
    });
    renderWithProviders();
    await waitFor(() => {
      expect(screen.getByTestId('sync-status-bar')).toBeInTheDocument();
    });
    const indicator = screen.getByTestId('sync-status-indicator');
    expect(indicator.className).toContain('bg-green-500');
    expect(screen.getByTestId('sync-status-text')).toHaveTextContent('Syncing');
  });

  it('shows stopped state with gray indicator', async () => {
    mockedApi.getSyncStatus.mockResolvedValue({
      is_running: false,
      last_sync: null,
      last_error: null,
    });
    renderWithProviders();
    await waitFor(() => {
      expect(screen.getByTestId('sync-status-bar')).toBeInTheDocument();
    });
    const indicator = screen.getByTestId('sync-status-indicator');
    expect(indicator.className).toContain('bg-gray-400');
    expect(screen.getByTestId('sync-status-text')).toHaveTextContent('Stopped');
  });

  it('displays last sync time when available', async () => {
    const recentDate = new Date(Date.now() - 5 * 60 * 1000).toISOString(); // 5 min ago
    mockedApi.getSyncStatus.mockResolvedValue({
      is_running: true,
      last_sync: recentDate,
      last_error: null,
    });
    renderWithProviders();
    await waitFor(() => {
      expect(screen.getByTestId('sync-last-time')).toBeInTheDocument();
    });
    expect(screen.getByTestId('sync-last-time')).toHaveTextContent(/Last sync/);
  });

  it('does not show last sync time when null', async () => {
    mockedApi.getSyncStatus.mockResolvedValue({
      is_running: true,
      last_sync: null,
      last_error: null,
    });
    renderWithProviders();
    await waitFor(() => {
      expect(screen.getByTestId('sync-status-bar')).toBeInTheDocument();
    });
    expect(screen.queryByTestId('sync-last-time')).toBeNull();
  });

  it('displays error message when present', async () => {
    mockedApi.getSyncStatus.mockResolvedValue({
      is_running: false,
      last_sync: null,
      last_error: 'Connection timeout',
    });
    renderWithProviders();
    await waitFor(() => {
      expect(screen.getByTestId('sync-error')).toBeInTheDocument();
    });
    expect(screen.getByTestId('sync-error')).toHaveTextContent('Connection timeout');
  });

  it('does not show error when null', async () => {
    mockedApi.getSyncStatus.mockResolvedValue({
      is_running: true,
      last_sync: null,
      last_error: null,
    });
    renderWithProviders();
    await waitFor(() => {
      expect(screen.getByTestId('sync-status-bar')).toBeInTheDocument();
    });
    expect(screen.queryByTestId('sync-error')).toBeNull();
  });
});
