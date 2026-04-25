/**
 * Property-based tests for useModalState hook — V2 extensions.
 * Uses fast-check for Properties 4, 5, 6.
 * Feature: appointment-modal-v2
 *
 * Validates: Requirements 2.4, 2.5, 3.5, 3.6, 7.3, 7.4, 7.5, 15.4, 15.5
 */

import { describe, it, expect } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import * as fc from 'fast-check';
import { useModalState, type ModalSheet } from './useModalState';

// ===================================================================
// Property 4: Panel mutual exclusivity
// Feature: appointment-modal-v2, Property 4: Panel mutual exclusivity
// Validates: Requirements 2.4, 2.5, 3.5, 15.4
// ===================================================================

describe('Property 4: Panel mutual exclusivity', () => {
  /**
   * For any sequence of togglePanel calls with arguments drawn from
   * {'photos', 'notes'}, at most one panel SHALL be open at any time.
   * Toggle-same-twice returns to null.
   *
   * **Validates: Requirements 2.4, 2.5, 3.5, 15.4**
   */
  it('property: at most one panel is open after any sequence of togglePanel calls', () => {
    fc.assert(
      fc.property(
        fc.array(
          fc.oneof(fc.constant('photos' as const), fc.constant('notes' as const)),
          { minLength: 1, maxLength: 50 },
        ),
        (sequence) => {
          const { result } = renderHook(() => useModalState());

          for (const panel of sequence) {
            act(() => result.current.togglePanel(panel));

            // After each call, openPanel is either null or exactly one panel
            const openPanel = result.current.openPanel;
            expect(openPanel === null || openPanel === 'photos' || openPanel === 'notes').toBe(true);
          }
        },
      ),
      { numRuns: 100 },
    );
  });

  it('property: toggle-same-twice returns to null', () => {
    fc.assert(
      fc.property(
        fc.oneof(fc.constant('photos' as const), fc.constant('notes' as const)),
        (panel) => {
          const { result } = renderHook(() => useModalState());

          // First toggle opens the panel
          act(() => result.current.togglePanel(panel));
          expect(result.current.openPanel).toBe(panel);

          // Second toggle closes it
          act(() => result.current.togglePanel(panel));
          expect(result.current.openPanel).toBeNull();
        },
      ),
      { numRuns: 100 },
    );
  });

  it('property: toggling a different panel switches to it', () => {
    fc.assert(
      fc.property(
        fc.oneof(fc.constant('photos' as const), fc.constant('notes' as const)),
        (firstPanel) => {
          const otherPanel = firstPanel === 'photos' ? 'notes' : 'photos';
          const { result } = renderHook(() => useModalState());

          act(() => result.current.togglePanel(firstPanel));
          expect(result.current.openPanel).toBe(firstPanel);

          act(() => result.current.togglePanel(otherPanel));
          expect(result.current.openPanel).toBe(otherPanel);
        },
      ),
      { numRuns: 100 },
    );
  });
});

// ===================================================================
// Property 5: editingNotes auto-reset invariant
// Feature: appointment-modal-v2, Property 5: editingNotes auto-reset invariant
// Validates: Requirements 3.6, 7.3, 15.5
// ===================================================================

