import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CalendarClock } from 'lucide-react';
import { QueueFreshnessHeader } from './QueueFreshnessHeader';

describe('QueueFreshnessHeader (Gap 15)', () => {
  const baseProps = {
    icon: <CalendarClock data-testid="qfh-icon" />,
    title: 'Reschedule Requests',
    dataUpdatedAt: Date.now(),
    isRefetching: false,
    onRefresh: vi.fn(),
  };

  it('renders title, icon, and badge count', () => {
    render(<QueueFreshnessHeader {...baseProps} badgeCount={3} />);
    expect(screen.getByText('Reschedule Requests')).toBeInTheDocument();
    expect(screen.getByTestId('qfh-icon')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('renders a recent relative-time label when dataUpdatedAt is fresh', () => {
    render(<QueueFreshnessHeader {...baseProps} />);
    const label = screen.getByTestId('queue-last-updated');
    expect(label).toBeInTheDocument();
    expect(label.textContent).toMatch(/Updated/);
    expect(label.textContent).toMatch(/(seconds?|minute) ago/);
  });

  it('renders "Updating…" when dataUpdatedAt is 0', () => {
    render(<QueueFreshnessHeader {...baseProps} dataUpdatedAt={0} />);
    expect(screen.getByTestId('queue-last-updated')).toHaveTextContent('Updating…');
  });

  it('invokes onRefresh when the refresh button is clicked', async () => {
    const onRefresh = vi.fn();
    const user = userEvent.setup();
    render(
      <QueueFreshnessHeader
        {...baseProps}
        onRefresh={onRefresh}
        testId="refresh-test-btn"
      />,
    );
    await user.click(screen.getByTestId('refresh-test-btn'));
    expect(onRefresh).toHaveBeenCalledTimes(1);
  });

  it('renders the spinner class and disables the button while refetching', () => {
    render(
      <QueueFreshnessHeader
        {...baseProps}
        isRefetching
        testId="refresh-test-btn"
      />,
    );
    const btn = screen.getByTestId('refresh-test-btn');
    expect(btn).toBeDisabled();
    expect(btn.querySelector('svg')).toHaveClass('animate-spin');
  });
});
