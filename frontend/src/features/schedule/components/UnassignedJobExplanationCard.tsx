/**
 * Unassigned Job Explanation Card component.
 * Displays AI-powered explanation for why a job couldn't be scheduled.
 */

import { AlertCircle, Lightbulb, MapPin, Clock } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useUnassignedJobExplanation } from '../hooks/useUnassignedJobExplanation';
import type { UnassignedJobResponse } from '../types';

interface UnassignedJobExplanationCardProps {
  job: UnassignedJobResponse;
}

export function UnassignedJobExplanationCard({
  job,
}: UnassignedJobExplanationCardProps) {
  // Always fetch explanation when card is rendered
  const { explanation } = useUnassignedJobExplanation({
    job,
    enabled: true,
  });

  // Get job_type from either property
  const jobType = job.job_type || job.service_type;

  return (
    <div className="bg-amber-50 rounded-xl p-4 border border-amber-100" data-testid={`job-explanation-${job.job_id}`}>
      {/* Card Header */}
      <div className="flex items-start gap-3 mb-3">
        <div className="flex-shrink-0">
          <AlertCircle className="h-5 w-5 text-amber-500" />
        </div>
        <div className="flex-1">
          <h3 className="font-medium text-slate-800">Why This Job Wasn't Assigned</h3>
        </div>
      </div>

      {/* Job Info Section */}
      <div className="space-y-2 mb-3">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-slate-700">{jobType}</span>
          <span className="text-sm text-slate-500">•</span>
          <span className="text-sm text-slate-600">{job.customer_name}</span>
        </div>
        {job.address && (
          <div className="flex items-center gap-2 text-sm text-slate-600">
            <MapPin className="h-4 w-4 text-slate-400" />
            <span>{job.address}</span>
          </div>
        )}
      </div>

      {/* Explanation Section */}
      <div className="space-y-3">
        <div className="text-sm text-amber-700">
          <p className="font-medium mb-1">Reason:</p>
          <ul className="list-disc list-inside space-y-1 ml-2">
            <li>{job.reason}</li>
            {explanation?.reason && explanation.reason !== job.reason && (
              <li>{explanation.reason}</li>
            )}
          </ul>
        </div>

        {/* Suggestion Section */}
        {(explanation?.suggestions.length ?? 0) > 0 && (
          <div className="bg-white rounded-lg p-3">
            <div className="flex items-start gap-2">
              <Lightbulb className="h-4 w-4 text-amber-500 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="text-sm font-medium text-slate-700 mb-1">Suggested Action:</p>
                <p className="text-sm text-slate-600">{explanation?.suggestions[0]}</p>
              </div>
            </div>
          </div>
        )}

        {/* Alternative Dates */}
        {(explanation?.alternative_dates.length ?? 0) > 0 && (
          <div className="flex items-center gap-2 flex-wrap">
            <Clock className="h-4 w-4 text-slate-400" />
            <span className="text-sm text-slate-600">Try these dates:</span>
            {explanation?.alternative_dates.slice(0, 3).map((date, index) => (
              <Badge
                key={index}
                variant="outline"
                className="bg-white text-xs"
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

      {/* Action Buttons */}
      <div className="flex gap-2 mt-4">
        <Button
          variant="secondary"
          size="sm"
          data-testid={`manual-assign-${job.job_id}`}
        >
          Manual Assign
        </Button>
        <Button
          variant="ghost"
          size="sm"
          data-testid={`reschedule-${job.job_id}`}
        >
          Reschedule
        </Button>
      </div>
    </div>
  );
}
