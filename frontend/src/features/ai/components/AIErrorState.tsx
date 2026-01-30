import { AlertCircle, RefreshCw } from 'lucide-react';

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
    <div 
      className="bg-red-50 rounded-xl p-6 border border-red-100"
      data-testid="ai-error-state"
    >
      <div className="flex items-start gap-4">
        <div className="bg-red-100 p-3 rounded-full text-red-600 flex-shrink-0">
          <AlertCircle className="h-5 w-5" />
        </div>
        <div className="flex-1 space-y-3">
          <h3 className="text-lg font-bold text-red-800">AI Error</h3>
          <p className="text-sm text-red-600">{errorMessage}</p>
          <div className="flex gap-2">
            {onRetry && (
              <button 
                onClick={onRetry}
                className="bg-red-100 hover:bg-red-200 text-red-700 px-4 py-2 rounded-lg flex items-center gap-2 transition-colors"
                data-testid="retry-btn"
              >
                <RefreshCw className="h-4 w-4" />
                Retry
              </button>
            )}
            {showManualFallback && onManualFallback && (
              <button 
                onClick={onManualFallback}
                className="bg-slate-100 hover:bg-slate-200 text-slate-700 px-4 py-2 rounded-lg transition-colors"
                data-testid="manual-fallback-btn"
              >
                Continue Manually
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
