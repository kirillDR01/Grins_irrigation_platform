/**
 * Tests for SecondaryActionsStrip — V2 upgrade with V2LinkBtn buttons.
 * Validates: Requirements 2.1–2.7, 13.4
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { toast } from 'sonner';
import { SecondaryActionsStrip } from './SecondaryActionsStrip';

vi.mock('sonner', () => ({
  toast: {
    info: vi.fn(),
  },
}));

// ── Default props ────────────────────────────────────────────────────────────

function defaultProps(overrides?: Partial<Parameters<typeof SecondaryActionsStrip>[0]>) {
  return {
    tagsOpen: false,
    onEditTags: vi.fn(),
    onReview: vi.fn(),
    photosOpen: false,
    notesOpen: false,
    photoCount: 5,
    noteCount: 1,
    onTogglePhotos: vi.fn(),
    onToggleNotes: vi.fn(),
    ...overrides,
  };
}

// ── Four buttons present ─────────────────────────────────────────────────────

describe('SecondaryActionsStrip — Button presence', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders "See attached photos" button', () => {
    render(<SecondaryActionsStrip {...defaultProps()} />);
    expect(screen.getByLabelText('See attached photos')).toBeInTheDocument();
  });

  it('renders "See attached notes" button', () => {
    render(<SecondaryActionsStrip {...defaultProps()} />);
    expect(screen.getByLabelText('See attached notes')).toBeInTheDocument();
  });

  it('renders "Send Review Request" button (not "Review")', () => {
    render(<SecondaryActionsStrip {...defaultProps()} />);
    expect(screen.getByLabelText('Send Review Request')).toBeInTheDocument();
    expect(screen.getByText('Send Review Request')).toBeInTheDocument();
    // Should NOT have just "Review" as standalone text
    expect(screen.queryByText(/^Review$/)).not.toBeInTheDocument();
  });

  it('renders "Edit tags" button', () => {
    render(<SecondaryActionsStrip {...defaultProps()} />);
    expect(screen.getByLabelText('Edit tags')).toBeInTheDocument();
  });

  it('renders exactly 4 buttons', () => {
    render(<SecondaryActionsStrip {...defaultProps()} />);
    const buttons = screen.getAllByRole('button');
    expect(buttons).toHaveLength(4);
  });
});

// ── V2LinkBtn count badges ───────────────────────────────────────────────────

describe('SecondaryActionsStrip — Count badges', () => {
  beforeEach(() => vi.clearAllMocks());

  it('shows correct photo count badge', () => {
    render(<SecondaryActionsStrip {...defaultProps({ photoCount: 12 })} />);
    expect(screen.getByText('12')).toBeInTheDocument();
  });

  it('shows correct note count badge (1 when notes exist)', () => {
    render(<SecondaryActionsStrip {...defaultProps({ noteCount: 1 })} />);
    expect(screen.getByText('1')).toBeInTheDocument();
  });

  it('shows note count badge of 0 when no notes', () => {
    render(<SecondaryActionsStrip {...defaultProps({ noteCount: 0 })} />);
    expect(screen.getByText('0')).toBeInTheDocument();
  });
});

// ── Panel toggle callbacks ───────────────────────────────────────────────────

describe('SecondaryActionsStrip — Panel toggle callbacks', () => {
  beforeEach(() => vi.clearAllMocks());

  it('fires onTogglePhotos when photos button is clicked', async () => {
    const user = userEvent.setup();
    const props = defaultProps();
    render(<SecondaryActionsStrip {...props} />);

    await user.click(screen.getByLabelText('See attached photos'));
    expect(props.onTogglePhotos).toHaveBeenCalledTimes(1);
  });

  it('fires onToggleNotes when notes button is clicked', async () => {
    const user = userEvent.setup();
    const props = defaultProps();
    render(<SecondaryActionsStrip {...props} />);

    await user.click(screen.getByLabelText('See attached notes'));
    expect(props.onToggleNotes).toHaveBeenCalledTimes(1);
  });

  it('fires onReview when "Send Review Request" is clicked', async () => {
    const user = userEvent.setup();
    const props = defaultProps();
    render(<SecondaryActionsStrip {...props} />);

    await user.click(screen.getByLabelText('Send Review Request'));
    expect(props.onReview).toHaveBeenCalledTimes(1);
  });

  it('fires onEditTags when "Edit tags" is clicked', async () => {
    const user = userEvent.setup();
    const props = defaultProps();
    render(<SecondaryActionsStrip {...props} />);

    await user.click(screen.getByLabelText('Edit tags'));
    expect(props.onEditTags).toHaveBeenCalledTimes(1);
  });
});

// ── Review-enabled gating ────────────────────────────────────────────────────

describe('SecondaryActionsStrip — Review gating', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders Send Review Request enabled by default', () => {
    render(<SecondaryActionsStrip {...defaultProps()} />);
    expect(screen.getByLabelText('Send Review Request')).not.toBeDisabled();
  });

  it('exposes the reason via title + aria-label when reviewEnabled=false', () => {
    render(
      <SecondaryActionsStrip
        {...defaultProps({
          reviewEnabled: false,
          reviewDisabledReason: 'Available after appointment is marked completed',
        })}
      />
    );
    const btn = screen.getByLabelText(
      /Send Review Request — Available after appointment is marked completed/
    );
    expect(btn).toHaveAttribute(
      'title',
      'Available after appointment is marked completed'
    );
  });

  it('does not call onReview when ineligible and clicked', async () => {
    const user = userEvent.setup();
    const props = defaultProps({
      reviewEnabled: false,
      reviewDisabledReason: 'Customer has no phone number',
    });
    render(<SecondaryActionsStrip {...props} />);

    const btn = screen.getByLabelText(
      /Send Review Request — Customer has no phone number/
    );
    await user.click(btn);
    expect(props.onReview).not.toHaveBeenCalled();
  });
});

// ── Review button gating UX (inactive mode + toast) ──────────────────────────

describe('SecondaryActionsStrip — Review button gating UX', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders aria-disabled (not HTML disabled) when reviewEnabled=false', () => {
    render(
      <SecondaryActionsStrip
        {...defaultProps({
          onReview: vi.fn(),
          // @ts-expect-error — extending the runtime props with new flag the
          // production component now accepts. If/when the component types are
          // updated, remove this directive.
          reviewEnabled: false,
          reviewDisabledReason: 'Available after appointment is marked completed',
        })}
      />,
    );
    const btn = screen.getByLabelText(
      'Send Review Request — Available after appointment is marked completed',
    );
    expect(btn).toHaveAttribute('aria-disabled', 'true');
    expect(btn).not.toBeDisabled();
  });

  it('toasts the reviewDisabledReason and does NOT call onReview when ineligible', async () => {
    const user = userEvent.setup();
    const onReview = vi.fn();
    render(
      <SecondaryActionsStrip
        {...defaultProps({
          onReview,
          // @ts-expect-error — see above
          reviewEnabled: false,
          reviewDisabledReason: 'Customer phone not on file',
        })}
      />,
    );
    await user.click(
      screen.getByLabelText('Send Review Request — Customer phone not on file'),
    );
    expect(toast.info).toHaveBeenCalledWith(
      'Send Review Request unavailable',
      expect.objectContaining({ description: 'Customer phone not on file' }),
    );
    expect(onReview).not.toHaveBeenCalled();
  });

  it('calls onReview and does NOT toast when reviewEnabled=true', async () => {
    const user = userEvent.setup();
    const onReview = vi.fn();
    render(
      <SecondaryActionsStrip
        {...defaultProps({ onReview, reviewEnabled: true })}
      />,
    );
    await user.click(screen.getByLabelText('Send Review Request'));
    expect(onReview).toHaveBeenCalledTimes(1);
    expect(toast.info).not.toHaveBeenCalled();
  });
});
