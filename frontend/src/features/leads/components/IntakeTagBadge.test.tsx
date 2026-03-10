import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { IntakeTagBadge } from './IntakeTagBadge';

describe('IntakeTagBadge', () => {
  it('renders green badge for "schedule" tag', () => {
    render(<IntakeTagBadge tag="schedule" />);
    const badge = screen.getByTestId('intake-tag-schedule');
    expect(badge).toHaveTextContent('Schedule');
    expect(badge.className).toContain('bg-green-100');
    expect(badge.className).toContain('text-green-800');
  });

  it('renders orange badge for "follow_up" tag', () => {
    render(<IntakeTagBadge tag="follow_up" />);
    const badge = screen.getByTestId('intake-tag-follow_up');
    expect(badge).toHaveTextContent('Follow Up');
    expect(badge.className).toContain('bg-orange-100');
    expect(badge.className).toContain('text-orange-800');
  });

  it('renders gray badge for null (untagged)', () => {
    render(<IntakeTagBadge tag={null} />);
    const badge = screen.getByTestId('intake-tag-none');
    expect(badge).toHaveTextContent('Untagged');
    expect(badge.className).toContain('bg-gray-100');
  });

  it('applies additional className when provided', () => {
    render(<IntakeTagBadge tag="schedule" className="ml-4" />);
    const badge = screen.getByTestId('intake-tag-schedule');
    expect(badge.className).toContain('ml-4');
  });
});
