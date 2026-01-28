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
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { useUnassignedJobExplanation } from '../hooks/useUnassignedJobExplanation';
import type { UnassignedJobResponse } from '../types';

interface UnassignedJobExplanationCardProps {
  job: UnassignedJobResponse;
  scheduleDate: string;
  availableStaff: string[];
}

export function UnassignedJobExplanationCard({
  job,
  scheduleDate,
  availableStaff,
}: UnassignedJobExplanationCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const { explanation, isLoading, error, refetch } = useUnassignedJobExplanation({
    job,
    scheduleDate,
    availableStaff,
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

      {/* Expandable Explanation Card */}
      {isExpanded && (
        <Card className="mt-2 border-yellow-200 bg-yellow-50">
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Why wasn't this job scheduled?</CardTitle>
            <CardDescription className="text-sm">
              {job.customer_name} - {job.service_type}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Loading State */}
            {isLoading && (
              <div className="flex items-center gap-2 text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Analyzing constraints...</span>
              </div>
            )}

            {/* Error State */}
            {error && (
              <Alert variant="destructive">
                <AlertDescription className="flex items-center justify-between">
                  <span>Failed to load explanation. {error.message}</span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => refetch()}
                    data-testid={`retry-explanation-${job.job_id}`}
                  >
                    Retry
                  </Button>
                </AlertDescription>
              </Alert>
            )}

            {/* Explanation Content */}
            {explanation && (
              <>
                {/* Main Explanation */}
                <div className="text-sm">
                  <p className="font-medium mb-2">Reason:</p>
                  <p className="text-muted-foreground">{explanation.explanation}</p>
                </div>

                {/* Suggestions */}
                {explanation.suggestions.length > 0 && (
                  <div className="text-sm">
                    <p className="font-medium mb-2">Suggestions:</p>
                    <ul className="list-disc list-inside space-y-1 text-muted-foreground">
                      {explanation.suggestions.map((suggestion, index) => (
                        <li key={index} data-testid={`suggestion-${job.job_id}-${index}`}>
                          {suggestion}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Alternative Dates */}
                {explanation.alternative_dates.length > 0 && (
                  <div className="text-sm">
                    <p className="font-medium mb-2">Alternative Dates:</p>
                    <div className="flex flex-wrap gap-2">
                      {explanation.alternative_dates.map((date, index) => (
                        <Badge
                          key={index}
                          variant="outline"
                          className="bg-white"
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
                  </div>
                )}
              </>
            )}

            {/* Fallback: Show basic reason if no AI explanation */}
            {!isLoading && !error && !explanation && (
              <div className="text-sm text-muted-foreground">
                <p className="font-medium mb-2">Basic Reason:</p>
                <p>{job.reason}</p>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
