import { AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

interface AIErrorStateProps {
  error: Error | string;
  onRetry?: () => void;
  showManualFallback?: boolean;
  onManualFallback?: () => void;
}

export function AIErrorState({ 
  error, 
  onRetry, 
  showManualFallback = false,
  onManualFallback 
}: AIErrorStateProps) {
  const errorMessage = typeof error === 'string' ? error : error.message;

  return (
    <Alert variant="destructive" data-testid="ai-error-state">
      <AlertCircle className="h-4 w-4" />
      <AlertTitle>AI Error</AlertTitle>
      <AlertDescription className="space-y-3">
        <p>{errorMessage}</p>
        <div className="flex gap-2">
          {onRetry && (
            <Button 
              variant="outline" 
              size="sm" 
              onClick={onRetry}
              data-testid="retry-btn"
            >
              Retry
            </Button>
          )}
          {showManualFallback && onManualFallback && (
            <Button 
              variant="secondary" 
              size="sm" 
              onClick={onManualFallback}
              data-testid="manual-fallback-btn"
            >
              Continue Manually
            </Button>
          )}
        </div>
      </AlertDescription>
    </Alert>
  );
}
