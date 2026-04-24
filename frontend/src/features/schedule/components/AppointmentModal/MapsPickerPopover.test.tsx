/**
 * Tests for MapsPickerPopover — URL generation for both map apps,
 * ARIA roles, keyboard navigation, outside click, rendering.
 * Validates: Requirements 8.4, 8.5, 8.6, 8.7, 18.3
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MapsPickerPopover } from './MapsPickerPopover';

// ── Helpers ──────────────────────────────────────────────────────────────────

const DEFAULT_PROPS = {
  address: '123 Main St, Springfield, IL 62701',
  onClose: vi.fn(),
};

function renderPopover(overrides: Partial<Parameters<typeof MapsPickerPopover>[0]> = {}) {
  return render(<MapsPickerPopover {...DEFAULT_PROPS} {...overrides} />);
}

// ── Rendering (Req 8.4) ─────────────────────────────────────────────────────

describe('MapsPickerPopover — Rendering (Req 8.4)', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders the "OPEN IN" header text', () => {
    renderPopover();
    expect(screen.getByText(/open in/i)).toBeInTheDocument();
  });

  it('renders Apple Maps row', () => {
    renderPopover();
    expect(screen.getByText('Apple Maps')).toBeInTheDocument();
  });

  it('renders Google Maps row', () => {
    renderPopover();
    expect(screen.getByText('Google Maps')).toBeInTheDocument();
  });

  it('renders exactly two menuitem links', () => {
    renderPopover();
    const items = screen.getAllByRole('menuitem');
    expect(items).toHaveLength(2);
  });
});

// ── ARIA roles (Req 18.3) ───────────────────────────────────────────────────

describe('MapsPickerPopover — ARIA roles (Req 18.3)', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders the popover container with role="menu"', () => {
    renderPopover();
    const menu = screen.getByRole('menu');
    expect(menu).toBeInTheDocument();
  });

  it('renders the popover with aria-label="Open in maps"', () => {
    renderPopover();
    const menu = screen.getByRole('menu');
    expect(menu).toHaveAttribute('aria-label', 'Open in maps');
  });

  it('renders Apple Maps link with role="menuitem"', () => {
    renderPopover();
    const items = screen.getAllByRole('menuitem');
    const appleItem = items.find((el) => el.textContent?.includes('Apple Maps'));
    expect(appleItem).toBeTruthy();
    expect(appleItem?.tagName).toBe('A');
  });

  it('renders Google Maps link with role="menuitem"', () => {
    renderPopover();
    const items = screen.getAllByRole('menuitem');
    const googleItem = items.find((el) => el.textContent?.includes('Google Maps'));
    expect(googleItem).toBeTruthy();
    expect(googleItem?.tagName).toBe('A');
  });
});

// ── Apple Maps URL generation (Req 8.6) ─────────────────────────────────────

describe('MapsPickerPopover — Apple Maps URL (Req 8.6)', () => {
  beforeEach(() => vi.clearAllMocks());

  it('generates Apple Maps URL with maps:// protocol and encoded address', () => {
    renderPopover({ address: '123 Main St, Springfield, IL 62701' });

    const items = screen.getAllByRole('menuitem');
    const appleLink = items.find((el) => el.textContent?.includes('Apple Maps')) as HTMLAnchorElement;

    expect(appleLink.href).toContain('maps://');
    expect(appleLink.href).toContain('daddr=');
    expect(appleLink.href).toContain(encodeURIComponent('123 Main St, Springfield, IL 62701'));
  });

  it('properly encodes special characters in the address', () => {
    renderPopover({ address: '100 O\'Brien Ave #5, San José, CA' });

    const items = screen.getAllByRole('menuitem');
    const appleLink = items.find((el) => el.textContent?.includes('Apple Maps')) as HTMLAnchorElement;

    const encoded = encodeURIComponent('100 O\'Brien Ave #5, San José, CA');
    expect(appleLink.href).toContain(encoded);
  });
});

// ── Google Maps URL generation (Req 8.7) ────────────────────────────────────

describe('MapsPickerPopover — Google Maps URL (Req 8.7)', () => {
  beforeEach(() => vi.clearAllMocks());

  it('generates Google Maps URL with encoded address when no lat/lng', () => {
    renderPopover({
      address: '123 Main St, Springfield, IL 62701',
      latitude: undefined,
      longitude: undefined,
    });

    const items = screen.getAllByRole('menuitem');
    const googleLink = items.find((el) => el.textContent?.includes('Google Maps')) as HTMLAnchorElement;

    expect(googleLink.href).toBe(
      `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent('123 Main St, Springfield, IL 62701')}`,
    );
  });

  it('prefers lat/lng coordinates when available', () => {
    renderPopover({
      address: '123 Main St, Springfield, IL 62701',
      latitude: 39.7817,
      longitude: -89.6501,
    });

    const items = screen.getAllByRole('menuitem');
    const googleLink = items.find((el) => el.textContent?.includes('Google Maps')) as HTMLAnchorElement;

    expect(googleLink.href).toBe(
      'https://www.google.com/maps/dir/?api=1&destination=39.7817,-89.6501',
    );
  });

  it('falls back to encoded address when latitude is null', () => {
    renderPopover({
      address: '456 Oak Ave',
      latitude: null,
      longitude: -89.6501,
    });

    const items = screen.getAllByRole('menuitem');
    const googleLink = items.find((el) => el.textContent?.includes('Google Maps')) as HTMLAnchorElement;

    expect(googleLink.href).toContain(`destination=${encodeURIComponent('456 Oak Ave')}`);
    expect(googleLink.href).not.toContain('-89.6501');
  });

  it('falls back to encoded address when longitude is null', () => {
    renderPopover({
      address: '456 Oak Ave',
      latitude: 39.7817,
      longitude: null,
    });

    const items = screen.getAllByRole('menuitem');
    const googleLink = items.find((el) => el.textContent?.includes('Google Maps')) as HTMLAnchorElement;

    expect(googleLink.href).toContain(`destination=${encodeURIComponent('456 Oak Ave')}`);
    expect(googleLink.href).not.toContain('39.7817');
  });

  it('opens Google Maps link in a new tab', () => {
    renderPopover();

    const items = screen.getAllByRole('menuitem');
    const googleLink = items.find((el) => el.textContent?.includes('Google Maps')) as HTMLAnchorElement;

    expect(googleLink).toHaveAttribute('target', '_blank');
    expect(googleLink).toHaveAttribute('rel', 'noopener noreferrer');
  });
});

// ── Keyboard navigation (Req 18.3) ──────────────────────────────────────────

describe('MapsPickerPopover — Keyboard navigation (Req 18.3)', () => {
  beforeEach(() => vi.clearAllMocks());

  it('calls onClose when Escape is pressed', () => {
    const onClose = vi.fn();
    renderPopover({ onClose });

    fireEvent.keyDown(document, { key: 'Escape' });

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('focuses the first menuitem on mount', () => {
    renderPopover();

    const items = screen.getAllByRole('menuitem');
    const firstItem = items[0];

    expect(document.activeElement).toBe(firstItem);
  });
});

// ── Outside click closes popover (Req 18.3) ─────────────────────────────────

describe('MapsPickerPopover — Outside click (Req 18.3)', () => {
  beforeEach(() => vi.clearAllMocks());

  it('calls onClose when clicking outside the popover', () => {
    const onClose = vi.fn();
    renderPopover({ onClose });

    // Click outside the popover (on the document body)
    fireEvent.mouseDown(document.body);

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('does not call onClose when clicking inside the popover', () => {
    const onClose = vi.fn();
    renderPopover({ onClose });

    const menu = screen.getByRole('menu');
    fireEvent.mouseDown(menu);

    // onClose should NOT be called for inside clicks
    expect(onClose).not.toHaveBeenCalled();
  });
});

// ── onClick calls onClose (Req 8.5) ─────────────────────────────────────────

describe('MapsPickerPopover — Row click calls onClose (Req 8.5)', () => {
  beforeEach(() => vi.clearAllMocks());

  it('calls onClose when Apple Maps row is clicked', async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();
    renderPopover({ onClose });

    const items = screen.getAllByRole('menuitem');
    const appleItem = items.find((el) => el.textContent?.includes('Apple Maps'))!;

    await user.click(appleItem);

    expect(onClose).toHaveBeenCalled();
  });

  it('calls onClose when Google Maps row is clicked', async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();
    renderPopover({ onClose });

    const items = screen.getAllByRole('menuitem');
    const googleItem = items.find((el) => el.textContent?.includes('Google Maps'))!;

    await user.click(googleItem);

    expect(onClose).toHaveBeenCalled();
  });
});
