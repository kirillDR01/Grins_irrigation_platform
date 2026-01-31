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
import { Sparkles, AlertCircle, Info, RefreshCw } from 'lucide-react';
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
          className="gap-2"
        >
          <Sparkles className="h-4 w-4" />
          Explain This Schedule
        </Button>
      </DialogTrigger>
      <DialogContent
        className="max-w-lg overflow-hidden"
        data-testid="schedule-explanation-modal"
      >
        <DialogHeader className="p-6 border-b border-slate-100 bg-slate-50/50">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-full bg-teal-100 text-teal-600">
              <Info className="h-5 w-5" />
            </div>
            <div>
              <DialogTitle className="text-lg font-bold text-slate-800">
                Why This Schedule?
              </DialogTitle>
              <DialogDescription className="text-slate-500 text-sm">
                AI-generated insights about scheduling decisions
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="p-6 max-h-[60vh] overflow-y-auto">
          {isLoading && (
            <div className="flex flex-col items-center justify-center py-12">
              <div className="w-12 h-12 border-4 border-teal-200 border-t-teal-500 rounded-full animate-spin" />
              <span className="mt-4 text-slate-600">
                Analyzing schedule...
              </span>
            </div>
          )}

          {error && (
            <div className="bg-red-50 rounded-xl p-6 border border-red-100">
              <div className="flex items-start gap-3">
                <div className="p-2 rounded-full bg-red-100 text-red-600 shrink-0">
                  <AlertCircle className="h-5 w-5" />
                </div>
                <div className="flex-1">
                  <h4 className="font-medium text-red-800">Unable to generate explanation</h4>
                  <p className="text-sm text-red-600 mt-1">{error}</p>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleRetry}
                    className="mt-3 bg-red-100 hover:bg-red-200 text-red-700 border-red-200"
                    data-testid="retry-explanation-btn"
                  >
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Retry
                  </Button>
                </div>
              </div>
            </div>
          )}

          {explanation && (
            <div className="space-y-4">
              {/* Main Explanation */}
              <div className="text-slate-600 text-sm leading-relaxed whitespace-pre-wrap break-words">
                {explanation.explanation}
              </div>

              {/* Factors Section */}
              {explanation.highlights.length > 0 && (
                <div className="bg-slate-50 rounded-lg p-4 mt-4">
                  <h4 className="text-sm font-semibold text-slate-700 mb-3">
                    Key Factors Considered
                  </h4>
                  <ul className="space-y-2">
                    {explanation.highlights.map((highlight, index) => (
                      <li
                        key={index}
                        className="flex items-start gap-2 text-sm text-slate-600"
                        data-testid={`highlight-${index}`}
                      >
                        <span className="w-1.5 h-1.5 rounded-full bg-teal-500 mt-2 shrink-0" />
                        <span className="break-words">{highlight}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="p-6 border-t border-slate-100 bg-slate-50/50">
          <Button
            variant="secondary"
            onClick={() => setOpen(false)}
            className="w-full"
            data-testid="close-explanation-btn"
          >
            Close
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
