import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { StatusBadge } from './StatusBadge';

describe('StatusBadge', () => {
  it('renders job status correctly', () => {
    render(<StatusBadge status="completed" type="job" />);
    expect(screen.getByTestId('status-completed')).toBeInTheDocument();
    expect(screen.getByText('completed')).toBeInTheDocument();
  });

  it('renders appointment status correctly', () => {
    render(<StatusBadge status="confirmed" type="appointment" />);
    expect(screen.getByTestId('status-confirmed')).toBeInTheDocument();
  });

  it('formats status with underscores', () => {
    render(<StatusBadge status="in_progress" type="job" />);
    expect(screen.getByText('in progress')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    render(<StatusBadge status="completed" className="custom-class" />);
    const badge = screen.getByTestId('status-completed');
    expect(badge).toHaveClass('custom-class');
  });
});
