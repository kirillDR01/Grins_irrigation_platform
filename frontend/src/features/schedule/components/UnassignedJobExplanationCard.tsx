/**
 * Unassigned Job Explanation Card component.
 * Displays AI-powered explanation for why a job couldn't be scheduled.
 */

import { useState } from 'react';
import { ChevronDown, ChevronRight, HelpCircle, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { useUnassignedJobExplanation } from '../hooks/useUnassignedJobExplanation';
import type { UnassignedJobResponse } from '../types';

interface UnassignedJobExplanationCardProps {
  job: UnassignedJobResponse;
}

export function UnassignedJobExplanationCard({
  job,
}: UnassignedJobExplanationCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const { explanation, isLoading, error, refetch } = useUnassignedJobExplanation({
    job,
    enabled: isExpanded,
  });

  const handleToggle = () => {
    if (!isExpanded && !explanation && !error) {
      // First time expanding - trigger fetch
      setIsExpanded(true);
    } else {
      setIsExpanded(!isExpanded);
    }
  };

  return (
    <div data-testid={`job-explanation-${job.job_id}`}>
      {/* Why? Link */}
      <Button
        variant="link"
        size="sm"
        onClick={handleToggle}
        className="h-auto p-0 text-blue-600 hover:text-blue-800"
        data-testid={`why-link-${job.job_id}`}
      >
        <HelpCircle className="h-4 w-4 mr-1" />
        Why?
        {isExpanded ? (
          <ChevronDown className="h-4 w-4 ml-1" />
        ) : (
          <ChevronRight className="h-4 w-4 ml-1" />
        )}
      </Button>

      {/* Expandable Explanation Card - Compact Design */}
      {isExpanded && (
        <Card className="mt-1 border-yellow-200 bg-yellow-50 max-w-md">
          <CardHeader className="py-2 px-3">
            <CardTitle className="text-sm font-medium">Why not scheduled?</CardTitle>
          </CardHeader>
          <CardContent className="py-2 px-3 space-y-2">
            {/* Loading State */}
            {isLoading && (
              <div className="flex items-center gap-2 text-muted-foreground text-xs">
                <Loader2 className="h-3 w-3 animate-spin" />
                <span>Analyzing...</span>
              </div>
            )}

            {/* Error State */}
            {error && (
              <Alert variant="destructive" className="py-1 px-2">
                <AlertDescription className="flex items-center justify-between text-xs">
                  <span>Failed to load</span>
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-6 text-xs px-2"
                    onClick={() => refetch()}
                    data-testid={`retry-explanation-${job.job_id}`}
                  >
                    Retry
                  </Button>
                </AlertDescription>
              </Alert>
            )}

            {/* Explanation Content - Compact */}
            {explanation && (
              <div className="space-y-2 text-xs">
                {/* Main Reason - truncated */}
                <div>
                  <span className="font-medium">Reason: </span>
                  <span className="text-muted-foreground">
                    {explanation.reason.length > 150 
                      ? `${explanation.reason.substring(0, 150)}...` 
                      : explanation.reason}
                  </span>
                </div>

                {/* Suggestions - show first 2 only */}
                {explanation.suggestions.length > 0 && (
                  <div>
                    <span className="font-medium">Tips: </span>
                    <span className="text-muted-foreground">
                      {explanation.suggestions.slice(0, 2).join(' • ')}
                    </span>
                  </div>
                )}

                {/* Alternative Dates - inline badges */}
                {explanation.alternative_dates.length > 0 && (
                  <div className="flex items-center gap-1 flex-wrap">
                    <span className="font-medium">Try: </span>
                    {explanation.alternative_dates.slice(0, 3).map((date, index) => (
                      <Badge
                        key={index}
                        variant="outline"
                        className="bg-white text-xs py-0 px-1.5 h-5"
                        data-testid={`alt-date-${job.job_id}-${index}`}
                      >
                        {new Date(date).toLocaleDateString('en-US', {
                          weekday: 'short',
                          month: 'short',
                          day: 'numeric',
                        })}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Fallback: Show basic reason if no AI explanation */}
            {!isLoading && !error && !explanation && (
              <div className="text-xs text-muted-foreground">
                <span className="font-medium">Reason: </span>
                <span>{job.reason}</span>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
