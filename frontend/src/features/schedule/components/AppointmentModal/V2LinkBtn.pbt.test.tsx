/**
 * Property-based tests for V2LinkBtn accent map correctness.
 * Uses fast-check for Property 7.
 * Feature: appointment-modal-v2
 *
 * Validates: Requirements 1.3, 1.5, 11.1
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import * as fc from 'fast-check';
import { V2LinkBtn } from './V2LinkBtn';

// Minimal icon stub
const TestIcon = () => <svg data-testid="test-icon" />;

// Expected color values (matching the ACCENT_MAP and CLOSED constants in V2LinkBtn)
const EXPECTED = {
  blue: {
    open: { bg: 'rgb(219, 234, 254)', color: 'rgb(29, 78, 216)', border: 'rgb(29, 78, 216)' },
    closed: { bg: 'rgb(255, 255, 255)', color: 'rgb(55, 65, 81)', border: 'rgb(229, 231, 235)' },
  },
  amber: {
    open: { bg: 'rgb(254, 243, 199)', color: 'rgb(180, 83, 9)', border: 'rgb(180, 83, 9)' },
    closed: { bg: 'rgb(255, 255, 255)', color: 'rgb(55, 65, 81)', border: 'rgb(229, 231, 235)' },
  },
} as const;

const BADGE_EXPECTED = {
  blue: {
    open: { bg: 'rgb(29, 78, 216)', color: 'rgb(255, 255, 255)' },
    closed: { bg: 'rgb(243, 244, 246)', color: 'rgb(75, 85, 99)' },
  },
  amber: {
    open: { bg: 'rgb(180, 83, 9)', color: 'rgb(255, 255, 255)' },
    closed: { bg: 'rgb(243, 244, 246)', color: 'rgb(75, 85, 99)' },
  },
} as const;

// ===================================================================
// Property 7: V2LinkBtn accent map correctness
// Feature: appointment-modal-v2, Property 7: V2LinkBtn accent map correctness
// Validates: Requirements 1.3, 1.5, 11.1
// ===================================================================

describe('Property 7: V2LinkBtn accent map correctness', () => {
  /**
   * For any valid accent value in {'blue', 'amber'} and any open state
   * {true, false}, the V2LinkBtn SHALL render with the correct color
   * triplet (background, text color, border color) and badge styling.
   *
   * **Validates: Requirements 1.3, 1.5, 11.1**
   */
  it('property: button renders correct bg, text color, and border for all accent × open combos', () => {
    fc.assert(
      fc.property(
        fc.record({
          accent: fc.oneof(fc.constant('blue' as const), fc.constant('amber' as const)),
          open: fc.boolean(),
        }),
        ({ accent, open }) => {
          const { unmount } = render(
            <V2LinkBtn
              icon={<TestIcon />}
              accent={accent}
              open={open}
              count={3}
              onClick={vi.fn()}
            >
              Label
            </V2LinkBtn>,
          );

          const btn = screen.getByRole('button');
          const state = open ? 'open' : 'closed';
          const expected = EXPECTED[accent][state];

          // Verify background color
          expect(btn.style.backgroundColor).toBe(expected.bg);

          // Verify text color
          expect(btn.style.color).toBe(expected.color);

          // Verify border contains the expected color
          expect(btn.style.border).toContain(expected.border);

          // Clean up to avoid DOM pollution between iterations
          unmount();
        },
      ),
      { numRuns: 100 },
    );
  });

  it('property: badge renders correct bg and text color for all accent × open combos', () => {
    fc.assert(
      fc.property(
        fc.record({
          accent: fc.oneof(fc.constant('blue' as const), fc.constant('amber' as const)),
          open: fc.boolean(),
        }),
        ({ accent, open }) => {
          const { unmount } = render(
            <V2LinkBtn
              icon={<TestIcon />}
              accent={accent}
              open={open}
              count={7}
              onClick={vi.fn()}
            >
              Label
            </V2LinkBtn>,
          );

          const badge = screen.getByText('7');
          const state = open ? 'open' : 'closed';
          const expected = BADGE_EXPECTED[accent][state];

          // Verify badge background color
          expect(badge.style.backgroundColor).toBe(expected.bg);

          // Verify badge text color
          expect(badge.style.color).toBe(expected.color);

          unmount();
        },
      ),
      { numRuns: 100 },
    );
  });
});
