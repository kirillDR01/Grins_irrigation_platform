/**
 * Unit tests for ScheduleGeneratePage thin wrapper.
 * Validates: Requirement 2.2
 */

import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';

// ── Mock the composed view ─────────────────────────────────────────────

vi.mock('@/features/schedule', () => ({
  AIScheduleView: () => <div data-testid="ai-schedule-view" />,
}));

// ── Import component under test AFTER mocks ────────────────────────────

import { ScheduleGeneratePage } from './ScheduleGenerate';

describe('ScheduleGeneratePage', () => {
  it('renders AIScheduleView', () => {
    render(<ScheduleGeneratePage />);
    expect(screen.getByTestId('ai-schedule-view')).toBeInTheDocument();
  });
});
