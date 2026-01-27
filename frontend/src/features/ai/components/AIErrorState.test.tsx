import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { AIErrorState } from './AIErrorState';

describe('AIErrorState', () => {
  it('renders error state', () => {
    render(<AIErrorState error="Test error" onRetry={vi.fn()} />);
    expect(screen.getByTestId('ai-error-state')).toBeInTheDocument();
  });

  it('displays error message', () => {
    render(<AIErrorState error="Connection failed" onRetry={vi.fn()} />);
    expect(screen.getByText(/Connection failed/i)).toBeInTheDocument();
  });

  it('displays retry button', () => {
    render(<AIErrorState error="Test error" onRetry={vi.fn()} />);
    expect(screen.getByTestId('retry-btn')).toBeInTheDocument();
  });

  it('calls onRetry when retry button is clicked', () => {
    const onRetry = vi.fn();
    render(<AIErrorState error="Test error" onRetry={onRetry} />);
    
    fireEvent.click(screen.getByTestId('retry-btn'));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it('displays manual fallback button when showManualFallback is true', () => {
    const onManualFallback = vi.fn();
    render(
      <AIErrorState
        error="Test error"
        onRetry={vi.fn()}
        showManualFallback={true}
        onManualFallback={onManualFallback}
      />
    );
    expect(screen.getByTestId('manual-fallback-btn')).toBeInTheDocument();
  });

  it('calls onManualFallback when manual button is clicked', () => {
    const onManualFallback = vi.fn();
    render(
      <AIErrorState
        error="Test error"
        onRetry={vi.fn()}
        showManualFallback={true}
        onManualFallback={onManualFallback}
      />
    );
    
    fireEvent.click(screen.getByTestId('manual-fallback-btn'));
    expect(onManualFallback).toHaveBeenCalledTimes(1);
  });

  it('does not display manual fallback button when showManualFallback is false', () => {
    render(<AIErrorState error="Test error" onRetry={vi.fn()} />);
    expect(screen.queryByTestId('manual-fallback-btn')).not.toBeInTheDocument();
  });

  it('handles Error object', () => {
    const error = new Error('Test error object');
    render(<AIErrorState error={error} onRetry={vi.fn()} />);
    expect(screen.getByText(/Test error object/i)).toBeInTheDocument();
  });
});
