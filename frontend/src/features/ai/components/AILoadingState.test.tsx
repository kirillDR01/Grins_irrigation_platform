import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { AILoadingState } from './AILoadingState';

describe('AILoadingState', () => {
  it('renders loading spinner', () => {
    render(<AILoadingState />);
    expect(screen.getByTestId('ai-loading-state')).toBeInTheDocument();
  });

  it('displays loading message', () => {
    render(<AILoadingState />);
    // Check for one of the dynamic loading texts
    const loadingText = screen.getByText(/Analyzing\.\.\.|Optimizing\.\.\.|Generating\.\.\./);
    expect(loadingText).toBeInTheDocument();
  });

  it('renders with correct styling', () => {
    render(<AILoadingState />);
    const container = screen.getByTestId('ai-loading-state');
    expect(container).toHaveClass('flex', 'flex-col', 'items-center', 'justify-center', 'py-12');
  });
});
