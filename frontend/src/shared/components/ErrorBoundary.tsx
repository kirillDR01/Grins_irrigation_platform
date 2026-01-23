import { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';

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
          <Card className="max-w-md w-full">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-destructive">
                <AlertTriangle className="h-5 w-5" />
                Something went wrong
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground">
                An unexpected error occurred. Please try again or contact support if the
                problem persists.
              </p>
              {this.state.error && (
                <pre className="mt-4 p-2 bg-muted rounded text-xs overflow-auto">
                  {this.state.error.message}
                </pre>
              )}
            </CardContent>
            <CardFooter>
              <Button onClick={this.handleReset} data-testid="error-retry-button">
                Try Again
              </Button>
            </CardFooter>
          </Card>
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
    <Card className="border-destructive" data-testid="error-message">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-destructive text-base">
          <AlertTriangle className="h-4 w-4" />
          Error
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground">{error.message}</p>
      </CardContent>
      {onRetry && (
        <CardFooter>
          <Button variant="outline" size="sm" onClick={onRetry}>
            Retry
          </Button>
        </CardFooter>
      )}
    </Card>
  );
}
