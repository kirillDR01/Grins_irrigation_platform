import { Loader2 } from 'lucide-react';

export function AILoadingState() {
  return (
    <div 
      className="flex items-center justify-center gap-3 p-6 text-muted-foreground"
      data-testid="ai-loading-state"
    >
      <Loader2 className="h-5 w-5 animate-spin" />
      <span>AI is thinking...</span>
    </div>
  );
}
