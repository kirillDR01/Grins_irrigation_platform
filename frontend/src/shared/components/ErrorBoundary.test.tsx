import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ErrorBoundary, ErrorMessage } from './ErrorBoundary';

// Component that throws an error
const ThrowError = ({ shouldThrow }: { shouldThrow: boolean }) => {
  if (shouldThrow) {
    throw new Error('Test error message');
  }
  return <div data-testid="child-content">Child content</div>;
};

describe('ErrorBoundary', () => {
  let consoleSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    // Suppress console.error for cleaner test output
    consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    consoleSpy.mockRestore();
  });

  describe('when no error occurs', () => {
    it('should render children normally', () => {
      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={false} />
        </ErrorBoundary>
      );

      expect(screen.getByTestId('child-content')).toBeInTheDocument();
      expect(screen.getByText('Child content')).toBeInTheDocument();
    });

    it('should not show error UI', () => {
      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={false} />
        </ErrorBoundary>
      );

      expect(screen.queryByTestId('error-boundary')).not.toBeInTheDocument();
    });
  });

  describe('when an error occurs', () => {
    it('should catch the error and display error UI', () => {
      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      expect(screen.getByTestId('error-boundary')).toBeInTheDocument();
      expect(screen.queryByTestId('child-content')).not.toBeInTheDocument();
    });

    it('should display error title', () => {
      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    });

    it('should display error description', () => {
      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      expect(
        screen.getByText(/An unexpected error occurred. Please try again/)
      ).toBeInTheDocument();
    });

    it('should display the error message', () => {
      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      expect(screen.getByText('Test error message')).toBeInTheDocument();
    });

    it('should display retry button', () => {
      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      expect(screen.getByTestId('error-retry-button')).toBeInTheDocument();
      expect(screen.getByText('Try Again')).toBeInTheDocument();
    });

    it('should log error to console', () => {
      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      expect(consoleSpy).toHaveBeenCalledWith(
        'ErrorBoundary caught an error:',
        expect.any(Error),
        expect.any(Object)
      );
    });

    it('should reset error state when retry button is clicked', () => {
      // Use a stateful component to control the error state
      let shouldThrow = true;
      const ControlledThrowError = () => {
        if (shouldThrow) {
          throw new Error('Test error message');
        }
        return <div data-testid="child-content">Child content</div>;
      };

      const { rerender } = render(
        <ErrorBoundary>
          <ControlledThrowError />
        </ErrorBoundary>
      );

      // Error UI should be shown
      expect(screen.getByTestId('error-boundary')).toBeInTheDocument();

      // Change the state so it won't throw on next render
      shouldThrow = false;

      // Click retry button
      fireEvent.click(screen.getByTestId('error-retry-button'));

      // Rerender to trigger the reset
      rerender(
        <ErrorBoundary>
          <ControlledThrowError />
        </ErrorBoundary>
      );

      // Should show children again
      expect(screen.queryByTestId('error-boundary')).not.toBeInTheDocument();
      expect(screen.getByTestId('child-content')).toBeInTheDocument();
    });
  });

  describe('with custom fallback', () => {
    it('should render custom fallback when provided', () => {
      const customFallback = <div data-testid="custom-fallback">Custom Error UI</div>;

      render(
        <ErrorBoundary fallback={customFallback}>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      expect(screen.getByTestId('custom-fallback')).toBeInTheDocument();
      expect(screen.getByText('Custom Error UI')).toBeInTheDocument();
      expect(screen.queryByTestId('error-boundary')).not.toBeInTheDocument();
    });

    it('should not render custom fallback when no error', () => {
      const customFallback = <div data-testid="custom-fallback">Custom Error UI</div>;

      render(
        <ErrorBoundary fallback={customFallback}>
          <ThrowError shouldThrow={false} />
        </ErrorBoundary>
      );

      expect(screen.queryByTestId('custom-fallback')).not.toBeInTheDocument();
      expect(screen.getByTestId('child-content')).toBeInTheDocument();
    });
  });
});

describe('ErrorMessage', () => {
  describe('when error is null', () => {
    it('should render nothing', () => {
      const { container } = render(<ErrorMessage error={null} />);

      expect(container.firstChild).toBeNull();
    });
  });

  describe('when error is provided', () => {
    it('should render error message card', () => {
      const error = new Error('Test error');

      render(<ErrorMessage error={error} />);

      expect(screen.getByTestId('error-message')).toBeInTheDocument();
    });

    it('should display error title', () => {
      const error = new Error('Test error');

      render(<ErrorMessage error={error} />);

      expect(screen.getByText('Error')).toBeInTheDocument();
    });

    it('should display error message text', () => {
      const error = new Error('This is the error message');

      render(<ErrorMessage error={error} />);

      expect(screen.getByText('This is the error message')).toBeInTheDocument();
    });

    it('should have redesigned card styling', () => {
      const error = new Error('Test error');

      render(<ErrorMessage error={error} />);

      expect(screen.getByTestId('error-message')).toHaveClass('bg-white', 'rounded-2xl', 'shadow-sm', 'border', 'border-slate-100');
    });
  });

  describe('retry functionality', () => {
    it('should not render retry button when onRetry is not provided', () => {
      const error = new Error('Test error');

      render(<ErrorMessage error={error} />);

      expect(screen.queryByText('Retry')).not.toBeInTheDocument();
    });

    it('should render retry button when onRetry is provided', () => {
      const error = new Error('Test error');
      const onRetry = vi.fn();

      render(<ErrorMessage error={error} onRetry={onRetry} />);

      expect(screen.getByText('Retry')).toBeInTheDocument();
    });

    it('should call onRetry when retry button is clicked', () => {
      const error = new Error('Test error');
      const onRetry = vi.fn();

      render(<ErrorMessage error={error} onRetry={onRetry} />);

      fireEvent.click(screen.getByText('Retry'));

      expect(onRetry).toHaveBeenCalledTimes(1);
    });
  });
});
