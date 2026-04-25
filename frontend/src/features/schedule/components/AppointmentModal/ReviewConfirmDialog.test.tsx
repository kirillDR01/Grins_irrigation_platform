/**
 * Tests for ReviewConfirmDialog — confirm-and-send Google review SMS dialog.
 *
 * Covers happy path, 30-day-dedup 409, generic error, disabled-while-pending,
 * Cancel, and disabled Send when customer phone is missing.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReviewConfirmDialog } from './ReviewConfirmDialog';

// ── Mocks ────────────────────────────────────────────────────────────────────

const mockMutateAsync = vi.fn();
const mockIsPending = vi.fn(() => false);

vi.mock('../../hooks/useAppointmentMutations', () => ({
  useRequestReview: () => ({
    mutateAsync: mockMutateAsync,
    get isPending() {
      return mockIsPending();
    },
  }),
}));

const mockToastSuccess = vi.fn();
const mockToastInfo = vi.fn();
const mockToastError = vi.fn();

vi.mock('sonner', () => ({
  toast: {
    success: (...args: unknown[]) => mockToastSuccess(...args),
    info: (...args: unknown[]) => mockToastInfo(...args),
    error: (...args: unknown[]) => mockToastError(...args),
  },
}));

// ── Helpers ──────────────────────────────────────────────────────────────────

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

interface RenderOptions {
  open?: boolean;
  customerPhone?: string | null;
  onOpenChange?: (open: boolean) => void;
}

function renderDialog(opts: RenderOptions = {}) {
  const onOpenChange = opts.onOpenChange ?? vi.fn();
  const customerPhone: string | null =
    'customerPhone' in opts ? (opts.customerPhone as string | null) : '+19527373312';
  return {
    onOpenChange,
    ...render(
      <ReviewConfirmDialog
        appointmentId="appt-001"
        customerName="Jane Smith"
        customerPhone={customerPhone}
        open={opts.open ?? true}
        onOpenChange={onOpenChange}
      />,
      { wrapper: createWrapper() }
    ),
  };
}

/**
 * Build an axios-shaped error so the `axios.isAxiosError` check passes.
 */
function makeAxiosError(status: number, detail?: unknown) {
  const err: Record<string, unknown> = {
    isAxiosError: true,
    response: { status, data: { detail } },
    message: 'Request failed',
  };
  return err;
}

beforeEach(() => {
  vi.clearAllMocks();
  mockIsPending.mockReturnValue(false);
});

// ── Rendering ────────────────────────────────────────────────────────────────

describe('ReviewConfirmDialog — Rendering', () => {
  it('renders the confirm prompt with customer name and phone', () => {
    renderDialog();

    expect(screen.getByTestId('review-confirm-dialog')).toBeInTheDocument();
    expect(
      screen.getByText(/Send Google review SMS to Jane Smith at \+19527373312/i)
    ).toBeInTheDocument();
  });

  it('renders Send and Cancel buttons', () => {
    renderDialog();
    expect(screen.getByTestId('send-review-btn')).toBeInTheDocument();
    expect(screen.getByTestId('cancel-review-btn')).toBeInTheDocument();
  });

  it('does not render content when open=false', () => {
    renderDialog({ open: false });
    expect(screen.queryByTestId('review-confirm-dialog')).not.toBeInTheDocument();
  });

  it('disables Send button when customerPhone is null', () => {
    renderDialog({ customerPhone: null });
    expect(screen.getByTestId('send-review-btn')).toBeDisabled();
  });
});

// ── Send: happy path ─────────────────────────────────────────────────────────

describe('ReviewConfirmDialog — Send success', () => {
  it('calls mutateAsync, shows success toast, and closes the dialog', async () => {
    mockMutateAsync.mockResolvedValueOnce({
      success: true,
      message: 'Sent',
      already_requested: false,
    });
    const user = userEvent.setup();
    const { onOpenChange } = renderDialog();

    await user.click(screen.getByTestId('send-review-btn'));

    await waitFor(() => {
      expect(mockMutateAsync).toHaveBeenCalledWith('appt-001');
    });
    expect(mockToastSuccess).toHaveBeenCalledWith(
      'Review Requested',
      expect.objectContaining({
        description: 'Google review request sent to the customer.',
      })
    );
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });
});

// ── Send: 409 already-requested ──────────────────────────────────────────────

describe('ReviewConfirmDialog — 409 REVIEW_ALREADY_SENT', () => {
  it('shows info toast with the prior send date and closes the dialog', async () => {
    mockMutateAsync.mockRejectedValueOnce(
      makeAxiosError(409, {
        code: 'REVIEW_ALREADY_SENT',
        last_sent_at: '2026-04-10T15:30:00Z',
      })
    );
    const user = userEvent.setup();
    const { onOpenChange } = renderDialog();

    await user.click(screen.getByTestId('send-review-btn'));

    await waitFor(() => {
      expect(mockToastInfo).toHaveBeenCalled();
    });
    const [title, payload] = mockToastInfo.mock.calls[0];
    expect(title).toBe('Already Requested');
    expect((payload as { description: string }).description).toMatch(
      /Already sent within last 30 days \(sent /
    );
    expect(onOpenChange).toHaveBeenCalledWith(false);
    expect(mockToastError).not.toHaveBeenCalled();
  });
});

// ── Send: generic error ──────────────────────────────────────────────────────

describe('ReviewConfirmDialog — generic error', () => {
  it('shows error toast and leaves the dialog open', async () => {
    mockMutateAsync.mockRejectedValueOnce(new Error('boom'));
    const user = userEvent.setup();
    const onOpenChange = vi.fn();
    renderDialog({ onOpenChange });

    await user.click(screen.getByTestId('send-review-btn'));

    await waitFor(() => {
      expect(mockToastError).toHaveBeenCalledWith(
        'Error',
        expect.objectContaining({
          description: 'Failed to send review request.',
        })
      );
    });
    expect(onOpenChange).not.toHaveBeenCalled();
  });
});

// ── Pending state ────────────────────────────────────────────────────────────

describe('ReviewConfirmDialog — pending state', () => {
  it('disables Send and Cancel while mutation is pending', () => {
    mockIsPending.mockReturnValue(true);
    renderDialog();

    expect(screen.getByTestId('send-review-btn')).toBeDisabled();
    expect(screen.getByTestId('cancel-review-btn')).toBeDisabled();
  });
});

// ── Cancel ───────────────────────────────────────────────────────────────────

describe('ReviewConfirmDialog — Cancel', () => {
  it('closes dialog without firing the mutation when Cancel clicked', async () => {
    const user = userEvent.setup();
    const { onOpenChange } = renderDialog();

    await user.click(screen.getByTestId('cancel-review-btn'));

    expect(mockMutateAsync).not.toHaveBeenCalled();
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });
});
