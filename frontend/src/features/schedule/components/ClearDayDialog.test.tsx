/**
 * Tests for ClearDayDialog component.
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ClearDayDialog } from './ClearDayDialog';

const mockAffectedJobs = [
  { job_id: '1', customer_name: 'John Doe', service_type: 'Spring Startup' },
  { job_id: '2', customer_name: 'Jane Smith', service_type: 'Winterization' },
  { job_id: '3', customer_name: 'Bob Wilson', service_type: 'Repair' },
];

const defaultProps = {
  open: true,
  onOpenChange: vi.fn(),
  date: new Date(2025, 0, 28), // January 28, 2025 in local time
  appointmentCount: 5,
  affectedJobs: mockAffectedJobs,
  onConfirm: vi.fn(),
};

describe('ClearDayDialog', () => {
  it('renders dialog with correct data-testid', () => {
    render(<ClearDayDialog {...defaultProps} />);
    expect(screen.getByTestId('clear-day-dialog')).toBeInTheDocument();
  });

  it('displays warning icon', () => {
    render(<ClearDayDialog {...defaultProps} />);
    expect(screen.getByTestId('clear-day-warning')).toBeInTheDocument();
  });

  it('displays date in title', () => {
    render(<ClearDayDialog {...defaultProps} />);
    // Check for the formatted date - January 28, 2025
    expect(screen.getByText(/January 28, 2025/)).toBeInTheDocument();
  });

  it('displays appointment count', () => {
    render(<ClearDayDialog {...defaultProps} />);
    expect(screen.getByText(/5 appointments will be cleared/)).toBeInTheDocument();
  });

  it('displays singular appointment text for count of 1', () => {
    render(<ClearDayDialog {...defaultProps} appointmentCount={1} />);
    expect(screen.getByText(/1 appointment will be cleared/)).toBeInTheDocument();
  });

  it('displays affected jobs preview', () => {
    render(<ClearDayDialog {...defaultProps} />);
    expect(screen.getByTestId('affected-jobs-list')).toBeInTheDocument();
    expect(screen.getByText('John Doe')).toBeInTheDocument();
    expect(screen.getByText('Spring Startup')).toBeInTheDocument();
    expect(screen.getByText('Jane Smith')).toBeInTheDocument();
    expect(screen.getByText('Winterization')).toBeInTheDocument();
    expect(screen.getByText('Bob Wilson')).toBeInTheDocument();
    expect(screen.getByText('Repair')).toBeInTheDocument();
  });

  it('shows "and X more" for many jobs', () => {
    const manyJobs = Array.from({ length: 11 }, (_, i) => ({
      job_id: String(i + 1),
      customer_name: `Customer ${i + 1}`,
      service_type: 'Service',
    }));
    render(<ClearDayDialog {...defaultProps} affectedJobs={manyJobs} />);
    expect(screen.getByText(/and 3 more appointments\.\.\./)).toBeInTheDocument();
  });

  it('displays status reset notice', () => {
    render(<ClearDayDialog {...defaultProps} />);
    expect(screen.getByTestId('status-reset-notice')).toBeInTheDocument();
    expect(screen.getByText(/Jobs with "scheduled" status will be reset/)).toBeInTheDocument();
  });

  it('displays audit notice', () => {
    render(<ClearDayDialog {...defaultProps} />);
    expect(screen.getByTestId('audit-notice')).toBeInTheDocument();
    expect(screen.getByText(/This action will be logged for audit purposes/)).toBeInTheDocument();
  });

  it('renders Cancel button', () => {
    render(<ClearDayDialog {...defaultProps} />);
    expect(screen.getByTestId('clear-day-cancel')).toBeInTheDocument();
    expect(screen.getByTestId('clear-day-cancel')).toHaveTextContent('Cancel');
  });

  it('renders Clear Day button', () => {
    render(<ClearDayDialog {...defaultProps} />);
    expect(screen.getByTestId('clear-day-confirm')).toBeInTheDocument();
    expect(screen.getByTestId('clear-day-confirm')).toHaveTextContent('Clear Day');
  });

  it('calls onOpenChange when Cancel is clicked', () => {
    const onOpenChange = vi.fn();
    render(<ClearDayDialog {...defaultProps} onOpenChange={onOpenChange} />);
    fireEvent.click(screen.getByTestId('clear-day-cancel'));
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it('calls onConfirm when Clear Day is clicked', () => {
    const onConfirm = vi.fn();
    render(<ClearDayDialog {...defaultProps} onConfirm={onConfirm} />);
    fireEvent.click(screen.getByTestId('clear-day-confirm'));
    expect(onConfirm).toHaveBeenCalled();
  });

  it('shows loading state when isLoading is true', () => {
    render(<ClearDayDialog {...defaultProps} isLoading={true} />);
    expect(screen.getByTestId('clear-day-confirm')).toHaveTextContent('Clearing...');
    expect(screen.getByTestId('clear-day-confirm')).toBeDisabled();
    expect(screen.getByTestId('clear-day-cancel')).toBeDisabled();
  });

  it('does not render when open is false', () => {
    render(<ClearDayDialog {...defaultProps} open={false} />);
    expect(screen.queryByTestId('clear-day-dialog')).not.toBeInTheDocument();
  });
});