describe('Property 5: editingNotes auto-reset invariant', () => {
  /**
   * For any sequence of togglePanel, openSheetExclusive, and
   * setEditingNotes(true) calls, whenever openPanel changes away from
   * 'notes' (via togglePanel or openSheetExclusive), editingNotes SHALL
   * be false. The invariant is checked after panel/sheet transitions,
   * not after raw setEditingNotes calls (which are only valid when
   * openPanel === 'notes').
   *
   * **Validates: Requirements 3.6, 7.3, 15.5**
   */
  it('property: editingNotes resets to false after any transition away from notes panel', () => {
    const actionArb = fc.oneof(
      fc.constant({ type: 'togglePhotos' as const }),
      fc.constant({ type: 'toggleNotes' as const }),
      fc.constantFrom(
        { type: 'openSheet' as const, sheet: 'payment' as ModalSheet },
        { type: 'openSheet' as const, sheet: 'estimate' as ModalSheet },
        { type: 'openSheet' as const, sheet: 'tags' as ModalSheet },
      ),
      fc.constant({ type: 'setEditingTrue' as const }),
    );

    fc.assert(
      fc.property(
        fc.array(actionArb, { minLength: 1, maxLength: 50 }),
        (actions) => {
          const { result } = renderHook(() => useModalState());

          for (const action of actions) {
            act(() => {
              switch (action.type) {
                case 'togglePhotos':
                  result.current.togglePanel('photos');
                  break;
                case 'toggleNotes':
                  result.current.togglePanel('notes');
                  break;
                case 'openSheet':
                  result.current.openSheetExclusive(action.sheet);
                  break;
                case 'setEditingTrue':
                  // Only set editing when notes panel is open (matches real usage)
                  if (result.current.openPanel === 'notes') {
                    result.current.setEditingNotes(true);
                  }
                  break;
              }
            });

            // After any panel/sheet transition, if openPanel is not 'notes',
            // editingNotes must be false
            if (result.current.openPanel !== 'notes') {
              expect(result.current.editingNotes).toBe(false);
            }
          }
        },
      ),
      { numRuns: 100 },
    );
  });

  it('property: setEditingNotes(true) then leaving notes panel always resets editing', () => {
    const leaveAction = fc.oneof(
      fc.constant({ type: 'togglePhotos' as const }),
      fc.constant({ type: 'toggleNotes' as const }),
      fc.constantFrom(
        { type: 'openSheet' as const, sheet: 'payment' as ModalSheet },
        { type: 'openSheet' as const, sheet: 'estimate' as ModalSheet },
        { type: 'openSheet' as const, sheet: 'tags' as ModalSheet },
      ),
    );

    fc.assert(
      fc.property(leaveAction, (action) => {
        const { result } = renderHook(() => useModalState());

        // Open notes panel and start editing
        act(() => result.current.togglePanel('notes'));
        act(() => result.current.setEditingNotes(true));
        expect(result.current.editingNotes).toBe(true);
        expect(result.current.openPanel).toBe('notes');

        // Leave notes panel via any transition
        act(() => {
          switch (action.type) {
            case 'togglePhotos':
              result.current.togglePanel('photos');
              break;
            case 'toggleNotes':
              result.current.togglePanel('notes');
              break;
            case 'openSheet':
              result.current.openSheetExclusive(action.sheet);
              break;
          }
        });

        // After leaving notes, editingNotes must be false
        expect(result.current.openPanel).not.toBe('notes');
        expect(result.current.editingNotes).toBe(false);
      }),
      { numRuns: 100 },
    );
  });
});

// ===================================================================
// Property 6: Sheet-panel mutual exclusivity
// Feature: appointment-modal-v2, Property 6: Sheet-panel mutual exclusivity
// Validates: Requirements 7.4, 7.5
// ===================================================================

describe('Property 6: Sheet-panel mutual exclusivity', () => {
  /**
   * For any sequence of openSheetExclusive and togglePanel calls,
   * openSheet and openPanel SHALL never both be non-null simultaneously.
   *
   * **Validates: Requirements 7.4, 7.5**
   */
  it('property: openSheet and openPanel are never both non-null', () => {
    const actionArb = fc.oneof(
      fc.constantFrom(
        { type: 'openSheet' as const, sheet: 'payment' as ModalSheet },
        { type: 'openSheet' as const, sheet: 'estimate' as ModalSheet },
        { type: 'openSheet' as const, sheet: 'tags' as ModalSheet },
      ),
      fc.constant({ type: 'togglePhotos' as const }),
      fc.constant({ type: 'toggleNotes' as const }),
    );

    fc.assert(
      fc.property(
        fc.array(actionArb, { minLength: 1, maxLength: 50 }),
        (actions) => {
          const { result } = renderHook(() => useModalState());

          for (const action of actions) {
            act(() => {
              switch (action.type) {
                case 'openSheet':
                  result.current.openSheetExclusive(action.sheet);
                  break;
                case 'togglePhotos':
                  result.current.togglePanel('photos');
                  break;
                case 'toggleNotes':
                  result.current.togglePanel('notes');
                  break;
              }
            });

            // Invariant: openSheet and openPanel are never both non-null
            const bothNonNull =
              result.current.openSheet !== null && result.current.openPanel !== null;
            expect(bothNonNull).toBe(false);
          }
        },
      ),
      { numRuns: 100 },
    );
  });
});
