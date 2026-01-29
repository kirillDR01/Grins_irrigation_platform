/**
 * Tests for ClearDayButton component.
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ClearDayButton } from './ClearDayButton';

describe('ClearDayButton', () => {
  it('renders with Trash2 icon and text', () => {
    render(<ClearDayButton onClick={vi.fn()} />);
    
    const button = screen.getByTestId('clear-day-btn');
    expect(button).toBeInTheDocument();
    expect(button).toHaveTextContent('Clear Day');
  });

  it('calls onClick when clicked', () => {
    const handleClick = vi.fn();
    render(<ClearDayButton onClick={handleClick} />);
    
    fireEvent.click(screen.getByTestId('clear-day-btn'));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('has correct data-testid', () => {
    render(<ClearDayButton onClick={vi.fn()} />);
    expect(screen.getByTestId('clear-day-btn')).toBeInTheDocument();
  });

  it('can be disabled', () => {
    render(<ClearDayButton onClick={vi.fn()} disabled />);
    expect(screen.getByTestId('clear-day-btn')).toBeDisabled();
  });

  it('does not call onClick when disabled', () => {
    const handleClick = vi.fn();
    render(<ClearDayButton onClick={handleClick} disabled />);
    
    fireEvent.click(screen.getByTestId('clear-day-btn'));
    expect(handleClick).not.toHaveBeenCalled();
  });
});
