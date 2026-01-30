import { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div
          className="flex items-center justify-center min-h-[400px] p-4"
          data-testid="error-boundary"
        >
          <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-6 max-w-md w-full">
            <div className="flex flex-col items-center text-center">
              {/* Error icon */}
              <div className="bg-red-100 rounded-full p-3 mb-4">
                <AlertTriangle className="h-6 w-6 text-red-500" />
              </div>
              
              {/* Title */}
              <h3 className="text-lg font-bold text-slate-800 mb-2">
                Something went wrong
              </h3>
              
              {/* Message */}
              <p className="text-slate-500 mb-4">
                An unexpected error occurred. Please try again or contact support if the
                problem persists.
              </p>
              
              {/* Error details */}
              {this.state.error && (
                <pre className="w-full mt-2 p-3 bg-slate-50 rounded-lg text-xs text-slate-600 overflow-auto text-left mb-4">
                  {this.state.error.message}
                </pre>
              )}
              
              {/* Retry button - primary teal styling */}
              <Button 
                onClick={this.handleReset} 
                data-testid="error-retry-button"
                className="bg-teal-500 hover:bg-teal-600 text-white"
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                Try Again
              </Button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

// Functional error display component for use with TanStack Query
interface ErrorMessageProps {
  error: Error | null;
  onRetry?: () => void;
}

export function ErrorMessage({ error, onRetry }: ErrorMessageProps) {
  if (!error) return null;

  return (
    <div 
      className="bg-white rounded-2xl shadow-sm border border-slate-100 p-6" 
      data-testid="error-message"
    >
      <div className="flex items-start gap-4">
        {/* Error icon */}
        <div className="bg-red-100 rounded-full p-3 flex-shrink-0">
          <AlertTriangle className="h-5 w-5 text-red-500" />
        </div>
        
        <div className="flex-1">
          {/* Title */}
          <h4 className="text-lg font-bold text-slate-800 mb-1">
            Error
          </h4>
          
          {/* Message */}
          <p className="text-slate-500 text-sm">{error.message}</p>
          
          {/* Retry button */}
          {onRetry && (
            <Button 
              onClick={onRetry} 
              className="mt-4 bg-teal-500 hover:bg-teal-600 text-white"
              size="sm"
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Retry
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
