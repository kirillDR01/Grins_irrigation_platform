/**
 * Unit tests for ScheduleMobilePage thin wrapper.
 * Validates: Requirement 4.2
 */

import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';

// ── Mock the composed view ─────────────────────────────────────────────

vi.mock('@/features/resource-mobile', () => ({
  ResourceMobileView: () => <div data-testid="resource-mobile-view" />,
}));

// ── Import component under test AFTER mocks ────────────────────────────

import { ScheduleMobilePage } from './ScheduleMobile';

describe('ScheduleMobilePage', () => {
  it('renders ResourceMobileView', () => {
    render(<ScheduleMobilePage />);
    expect(screen.getByTestId('resource-mobile-view')).toBeInTheDocument();
  });
});
