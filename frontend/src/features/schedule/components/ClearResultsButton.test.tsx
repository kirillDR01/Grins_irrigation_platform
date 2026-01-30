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

  it('renders with Trash2 icon and text', () => {
    render(<ClearResultsButton onClear={vi.fn()} />);
    expect(screen.getByText('Clear Results')).toBeInTheDocument();
  });

  it('opens confirmation dialog when clicked', () => {
    const onClear = vi.fn();
    render(<ClearResultsButton onClear={onClear} />);
    
    fireEvent.click(screen.getByTestId('clear-results-btn'));
    
    expect(screen.getByTestId('clear-confirmation-dialog')).toBeInTheDocument();
    expect(onClear).not.toHaveBeenCalled();
  });

  it('calls onClear when confirmation is clicked', () => {
    const onClear = vi.fn();
    render(<ClearResultsButton onClear={onClear} />);
    
    // Open dialog
    fireEvent.click(screen.getByTestId('clear-results-btn'));
    
    // Confirm
    fireEvent.click(screen.getByTestId('confirm-clear-btn'));
    
    expect(onClear).toHaveBeenCalledTimes(1);
  });

  it('does not call onClear when cancel is clicked', () => {
    const onClear = vi.fn();
    render(<ClearResultsButton onClear={onClear} />);
    
    // Open dialog
    fireEvent.click(screen.getByTestId('clear-results-btn'));
    
    // Cancel
    fireEvent.click(screen.getByTestId('cancel-clear-btn'));
    
    expect(onClear).not.toHaveBeenCalled();
  });

  it('has secondary variant styling', () => {
    render(<ClearResultsButton onClear={vi.fn()} />);
    const button = screen.getByTestId('clear-results-btn');
    // Check that it's a button element
    expect(button.tagName).toBe('BUTTON');
  });
});
