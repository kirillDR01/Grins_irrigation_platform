/**
 * Schedule Explanation Modal component.
 * Displays AI-generated explanation of schedule decisions.
 */

import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Sparkles, Loader2, AlertCircle } from 'lucide-react';
import { useScheduleExplanation } from '../hooks/useScheduleExplanation';
import type { ScheduleGenerateResponse } from '../types';

interface ScheduleExplanationModalProps {
  results: ScheduleGenerateResponse;
  scheduleDate: string;
}

export function ScheduleExplanationModal({
  results,
  scheduleDate,
}: ScheduleExplanationModalProps) {
  const [open, setOpen] = useState(false);
  const { explanation, isLoading, error, fetchExplanation } = useScheduleExplanation();

  const handleOpen = () => {
    setOpen(true);
    if (!explanation && !isLoading && !error) {
      fetchExplanation(results, scheduleDate);
    }
  };

  const handleRetry = () => {
    fetchExplanation(results, scheduleDate);
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button
          variant="outline"
          onClick={handleOpen}
          data-testid="explain-schedule-btn"
        >
          <Sparkles className="h-4 w-4 mr-2" />
          Explain This Schedule
        </Button>
      </DialogTrigger>
      <DialogContent
        className="max-w-2xl max-h-[80vh] overflow-y-auto"
        data-testid="schedule-explanation-modal"
      >
        <DialogHeader>
          <DialogTitle>Schedule Explanation</DialogTitle>
          <DialogDescription>
            AI-generated insights about this schedule's decisions and optimizations
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {isLoading && (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              <span className="ml-2 text-muted-foreground">
                Analyzing schedule...
              </span>
            </div>
          )}

          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription className="flex items-center justify-between">
                <span>{error}</span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleRetry}
                  data-testid="retry-explanation-btn"
                >
                  Retry
                </Button>
              </AlertDescription>
            </Alert>
          )}

          {explanation && (
            <>
              {/* Main Explanation */}
              <div className="prose prose-sm max-w-none">
                <p className="text-sm leading-relaxed whitespace-pre-wrap break-words">
                  {explanation.explanation}
                </p>
              </div>

              {/* Highlights */}
              {explanation.highlights.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-sm font-semibold">Key Highlights</h4>
                  <ul className="list-disc list-inside space-y-1">
                    {explanation.highlights.map((highlight, index) => (
                      <li
                        key={index}
                        className="text-sm text-muted-foreground break-words"
                        data-testid={`highlight-${index}`}
                      >
                        {highlight}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
