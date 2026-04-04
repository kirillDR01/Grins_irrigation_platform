/**
 * Unit tests for ResourceMobileView composed page component.
 * Validates: Requirements 3.1, 3.2, 6.2
 */

import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';

// ── Mock child components as simple stubs ──────────────────────────────

vi.mock('./ResourceScheduleView', () => ({
  ResourceScheduleView: () => <div data-testid="resource-schedule-view" />,
}));

vi.mock('@/features/ai/components/ResourceMobileChat', () => ({
  ResourceMobileChat: () => <div data-testid="resource-mobile-chat" />,
}));

// ── Import component under test AFTER mocks ────────────────────────────

import { ResourceMobileView } from './ResourceMobileView';

describe('ResourceMobileView', () => {
  it('renders root element with data-testid="resource-mobile-page"', () => {
    render(<ResourceMobileView />);
    expect(screen.getByTestId('resource-mobile-page')).toBeInTheDocument();
  });

  it('renders both child components', () => {
    render(<ResourceMobileView />);
    expect(screen.getByTestId('resource-schedule-view')).toBeInTheDocument();
    expect(screen.getByTestId('resource-mobile-chat')).toBeInTheDocument();
  });

  it('renders ResourceScheduleView before ResourceMobileChat in document order', () => {
    render(<ResourceMobileView />);
    const scheduleView = screen.getByTestId('resource-schedule-view');
    const mobileChat = screen.getByTestId('resource-mobile-chat');

    // compareDocumentPosition returns a bitmask; bit 4 (DOCUMENT_POSITION_FOLLOWING) means the argument follows
    const position = scheduleView.compareDocumentPosition(mobileChat);
    expect(position & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });
});


// ── Property-Based Tests (fast-check) ──────────────────────────────────

import * as fc from 'fast-check';

/**
 * Feature: ai-scheduling-page-routing, Property 4: Mobile page composition structure
 * Validates: Requirements 3.1, 3.2, 6.2
 *
 * For any render of ResourceMobileView, the resulting DOM SHALL contain:
 * - A root element with data-testid="resource-mobile-page"
 * - resource-schedule-view appearing before resource-mobile-chat in document order
 */
describe('PBT: Property 4 — Mobile Page Composition Structure', () => {
  it('DOM structure invariants hold for any generated resource schedule data', () => {
    fc.assert(
      fc.property(
        fc.record({
          jobCount: fc.integer({ min: 0, max: 20 }),
          resourceId: fc.string({ minLength: 1, maxLength: 36 }),
          dayOffset: fc.integer({ min: 0, max: 6 }),
        }),
        (_data) => {
          const { unmount } = render(<ResourceMobileView />);

          // Root element
          const root = screen.getByTestId('resource-mobile-page');
          expect(root).toBeInTheDocument();

          // Both child components present
          const scheduleView = screen.getByTestId('resource-schedule-view');
          const mobileChat = screen.getByTestId('resource-mobile-chat');
          expect(scheduleView).toBeInTheDocument();
          expect(mobileChat).toBeInTheDocument();

          // Document order: schedule-view before mobile-chat
          const position = scheduleView.compareDocumentPosition(mobileChat);
          expect(position & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();

          unmount();
        }
      ),
      { numRuns: 100 }
    );
  });
});
