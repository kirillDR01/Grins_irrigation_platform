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
import { Calendar, Users, AlertTriangle, CheckCircle, RefreshCw } from 'lucide-react';
import { AILoadingState } from './AILoadingState';
import { AIErrorState } from './AIErrorState';
import type { ScheduleDay, StaffAssignment, ScheduledJob, ScheduleWarning } from '../types';

export function AIScheduleGenerator() {
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [selectedStaff, setSelectedStaff] = useState<string[]>([]);
  
  const { schedule, isLoading, error, generateSchedule, regenerate } = useAISchedule();

  const handleGenerate = async () => {
    if (!startDate || !endDate) return;
    await generateSchedule({
      start_date: startDate,
      end_date: endDate,
      staff_ids: selectedStaff.length > 0 ? selectedStaff : undefined,
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
          {/* Date Range Selector */}
          <div data-testid="date-range-selector" className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="start-date" className="block text-sm font-medium mb-1">
                Start Date
              </label>
              <input
                id="start-date"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full px-3 py-2 border rounded-md"
                data-testid="start-date-input"
              />
            </div>
            <div>
              <label htmlFor="end-date" className="block text-sm font-medium mb-1">
                End Date
              </label>
              <input
                id="end-date"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="w-full px-3 py-2 border rounded-md"
                data-testid="end-date-input"
              />
            </div>
          </div>

          {/* Staff Filter */}
          <div data-testid="staff-filter">
            <label className="block text-sm font-medium mb-2">
              Filter by Staff (optional)
            </label>
            <div className="space-y-2">
              {['Viktor', 'Vas', 'Dad', 'Steven', 'Vitallik'].map((staff) => (
                <label key={staff} className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={selectedStaff.includes(staff)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedStaff([...selectedStaff, staff]);
                      } else {
                        setSelectedStaff(selectedStaff.filter((s) => s !== staff));
                      }
                    }}
                    data-testid={`staff-checkbox-${staff.toLowerCase()}`}
                  />
                  <span>{staff}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Generate Button */}
          <Button
            onClick={handleGenerate}
            disabled={!startDate || !endDate || isLoading}
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
          {/* AI Explanation */}
          <Alert>
            <AlertDescription data-testid="ai-explanation">
              {schedule.ai_explanation}
            </AlertDescription>
          </Alert>

          {/* Summary */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Schedule Summary</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4" data-testid="schedule-summary">
                <div>
                  <div className="text-sm text-muted-foreground">Total Jobs</div>
                  <div className="text-2xl font-bold">{schedule.summary.total_jobs}</div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground">Staff Members</div>
                  <div className="text-2xl font-bold">{schedule.summary.total_staff}</div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground">Days</div>
                  <div className="text-2xl font-bold">{schedule.summary.total_days}</div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground">Avg Jobs/Day</div>
                  <div className="text-2xl font-bold">
                    {schedule.summary.jobs_per_day_avg.toFixed(1)}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Warnings */}
          {schedule.summary.warnings_count > 0 && (
            <Alert variant="destructive" data-testid="schedule-warnings">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                <div className="font-semibold mb-2">
                  {schedule.summary.warnings_count} Warning(s)
                </div>
                <ul className="space-y-1">
                  {schedule.days.flatMap((day) =>
                    day.warnings.map((warning, idx) => (
                      <li key={`${day.date}-${idx}`} className="text-sm">
                        {warning.message}
                      </li>
                    ))
                  )}
                </ul>
              </AlertDescription>
            </Alert>
          )}

          {/* Schedule by Day */}
          <div className="space-y-4">
            {schedule.days.map((day) => (
              <ScheduleDayCard key={day.date} day={day} />
            ))}
          </div>

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

/**
 * ScheduleDayCard Component
 * Displays a single day's schedule with staff assignments
 */
function ScheduleDayCard({ day }: { day: ScheduleDay }) {
  return (
    <Card data-testid="schedule-day-card">
      <CardHeader>
        <CardTitle className="text-lg">
          {new Date(day.date).toLocaleDateString('en-US', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric',
          })}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {day.staff_assignments.map((assignment) => (
          <StaffAssignmentCard key={assignment.staff_id} assignment={assignment} />
        ))}
      </CardContent>
    </Card>
  );
}

/**
 * StaffAssignmentCard Component
 * Displays a staff member's jobs for the day
 */
function StaffAssignmentCard({ assignment }: { assignment: StaffAssignment }) {
  return (
    <div data-testid="staff-assignment" className="border rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Users className="h-4 w-4" />
          <span className="font-semibold">{assignment.staff_name}</span>
        </div>
        <div className="text-sm text-muted-foreground">
          {assignment.total_jobs} jobs • {Math.round(assignment.total_minutes / 60)}h
        </div>
      </div>
      <div className="space-y-2">
        {assignment.jobs.map((job) => (
          <JobCard key={job.job_id} job={job} />
        ))}
      </div>
    </div>
  );
}

/**
 * JobCard Component
 * Displays a single scheduled job
 */
function JobCard({ job }: { job: ScheduledJob }) {
  return (
    <div data-testid="scheduled-job" className="bg-muted/50 rounded p-3 text-sm">
      <div className="flex justify-between items-start mb-1">
        <div className="font-medium">{job.customer_name}</div>
        <div className="text-xs text-muted-foreground">
          {job.time_window_start} - {job.time_window_end}
        </div>
      </div>
      <div className="text-muted-foreground">{job.address}</div>
      <div className="flex justify-between items-center mt-2">
        <span className="text-xs bg-primary/10 text-primary px-2 py-1 rounded">
          {job.job_type}
        </span>
        <span className="text-xs text-muted-foreground">
          {job.estimated_duration_minutes} min
        </span>
      </div>
      {job.notes && (
        <div className="mt-2 text-xs text-muted-foreground italic">{job.notes}</div>
      )}
    </div>
  );
}
