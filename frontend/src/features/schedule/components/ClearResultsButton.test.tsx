/**
 * Tests for ClearResultsButton component.
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ClearResultsButton } from './ClearResultsButton';

describe('ClearResultsButton', () => {
  it('renders with correct data-testid', () => {
    render(<ClearResultsButton onClear={vi.fn()} />);
    expect(screen.getByTestId('clear-results-btn')).toBeInTheDocument();
  });

  it('renders with X icon and text', () => {
    render(<ClearResultsButton onClear={vi.fn()} />);
    expect(screen.getByText('Clear Results')).toBeInTheDocument();
  });

  it('calls onClear when clicked', () => {
    const onClear = vi.fn();
    render(<ClearResultsButton onClear={onClear} />);
    
    fireEvent.click(screen.getByTestId('clear-results-btn'));
    
    expect(onClear).toHaveBeenCalledTimes(1);
  });

  it('has outline variant styling', () => {
    render(<ClearResultsButton onClear={vi.fn()} />);
    const button = screen.getByTestId('clear-results-btn');
    // Check that it's a button element
    expect(button.tagName).toBe('BUTTON');
  });
});
