/**
 * Tests for ActionTrack — card states for each step, tap handlers call
 * correct mutations, disabled states, hidden for terminal statuses.
 * Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5, 4.7
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ActionTrack } from './ActionTrack';
import type { AppointmentStatus } from '../../types';

// ── Mock mutation hooks ──────────────────────────────────────────────────────

const mockEnRouteMutate = vi.fn();
const mockArrivedMutate = vi.fn();
const mockCompletedMutate = vi.fn();

vi.mock('../../hooks/useAppointmentMutations', () => ({
  useMarkAppointmentEnRoute: () => ({
    mutate: mockEnRouteMutate,
    isPending: false,
  }),
  useMarkAppointmentArrived: () => ({
    mutate: mockArrivedMutate,
    isPending: false,
  }),
  useMarkAppointmentCompleted: () => ({
    mutate: mockCompletedMutate,
    isPending: false,
  }),
}));

// ── Helpers ──────────────────────────────────────────────────────────────────

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

interface RenderProps {
  status: AppointmentStatus;
  enRouteAt?: string | null;
  arrivedAt?: string | null;
  completedAt?: string | null;
}

function renderActionTrack({
  status,
  enRouteAt = null,
  arrivedAt = null,
  completedAt = null,
}: RenderProps) {
  return render(
    <ActionTrack
      appointmentId="appt-001"
      status={status}
      enRouteAt={enRouteAt}
      arrivedAt={arrivedAt}
      completedAt={completedAt}
    />,
    { wrapper: createWrapper() },
  );
}

// ── Hidden for terminal statuses (Req 4.8) ───────────────────────────────────

describe('ActionTrack — Hidden for terminal statuses (Req 4.8)', () => {
  beforeEach(() => vi.clearAllMocks());

  it.each(['pending', 'draft', 'cancelled', 'no_show'] as AppointmentStatus[])(
    'returns null for %s status',
    (status) => {
      const { container } = renderActionTrack({ status });
      expect(container.innerHTML).toBe('');
    },
  );

  it.each([
    'confirmed',
    'scheduled',
    'en_route',
    'in_progress',
    'completed',
  ] as AppointmentStatus[])(
    'renders cards for %s status',
    (status) => {
      renderActionTrack({
        status,
        enRouteAt:
          status === 'en_route' || status === 'in_progress' || status === 'completed'
            ? '2025-07-15T09:30:00Z'
            : null,
        arrivedAt:
          status === 'in_progress' || status === 'completed'
            ? '2025-07-15T10:00:00Z'
            : null,
        completedAt: status === 'completed' ? '2025-07-15T11:00:00Z' : null,
      });

      expect(screen.getByRole('button', { name: /mark as en route/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /mark as on site/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /mark as done/i })).toBeInTheDocument();
    },
  );
});

// ── Three cards rendered (Req 4.1) ───────────────────────────────────────────

describe('ActionTrack — Three cards rendered (Req 4.1)', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders exactly 3 action card buttons', () => {
    renderActionTrack({ status: 'confirmed' });

    const buttons = screen.getAllByRole('button');
    expect(buttons).toHaveLength(3);
  });

  it('renders cards with labels: En route, On site, Done', () => {
    renderActionTrack({ status: 'confirmed' });

    expect(screen.getByText('En route')).toBeInTheDocument();
    expect(screen.getByText('On site')).toBeInTheDocument();
    expect(screen.getByText('Done')).toBeInTheDocument();
  });

  it('renders cards with accessible aria-labels', () => {
    renderActionTrack({ status: 'confirmed' });

    expect(screen.getByRole('button', { name: 'Mark as en route' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Mark as on site' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Mark as done' })).toBeInTheDocument();
  });
});

// ── Card states for step 0 — Booked/confirmed (Req 4.3) ─────────────────────
// At step 0, all three cards are disabled because cardState uses indices 1, 2, 3
// and step(0) < all card indices.

describe('ActionTrack — Step 0 (Booked/confirmed)', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders all three cards as disabled (opacity 0.4, cursor not-allowed)', () => {
    renderActionTrack({ status: 'confirmed' });

    const buttons = screen.getAllByRole('button');
    buttons.forEach((btn) => {
      expect(btn.className).toContain('opacity-40');
      expect(btn.className).toContain('cursor-not-allowed');
      expect(btn).toBeDisabled();
    });
  });
});

// ── Card states for step 1 — En route (Req 4.2, 4.3) ────────────────────────
// At step 1: "En route" card is active, "On site" and "Done" are disabled.

describe('ActionTrack — Step 1 (En route)', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders "En route" card as active (stage color fill, not disabled)', () => {
    renderActionTrack({
      status: 'en_route',
      enRouteAt: '2025-07-15T09:30:00Z',
    });

    const enRouteBtn = screen.getByRole('button', { name: /mark as en route/i });
    expect(enRouteBtn.className).toContain('bg-cyan-600');
    expect(enRouteBtn.className).toContain('text-white');
    expect(enRouteBtn).not.toBeDisabled();
  });

  it('renders "On site" card as disabled', () => {
    renderActionTrack({
      status: 'en_route',
      enRouteAt: '2025-07-15T09:30:00Z',
    });

    const onSiteBtn = screen.getByRole('button', { name: /mark as on site/i });
    expect(onSiteBtn.className).toContain('opacity-40');
    expect(onSiteBtn.className).toContain('cursor-not-allowed');
    expect(onSiteBtn).toBeDisabled();
  });

  it('renders "Done" card as disabled', () => {
    renderActionTrack({
      status: 'en_route',
      enRouteAt: '2025-07-15T09:30:00Z',
    });

    const doneBtn = screen.getByRole('button', { name: /mark as done/i });
    expect(doneBtn.className).toContain('opacity-40');
    expect(doneBtn.className).toContain('cursor-not-allowed');
    expect(doneBtn).toBeDisabled();
  });
});

// ── Card states for step 2 — On site / in_progress (Req 4.2, 4.3, 4.4) ─────
// At step 2: "En route" card is done, "On site" card is active, "Done" is disabled.

describe('ActionTrack — Step 2 (On site / in_progress)', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders "En route" card as done (white bg, green border)', () => {
    renderActionTrack({
      status: 'in_progress',
      enRouteAt: '2025-07-15T09:30:00Z',
      arrivedAt: '2025-07-15T10:00:00Z',
    });

    const enRouteBtn = screen.getByRole('button', { name: /mark as en route/i });
    expect(enRouteBtn.className).toContain('border-green-400');
    expect(enRouteBtn.className).toContain('bg-white');
  });

  it('renders "On site" card as active (stage color fill)', () => {
    renderActionTrack({
      status: 'in_progress',
      enRouteAt: '2025-07-15T09:30:00Z',
      arrivedAt: '2025-07-15T10:00:00Z',
    });

    const onSiteBtn = screen.getByRole('button', { name: /mark as on site/i });
    expect(onSiteBtn.className).toContain('bg-orange-500');
    expect(onSiteBtn.className).toContain('text-white');
    expect(onSiteBtn).not.toBeDisabled();
  });

  it('renders "Done" card as disabled', () => {
    renderActionTrack({
      status: 'in_progress',
      enRouteAt: '2025-07-15T09:30:00Z',
      arrivedAt: '2025-07-15T10:00:00Z',
    });

    const doneBtn = screen.getByRole('button', { name: /mark as done/i });
    expect(doneBtn.className).toContain('opacity-40');
    expect(doneBtn.className).toContain('cursor-not-allowed');
    expect(doneBtn).toBeDisabled();
  });

  it('displays completion timestamp on the done "En route" card', () => {
    renderActionTrack({
      status: 'in_progress',
      enRouteAt: '2025-07-15T09:30:00Z',
      arrivedAt: '2025-07-15T10:00:00Z',
    });

    const enRouteBtn = screen.getByRole('button', { name: /mark as en route/i });
    const monoSpan = enRouteBtn.querySelector('.font-mono');
    expect(monoSpan).toBeTruthy();
  });
});

// ── Card states for step 3 — Completed (Req 4.4) ────────────────────────────
// At step 3: "En route" and "On site" are done, "Done" card is active.

describe('ActionTrack — Step 3 (Completed)', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders "En route" and "On site" cards as done (green border)', () => {
    renderActionTrack({
      status: 'completed',
      enRouteAt: '2025-07-15T09:30:00Z',
      arrivedAt: '2025-07-15T10:00:00Z',
      completedAt: '2025-07-15T11:00:00Z',
    });

    const enRouteBtn = screen.getByRole('button', { name: /mark as en route/i });
    const onSiteBtn = screen.getByRole('button', { name: /mark as on site/i });

    expect(enRouteBtn.className).toContain('border-green-400');
    expect(enRouteBtn.className).toContain('bg-white');
    expect(onSiteBtn.className).toContain('border-green-400');
    expect(onSiteBtn.className).toContain('bg-white');
  });

  it('renders "Done" card as active (stage color fill)', () => {
    renderActionTrack({
      status: 'completed',
      enRouteAt: '2025-07-15T09:30:00Z',
      arrivedAt: '2025-07-15T10:00:00Z',
      completedAt: '2025-07-15T11:00:00Z',
    });

    const doneBtn = screen.getByRole('button', { name: /mark as done/i });
    expect(doneBtn.className).toContain('bg-green-600');
    expect(doneBtn.className).toContain('text-white');
    expect(doneBtn).not.toBeDisabled();
  });

  it('displays completion timestamps on done cards', () => {
    renderActionTrack({
      status: 'completed',
      enRouteAt: '2025-07-15T09:30:00Z',
      arrivedAt: '2025-07-15T10:00:00Z',
      completedAt: '2025-07-15T11:00:00Z',
    });

    // Done cards (En route and On site) should show timestamps in mono font
    const enRouteBtn = screen.getByRole('button', { name: /mark as en route/i });
    const onSiteBtn = screen.getByRole('button', { name: /mark as on site/i });

    expect(enRouteBtn.querySelector('.font-mono')).toBeTruthy();
    expect(onSiteBtn.querySelector('.font-mono')).toBeTruthy();
  });
});

// ── Tap handlers call correct mutations (Req 4.5) ───────────────────────────

describe('ActionTrack — Tap handlers call correct mutations (Req 4.5)', () => {
  beforeEach(() => vi.clearAllMocks());

  it('calls useMarkAppointmentEnRoute when tapping active "En route" card at step 1', async () => {
    const user = userEvent.setup();
    renderActionTrack({
      status: 'en_route',
      enRouteAt: '2025-07-15T09:30:00Z',
    });

    await user.click(screen.getByRole('button', { name: /mark as en route/i }));

    expect(mockEnRouteMutate).toHaveBeenCalledTimes(1);
    expect(mockEnRouteMutate).toHaveBeenCalledWith('appt-001', expect.any(Object));
  });

  it('calls useMarkAppointmentArrived when tapping active "On site" card at step 2', async () => {
    const user = userEvent.setup();
    renderActionTrack({
      status: 'in_progress',
      enRouteAt: '2025-07-15T09:30:00Z',
      arrivedAt: '2025-07-15T10:00:00Z',
    });

    await user.click(screen.getByRole('button', { name: /mark as on site/i }));

    expect(mockArrivedMutate).toHaveBeenCalledTimes(1);
    expect(mockArrivedMutate).toHaveBeenCalledWith('appt-001', expect.any(Object));
  });

  it('calls useMarkAppointmentCompleted when tapping active "Done" card at step 3', async () => {
    const user = userEvent.setup();
    renderActionTrack({
      status: 'completed',
      enRouteAt: '2025-07-15T09:30:00Z',
      arrivedAt: '2025-07-15T10:00:00Z',
      completedAt: '2025-07-15T11:00:00Z',
    });

    await user.click(screen.getByRole('button', { name: /mark as done/i }));

    expect(mockCompletedMutate).toHaveBeenCalledTimes(1);
    expect(mockCompletedMutate).toHaveBeenCalledWith('appt-001', expect.any(Object));
  });
});

// ── Disabled cards cannot be clicked (Req 4.3) ──────────────────────────────

describe('ActionTrack — Disabled cards cannot be clicked (Req 4.3)', () => {
  beforeEach(() => vi.clearAllMocks());

  it('does not call any mutation when clicking disabled cards at step 0', async () => {
    const user = userEvent.setup();
    renderActionTrack({ status: 'confirmed' });

    // All cards are disabled at step 0
    await user.click(screen.getByRole('button', { name: /mark as en route/i }));
    await user.click(screen.getByRole('button', { name: /mark as on site/i }));
    await user.click(screen.getByRole('button', { name: /mark as done/i }));

    expect(mockEnRouteMutate).not.toHaveBeenCalled();
    expect(mockArrivedMutate).not.toHaveBeenCalled();
    expect(mockCompletedMutate).not.toHaveBeenCalled();
  });

  it('does not call arrived or completed mutations when clicking disabled cards at step 1', async () => {
    const user = userEvent.setup();
    renderActionTrack({
      status: 'en_route',
      enRouteAt: '2025-07-15T09:30:00Z',
    });

    // "On site" and "Done" are disabled at step 1
    await user.click(screen.getByRole('button', { name: /mark as on site/i }));
    await user.click(screen.getByRole('button', { name: /mark as done/i }));

    expect(mockArrivedMutate).not.toHaveBeenCalled();
    expect(mockCompletedMutate).not.toHaveBeenCalled();
  });

  it('does not call completed mutation when clicking disabled "Done" card at step 2', async () => {
    const user = userEvent.setup();
    renderActionTrack({
      status: 'in_progress',
      enRouteAt: '2025-07-15T09:30:00Z',
      arrivedAt: '2025-07-15T10:00:00Z',
    });

    await user.click(screen.getByRole('button', { name: /mark as done/i }));

    expect(mockCompletedMutate).not.toHaveBeenCalled();
  });
});

// ── Done cards do not re-trigger mutations (Req 4.3) ─────────────────────────

describe('ActionTrack — Done cards do not re-trigger mutations', () => {
  beforeEach(() => vi.clearAllMocks());

  it('does not call en route mutation when clicking done "En route" card at step 2', async () => {
    const user = userEvent.setup();
    renderActionTrack({
      status: 'in_progress',
      enRouteAt: '2025-07-15T09:30:00Z',
      arrivedAt: '2025-07-15T10:00:00Z',
    });

    // "En route" card is done at step 2 — clicking it should not trigger mutation
    const enRouteBtn = screen.getByRole('button', { name: /mark as en route/i });
    await user.click(enRouteBtn);

    expect(mockEnRouteMutate).not.toHaveBeenCalled();
  });
});

// ── Accessibility: aria-live on done cards (Req 4.7) ─────────────────────────

describe('ActionTrack — Accessibility (Req 4.7)', () => {
  beforeEach(() => vi.clearAllMocks());

  it('sets aria-live="polite" on done cards for completion announcements', () => {
    renderActionTrack({
      status: 'in_progress',
      enRouteAt: '2025-07-15T09:30:00Z',
      arrivedAt: '2025-07-15T10:00:00Z',
    });

    // "En route" card is done at step 2
    const enRouteBtn = screen.getByRole('button', { name: /mark as en route/i });
    expect(enRouteBtn).toHaveAttribute('aria-live', 'polite');
  });

  it('does not set aria-live on active or disabled cards', () => {
    renderActionTrack({
      status: 'in_progress',
      enRouteAt: '2025-07-15T09:30:00Z',
      arrivedAt: '2025-07-15T10:00:00Z',
    });

    // "On site" is active, "Done" is disabled at step 2
    const onSiteBtn = screen.getByRole('button', { name: /mark as on site/i });
    const doneBtn = screen.getByRole('button', { name: /mark as done/i });

    expect(onSiteBtn).not.toHaveAttribute('aria-live');
    expect(doneBtn).not.toHaveAttribute('aria-live');
  });

  it('uses <button> elements with type="button" for all action cards', () => {
    renderActionTrack({ status: 'confirmed' });

    const buttons = screen.getAllByRole('button');
    buttons.forEach((btn) => {
      expect(btn.tagName).toBe('BUTTON');
      expect(btn).toHaveAttribute('type', 'button');
    });
  });
});

// ── Layout: flex gap container (Req 4.1) ─────────────────────────────────────

describe('ActionTrack — Layout (Req 4.1)', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders cards in a flex container with gap', () => {
    const { container } = renderActionTrack({ status: 'confirmed' });

    const wrapper = container.firstElementChild as HTMLElement;
    expect(wrapper.className).toContain('flex');
    expect(wrapper.className).toContain('gap-');
  });

  it('each card has flex-1 and min-height 104px', () => {
    renderActionTrack({ status: 'confirmed' });

    const buttons = screen.getAllByRole('button');
    buttons.forEach((btn) => {
      expect(btn.className).toContain('flex-1');
      expect(btn.className).toContain('min-h-[104px]');
    });
  });
});
