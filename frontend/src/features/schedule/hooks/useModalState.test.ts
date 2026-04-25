/**
 * Tests for useModalState hook — V2 extensions.
 * Validates: Requirements 7.1–7.6, 13.5
 */

import { describe, it, expect } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useModalState, deriveStep } from './useModalState';

// ── Initial state ────────────────────────────────────────────────────────────

describe('useModalState — Initial state', () => {
  it('starts with openPanel: null', () => {
    const { result } = renderHook(() => useModalState());
    expect(result.current.openPanel).toBeNull();
  });

  it('starts with editingNotes: false', () => {
    const { result } = renderHook(() => useModalState());
    expect(result.current.editingNotes).toBe(false);
  });

  it('starts with openSheet: null', () => {
    const { result } = renderHook(() => useModalState());
    expect(result.current.openSheet).toBeNull();
  });
});

// ── togglePanel ──────────────────────────────────────────────────────────────

describe('useModalState — togglePanel', () => {
  it('opens photos panel on first call', () => {
    const { result } = renderHook(() => useModalState());

    act(() => result.current.togglePanel('photos'));
    expect(result.current.openPanel).toBe('photos');
  });

  it('closes photos panel on second call (toggle off)', () => {
    const { result } = renderHook(() => useModalState());

    act(() => result.current.togglePanel('photos'));
    expect(result.current.openPanel).toBe('photos');

    act(() => result.current.togglePanel('photos'));
    expect(result.current.openPanel).toBeNull();
  });

  it('opens notes panel', () => {
    const { result } = renderHook(() => useModalState());

    act(() => result.current.togglePanel('notes'));
    expect(result.current.openPanel).toBe('notes');
  });

  it('closes notes panel on second call', () => {
    const { result } = renderHook(() => useModalState());

    act(() => result.current.togglePanel('notes'));
    act(() => result.current.togglePanel('notes'));
    expect(result.current.openPanel).toBeNull();
  });

  it('switches from photos to notes (closes photos, opens notes)', () => {
    const { result } = renderHook(() => useModalState());

    act(() => result.current.togglePanel('photos'));
    expect(result.current.openPanel).toBe('photos');

    act(() => result.current.togglePanel('notes'));
    expect(result.current.openPanel).toBe('notes');
  });

  it('switches from notes to photos', () => {
    const { result } = renderHook(() => useModalState());

    act(() => result.current.togglePanel('notes'));
    act(() => result.current.togglePanel('photos'));
    expect(result.current.openPanel).toBe('photos');
  });
});

// ── Panel mutual exclusivity ─────────────────────────────────────────────────

describe('useModalState — Panel mutual exclusivity', () => {
  it('only one panel open at a time', () => {
    const { result } = renderHook(() => useModalState());

    act(() => result.current.togglePanel('photos'));
    expect(result.current.openPanel).toBe('photos');

    act(() => result.current.togglePanel('notes'));
    expect(result.current.openPanel).toBe('notes');
    // photos is implicitly closed since openPanel can only be one value
  });
});

// ── editingNotes auto-reset ──────────────────────────────────────────────────

describe('useModalState — editingNotes auto-reset', () => {
  it('resets editingNotes to false when openPanel changes away from notes', () => {
    const { result } = renderHook(() => useModalState());

    // Open notes and start editing
    act(() => result.current.togglePanel('notes'));
    act(() => result.current.setEditingNotes(true));
    expect(result.current.editingNotes).toBe(true);

    // Switch to photos — editingNotes should auto-reset
    act(() => result.current.togglePanel('photos'));
    expect(result.current.editingNotes).toBe(false);
  });

  it('resets editingNotes when notes panel is closed', () => {
    const { result } = renderHook(() => useModalState());

    act(() => result.current.togglePanel('notes'));
    act(() => result.current.setEditingNotes(true));
    expect(result.current.editingNotes).toBe(true);

    // Toggle notes off
    act(() => result.current.togglePanel('notes'));
    expect(result.current.editingNotes).toBe(false);
  });

  it('does not reset editingNotes when staying on notes panel', () => {
    const { result } = renderHook(() => useModalState());

    act(() => result.current.togglePanel('notes'));
    act(() => result.current.setEditingNotes(true));
    expect(result.current.editingNotes).toBe(true);
    expect(result.current.openPanel).toBe('notes');
  });
});

// ── Sheet-panel mutual exclusivity ───────────────────────────────────────────

describe('useModalState — Sheet-panel mutual exclusivity', () => {
  it('opening a sheet closes any open panel', () => {
    const { result } = renderHook(() => useModalState());

    act(() => result.current.togglePanel('photos'));
    expect(result.current.openPanel).toBe('photos');

    act(() => result.current.openSheetExclusive('tags'));
    expect(result.current.openSheet).toBe('tags');
    expect(result.current.openPanel).toBeNull();
  });

  it('opening a panel closes any open sheet', () => {
    const { result } = renderHook(() => useModalState());

    act(() => result.current.openSheetExclusive('payment'));
    expect(result.current.openSheet).toBe('payment');

    act(() => result.current.togglePanel('notes'));
    expect(result.current.openPanel).toBe('notes');
    expect(result.current.openSheet).toBeNull();
  });

  it('openSheet and openPanel are never both non-null', () => {
    const { result } = renderHook(() => useModalState());

    // Open panel
    act(() => result.current.togglePanel('photos'));
    expect(result.current.openSheet).toBeNull();

    // Open sheet — panel should close
    act(() => result.current.openSheetExclusive('estimate'));
    expect(result.current.openPanel).toBeNull();

    // Open panel again — sheet should close
    act(() => result.current.togglePanel('notes'));
    expect(result.current.openSheet).toBeNull();
  });
});

// ── setEditingNotes ──────────────────────────────────────────────────────────

describe('useModalState — setEditingNotes', () => {
  it('sets editingNotes to true', () => {
    const { result } = renderHook(() => useModalState());

    act(() => result.current.setEditingNotes(true));
    expect(result.current.editingNotes).toBe(true);
  });

  it('sets editingNotes to false', () => {
    const { result } = renderHook(() => useModalState());

    act(() => result.current.setEditingNotes(true));
    act(() => result.current.setEditingNotes(false));
    expect(result.current.editingNotes).toBe(false);
  });
});

// ── deriveStep utility ───────────────────────────────────────────────────────

describe('deriveStep', () => {
  it('returns 0 for scheduled', () => {
    expect(deriveStep('scheduled')).toBe(0);
  });

  it('returns 0 for confirmed', () => {
    expect(deriveStep('confirmed')).toBe(0);
  });

  it('returns 1 for en_route', () => {
    expect(deriveStep('en_route')).toBe(1);
  });

  it('returns 2 for in_progress', () => {
    expect(deriveStep('in_progress')).toBe(2);
  });

  it('returns 3 for completed', () => {
    expect(deriveStep('completed')).toBe(3);
  });

  it('returns null for unknown status', () => {
    expect(deriveStep('cancelled' as any)).toBeNull();
  });
});
