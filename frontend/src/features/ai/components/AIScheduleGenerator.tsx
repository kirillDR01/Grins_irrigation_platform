/**
 * AIScheduleGenerator Component
 * 
 * AI-powered schedule generation interface
 * Displays generated schedules by day with staff assignments,
 * warnings, and provides approval/modification actions
 */

import { useState } from 'react';
import { useAISchedule } from '../hooks/useAISchedule';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Calendar, AlertTriangle, CheckCircle, RefreshCw } from 'lucide-react';
import { AILoadingState } from './AILoadingState';
import { AIErrorState } from './AIErrorState';

export function AIScheduleGenerator() {
  const [targetDate, setTargetDate] = useState('');
  
  const { schedule, isLoading, error, generateSchedule, regenerate } = useAISchedule();

  const handleGenerate = async () => {
    if (!targetDate) return;
    await generateSchedule({
      target_date: targetDate,
      job_ids: undefined, // Let the backend select all available jobs
    });
  };

  const handleAccept = () => {
    // TODO: Implement schedule acceptance
    console.log('Schedule accepted');
  };

  const handleModify = () => {
    // TODO: Implement schedule modification
    console.log('Modify schedule');
  };

  return (
    <div data-testid="ai-schedule-generator" className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Calendar className="h-5 w-5" />
            AI Schedule Generator
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Date Selector */}
          <div data-testid="date-selector">
            <label htmlFor="target-date" className="block text-sm font-medium mb-1">
              Target Date
            </label>
            <input
              id="target-date"
              type="date"
              value={targetDate}
              onChange={(e) => setTargetDate(e.target.value)}
              className="w-full px-3 py-2 border rounded-md"
              data-testid="target-date-input"
            />
          </div>

          {/* Generate Button */}
          <Button
            onClick={handleGenerate}
            disabled={!targetDate || isLoading}
            className="w-full"
            data-testid="generate-schedule-btn"
          >
            {isLoading ? 'Generating...' : 'Generate Schedule'}
          </Button>
        </CardContent>
      </Card>

      {/* Loading State */}
      {isLoading && <AILoadingState message="Generating optimal schedule..." />}

      {/* Error State */}
      {error && <AIErrorState error={error} onRetry={handleGenerate} />}

      {/* Generated Schedule */}
      {schedule && !isLoading && (
        <div data-testid="generated-schedule" className="space-y-4">
          {/* Confidence Score */}
          <Alert>
            <AlertDescription data-testid="ai-explanation">
              Schedule generated with {(schedule.confidence_score * 100).toFixed(0)}% confidence.
            </AlertDescription>
          </Alert>

          {/* Schedule Data */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Generated Schedule</CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="text-sm bg-muted p-4 rounded overflow-auto max-h-96">
                {JSON.stringify(schedule.schedule, null, 2)}
              </pre>
            </CardContent>
          </Card>

          {/* Warnings */}
          {schedule.warnings.length > 0 && (
            <Alert variant="destructive" data-testid="schedule-warnings">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                <div className="font-semibold mb-2">
                  {schedule.warnings.length} Warning(s)
                </div>
                <ul className="space-y-1">
                  {schedule.warnings.map((warning, idx) => (
                    <li key={idx} className="text-sm">
                      {warning}
                    </li>
                  ))}
                </ul>
              </AlertDescription>
            </Alert>
          )}

          {/* Action Buttons */}
          <div className="flex gap-2" data-testid="schedule-actions">
            <Button
              onClick={handleAccept}
              className="flex-1"
              data-testid="accept-schedule-btn"
            >
              <CheckCircle className="h-4 w-4 mr-2" />
              Accept Schedule
            </Button>
            <Button
              onClick={handleModify}
              variant="outline"
              className="flex-1"
              data-testid="modify-schedule-btn"
            >
              Modify
            </Button>
            <Button
              onClick={regenerate}
              variant="outline"
              data-testid="regenerate-btn"
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Regenerate
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
