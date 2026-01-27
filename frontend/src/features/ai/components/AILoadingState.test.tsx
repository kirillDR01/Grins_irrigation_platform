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
    expect(screen.getByText('AI is thinking...')).toBeInTheDocument();
  });

  it('renders with correct styling', () => {
    render(<AILoadingState />);
    const container = screen.getByTestId('ai-loading-state');
    expect(container).toHaveClass('flex', 'items-center', 'justify-center');
  });
});
