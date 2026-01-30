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
import { Calendar, AlertTriangle, CheckCircle, RefreshCw, Sparkles, Loader2 } from 'lucide-react';
import { AIErrorState } from './AIErrorState';

export function AIScheduleGenerator() {
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  
  const { schedule, isLoading, error, generateSchedule, regenerate } = useAISchedule();

  const handleGenerate = async () => {
    if (!startDate || !endDate) return;
    await generateSchedule({
      target_date: startDate,
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
    <div data-testid="ai-schedule-generator" className="space-y-6">
      {/* Main Card */}
      <Card className="bg-white rounded-2xl shadow-sm border border-slate-100">
        <CardHeader className="p-6 border-b border-slate-100">
          <CardTitle className="flex items-center gap-2 font-bold text-slate-800 text-lg">
            <Calendar className="h-5 w-5 text-teal-500" />
            <Sparkles className="h-5 w-5 text-teal-500" />
            AI Schedule Generator
          </CardTitle>
        </CardHeader>
        <CardContent className="p-6 space-y-6">
          {/* Date Range Selector */}
          <div data-testid="date-range-selector" className="space-y-4">
            <div>
              <label htmlFor="start-date" className="block text-sm font-medium text-slate-700 mb-2">
                Start Date
              </label>
              <input
                id="start-date"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-lg text-slate-700 placeholder-slate-400 focus:ring-2 focus:ring-teal-100 focus:border-teal-500 focus:outline-none"
                data-testid="start-date-input"
              />
            </div>
            <div>
              <label htmlFor="end-date" className="block text-sm font-medium text-slate-700 mb-2">
                End Date
              </label>
              <input
                id="end-date"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-lg text-slate-700 placeholder-slate-400 focus:ring-2 focus:ring-teal-100 focus:border-teal-500 focus:outline-none"
                data-testid="end-date-input"
              />
            </div>
          </div>

          {/* Constraints Section - Placeholder for NaturalLanguageConstraintsInput */}
          <div data-testid="constraints-section" className="space-y-2">
            <label className="block text-sm font-medium text-slate-700">
              Scheduling Constraints
            </label>
            <div className="text-sm text-slate-500 italic">
              Natural language constraints input will be integrated here
            </div>
          </div>

          {/* Job Selection Section - Placeholder for JobSelectionControls */}
          <div data-testid="job-selection-section" className="space-y-2">
            <label className="block text-sm font-medium text-slate-700">
              Job Selection
            </label>
            <div className="text-sm text-slate-500 italic">
              Job selection controls will be integrated here
            </div>
          </div>

          {/* Generate Button */}
          <Button
            onClick={handleGenerate}
            disabled={!startDate || !endDate || isLoading}
            className="w-full bg-gradient-to-r from-teal-500 to-teal-600 hover:from-teal-600 hover:to-teal-700 text-white px-6 py-3 rounded-xl font-medium shadow-sm transition-all"
            data-testid="generate-schedule-btn"
          >
            {isLoading ? (
              <>
                <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                Optimizing routes...
              </>
            ) : (
              <>
                <Sparkles className="h-5 w-5 mr-2" />
                Generate Schedule
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      {/* Loading State */}
      {isLoading && (
        <div className="flex flex-col items-center justify-center py-12">
          <div className="w-12 h-12 border-4 border-teal-200 border-t-teal-500 rounded-full animate-spin"></div>
          <p className="text-slate-600 mt-4 animate-pulse">Optimizing routes...</p>
        </div>
      )}

      {/* Error State */}
      {error && <AIErrorState error={error} onRetry={handleGenerate} />}

      {/* Generated Schedule */}
      {schedule && !isLoading && (
        <div data-testid="generated-schedule" className="space-y-4">
          {/* Confidence Score */}
          <Alert className="bg-teal-50 border-teal-100">
            <AlertDescription data-testid="ai-explanation" className="text-slate-700">
              Schedule generated with {(schedule.confidence_score * 100).toFixed(0)}% confidence.
            </AlertDescription>
          </Alert>

          {/* Schedule Data */}
          <Card className="bg-white rounded-2xl shadow-sm border border-slate-100">
            <CardHeader className="p-6 border-b border-slate-100">
              <CardTitle className="text-lg font-bold text-slate-800">Generated Schedule</CardTitle>
            </CardHeader>
            <CardContent className="p-6">
              <pre className="text-sm bg-slate-50 p-4 rounded-xl overflow-auto max-h-96 text-slate-700">
                {JSON.stringify(schedule.schedule, null, 2)}
              </pre>
            </CardContent>
          </Card>

          {/* Warnings */}
          {schedule.warnings.length > 0 && (
            <Alert variant="destructive" data-testid="schedule-warnings" className="bg-red-50 border-red-100">
              <AlertTriangle className="h-4 w-4 text-red-600" />
              <AlertDescription className="text-red-700">
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
          <div className="flex gap-3" data-testid="schedule-actions">
            <Button
              onClick={handleAccept}
              className="flex-1 bg-teal-500 hover:bg-teal-600 text-white"
              data-testid="accept-schedule-btn"
            >
              <CheckCircle className="h-4 w-4 mr-2" />
              Accept Schedule
            </Button>
            <Button
              onClick={handleModify}
              variant="outline"
              className="flex-1 bg-white hover:bg-slate-50 border-slate-200 text-slate-700"
              data-testid="modify-schedule-btn"
            >
              Modify
            </Button>
            <Button
              onClick={regenerate}
              variant="outline"
              className="bg-white hover:bg-slate-50 border-slate-200 text-slate-700"
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
