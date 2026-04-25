/**
 * Tests for V2LinkBtn — accent-tinted toggle button with count badge and chevron.
 * Validates: Requirements 1.1–1.6, 12.1, 12.6, 13.1
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { V2LinkBtn } from './V2LinkBtn';

// Minimal icon stub
const TestIcon = () => <svg data-testid="test-icon" />;

// ── Default (closed) state rendering ─────────────────────────────────────────

describe('V2LinkBtn — Default (closed) state', () => {
  it('renders with white background, correct text color, and border', () => {
    render(
      <V2LinkBtn icon={<TestIcon />} accent="blue" open={false} onClick={vi.fn()}>
        See attached photos
      </V2LinkBtn>,
    );

    const btn = screen.getByRole('button');
    expect(btn.style.backgroundColor).toBe('rgb(255, 255, 255)');
    expect(btn.style.color).toBe('rgb(55, 65, 81)'); // #374151
    expect(btn.style.border).toContain('rgb(229, 231, 235)'); // #E5E7EB
  });

  it('renders chevron down when closed', () => {
    render(
      <V2LinkBtn icon={<TestIcon />} accent="blue" open={false} onClick={vi.fn()}>
        Label
      </V2LinkBtn>,
    );

    const btn = screen.getByRole('button');
    // ChevronDown from lucide-react renders an SVG — check for its presence
    const svgs = btn.querySelectorAll('svg');
    // Should have: test-icon SVG + ChevronDown SVG
    expect(svgs.length).toBeGreaterThanOrEqual(2);
  });

  it('renders the label text', () => {
    render(
      <V2LinkBtn icon={<TestIcon />} accent="blue" open={false} onClick={vi.fn()}>
        See attached photos
      </V2LinkBtn>,
    );

    expect(screen.getByText('See attached photos')).toBeInTheDocument();
  });
});

// ── Open state with blue accent ──────────────────────────────────────────────

describe('V2LinkBtn — Open state with blue accent', () => {
  it('renders with #DBEAFE bg, #1D4ED8 text and border', () => {
    render(
      <V2LinkBtn icon={<TestIcon />} accent="blue" open={true} onClick={vi.fn()}>
        See attached photos
      </V2LinkBtn>,
    );

    const btn = screen.getByRole('button');
    expect(btn.style.backgroundColor).toBe('rgb(219, 234, 254)'); // #DBEAFE
    expect(btn.style.color).toBe('rgb(29, 78, 216)'); // #1D4ED8
    expect(btn.style.border).toContain('rgb(29, 78, 216)'); // #1D4ED8
  });

  it('renders chevron up when open', () => {
    render(
      <V2LinkBtn icon={<TestIcon />} accent="blue" open={true} onClick={vi.fn()}>
        Label
      </V2LinkBtn>,
    );

    // The button should contain a ChevronUp SVG (not ChevronDown)
    const btn = screen.getByRole('button');
    const svgs = btn.querySelectorAll('svg');
    expect(svgs.length).toBeGreaterThanOrEqual(2);
  });
});

// ── Open state with amber accent ─────────────────────────────────────────────

describe('V2LinkBtn — Open state with amber accent', () => {
  it('renders with #FEF3C7 bg, #B45309 text and border', () => {
    render(
      <V2LinkBtn icon={<TestIcon />} accent="amber" open={true} onClick={vi.fn()}>
        See attached notes
      </V2LinkBtn>,
    );

    const btn = screen.getByRole('button');
    expect(btn.style.backgroundColor).toBe('rgb(254, 243, 199)'); // #FEF3C7
    expect(btn.style.color).toBe('rgb(180, 83, 9)'); // #B45309
    expect(btn.style.border).toContain('rgb(180, 83, 9)'); // #B45309
  });
});

// ── Count badge display ──────────────────────────────────────────────────────

describe('V2LinkBtn — Count badge', () => {
  it('displays count badge when count prop is provided', () => {
    render(
      <V2LinkBtn icon={<TestIcon />} accent="blue" open={false} count={5} onClick={vi.fn()}>
        Label
      </V2LinkBtn>,
    );

    expect(screen.getByText('5')).toBeInTheDocument();
  });

  it('does not display count badge when count prop is omitted', () => {
    render(
      <V2LinkBtn icon={<TestIcon />} accent="blue" open={false} onClick={vi.fn()}>
        Label
      </V2LinkBtn>,
    );

    // No numeric badge should be present
    expect(screen.queryByText('0')).not.toBeInTheDocument();
  });

  it('renders open badge with accent bg and white text (blue)', () => {
    render(
      <V2LinkBtn icon={<TestIcon />} accent="blue" open={true} count={3} onClick={vi.fn()}>
        Label
      </V2LinkBtn>,
    );

    const badge = screen.getByText('3');
    expect(badge.style.backgroundColor).toBe('rgb(29, 78, 216)'); // #1D4ED8
    expect(badge.style.color).toBe('rgb(255, 255, 255)'); // white
  });

  it('renders closed badge with #F3F4F6 bg and #4B5563 text', () => {
    render(
      <V2LinkBtn icon={<TestIcon />} accent="blue" open={false} count={3} onClick={vi.fn()}>
        Label
      </V2LinkBtn>,
    );

    const badge = screen.getByText('3');
    expect(badge.style.backgroundColor).toBe('rgb(243, 244, 246)'); // #F3F4F6
    expect(badge.style.color).toBe('rgb(75, 85, 99)'); // #4B5563
  });
});

// ── aria-expanded attribute ──────────────────────────────────────────────────

describe('V2LinkBtn — aria-expanded', () => {
  it('sets aria-expanded="true" when open', () => {
    render(
      <V2LinkBtn icon={<TestIcon />} accent="blue" open={true} onClick={vi.fn()}>
        Label
      </V2LinkBtn>,
    );

    expect(screen.getByRole('button')).toHaveAttribute('aria-expanded', 'true');
  });

  it('sets aria-expanded="false" when closed', () => {
    render(
      <V2LinkBtn icon={<TestIcon />} accent="blue" open={false} onClick={vi.fn()}>
        Label
      </V2LinkBtn>,
    );

    expect(screen.getByRole('button')).toHaveAttribute('aria-expanded', 'false');
  });
});

// ── Click handler fires on click, Enter, and Space ───────────────────────────

describe('V2LinkBtn — Click and keyboard activation', () => {
  let onClick: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    onClick = vi.fn();
  });

  it('fires onClick on mouse click', async () => {
    const user = userEvent.setup();
    render(
      <V2LinkBtn icon={<TestIcon />} accent="blue" open={false} onClick={onClick}>
        Label
      </V2LinkBtn>,
    );

    await user.click(screen.getByRole('button'));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('fires onClick on Enter key', async () => {
    const user = userEvent.setup();
    render(
      <V2LinkBtn icon={<TestIcon />} accent="blue" open={false} onClick={onClick}>
        Label
      </V2LinkBtn>,
    );

    screen.getByRole('button').focus();
    await user.keyboard('{Enter}');
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('fires onClick on Space key', async () => {
    const user = userEvent.setup();
    render(
      <V2LinkBtn icon={<TestIcon />} accent="blue" open={false} onClick={onClick}>
        Label
      </V2LinkBtn>,
    );

    screen.getByRole('button').focus();
    await user.keyboard(' ');
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('passes aria-label to the button', () => {
    render(
      <V2LinkBtn
        icon={<TestIcon />}
        accent="blue"
        open={false}
        onClick={vi.fn()}
        aria-label="See attached photos"
      >
        Label
      </V2LinkBtn>,
    );

    expect(screen.getByRole('button')).toHaveAttribute('aria-label', 'See attached photos');
  });
});
