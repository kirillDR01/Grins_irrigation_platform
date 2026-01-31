/**
 * Schedule Generation Page component.
 * Allows generating optimized schedules for a selected date.
 */

import { useState } from 'react';
import { format } from 'date-fns';
import { PageHeader } from '@/shared/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Calendar } from '@/components/ui/calendar';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { CalendarIcon, Loader2, Zap, Eye, List, Map } from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  useGenerateSchedule,
  usePreviewSchedule,
  useScheduleCapacity,
} from '../hooks/useScheduleGeneration';
import { ScheduleResults } from './ScheduleResults';
import { ClearResultsButton } from './ClearResultsButton';
import { MapProvider } from './map/MapProvider';
import { ScheduleMap } from './map/ScheduleMap';
import { NaturalLanguageConstraintsInput } from './NaturalLanguageConstraintsInput';
import { SchedulingHelpAssistant } from './SchedulingHelpAssistant';
import { JobsReadyToSchedulePreview } from './JobsReadyToSchedulePreview';
import { useJobsReadyToSchedule } from '../hooks/useJobsReadyToSchedule';
import type { ScheduleGenerateResponse } from '../types';
import type { ViewMode } from '../types/map';
import type { ParsedConstraint } from '../types/explanation';

export function ScheduleGenerationPage() {
  const [selectedDate, setSelectedDate] = useState<Date>(new Date());
  const [results, setResults] = useState<ScheduleGenerateResponse | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('list');
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [constraints, setConstraints] = useState<ParsedConstraint[]>([]);
  const [excludedJobIds, setExcludedJobIds] = useState<Set<string>>(new Set());

  const dateStr = format(selectedDate, 'yyyy-MM-dd');
  const { data: capacity, isLoading: capacityLoading } =
    useScheduleCapacity(dateStr);
  
  const { data: jobsData, isLoading: jobsLoading, error: jobsError} = 
    useJobsReadyToSchedule(); // Don't pass date params - we want ALL unscheduled jobs

  const generateMutation = useGenerateSchedule();
  const previewMutation = usePreviewSchedule();

  const isGenerating =
    generateMutation.isPending || previewMutation.isPending;

  const handleToggleExclude = (jobId: string) => {
    setExcludedJobIds(prev => {
      const next = new Set(prev);
      if (next.has(jobId)) {
        next.delete(jobId);
      } else {
        next.add(jobId);
      }
      return next;
    });
  };

  const handleSelectAll = () => {
    setExcludedJobIds(new Set());
  };

  const handleDeselectAll = () => {
    if (jobsData?.jobs) {
      setExcludedJobIds(new Set(jobsData.jobs.map(j => j.job_id)));
    }
  };

  const handleGenerate = async () => {
    const includedJobIds = jobsData?.jobs
      .filter(j => !excludedJobIds.has(j.job_id))
      .map(j => j.job_id);

    const response = await generateMutation.mutateAsync({
      schedule_date: dateStr,
      job_ids: includedJobIds,
      constraints: constraints.map((c) => ({
        type: c.type,
        description: c.description,
        staff_name: c.staff_name,
        time_start: c.time_start,
        time_end: c.time_end,
        job_type: c.job_type,
        city: c.city,
      })),
    });
    setResults(response);
  };

  const handlePreview = async () => {
    const includedJobIds = jobsData?.jobs
      .filter(j => !excludedJobIds.has(j.job_id))
      .map(j => j.job_id);

    const response = await previewMutation.mutateAsync({
      schedule_date: dateStr,
      preview_only: true,
      job_ids: includedJobIds,
      constraints: constraints.map((c) => ({
        type: c.type,
        description: c.description,
        staff_name: c.staff_name,
        time_start: c.time_start,
        time_end: c.time_end,
        job_type: c.job_type,
        city: c.city,
      })),
    });
    setResults(response);
  };

  return (
    <div data-testid="schedule-generation-page" className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <PageHeader
        title="Generate Schedule"
        description={`Optimize routes and generate schedules for ${format(selectedDate, 'EEEE, MMMM d, yyyy')}`}
      />

      <div className="grid gap-8 grid-cols-1 lg:grid-cols-3">
        {/* Left Column (2/3): Job Selection and Preview */}
        <div className="lg:col-span-2 space-y-6">
          {/* Jobs Ready to Schedule Preview */}
          <JobsReadyToSchedulePreview
            jobs={jobsData?.jobs ?? []}
            isLoading={jobsLoading}
            error={jobsError}
            excludedJobIds={excludedJobIds}
            onToggleExclude={handleToggleExclude}
            onSelectAll={handleSelectAll}
            onDeselectAll={handleDeselectAll}
          />
        </div>

        {/* Right Column (1/3): Generation Controls */}
        <div className="space-y-6">
          {/* Date Selection Card */}
          <Card className="sticky top-4 bg-white rounded-2xl shadow-sm border border-slate-100">
            <CardHeader>
              <CardTitle>Generate Schedule</CardTitle>
              <CardDescription>
                Select date and configure constraints
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
            <Popover>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  className={cn(
                    'w-full justify-start text-left font-normal',
                    !selectedDate && 'text-muted-foreground'
                  )}
                  data-testid="date-picker-trigger"
                >
                  <CalendarIcon className="mr-2 h-4 w-4" />
                  {selectedDate ? (
                    format(selectedDate, 'EEEE, MMMM d, yyyy')
                  ) : (
                    <span>Pick a date</span>
                  )}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-auto p-0" align="start">
                <Calendar
                  mode="single"
                  selected={selectedDate}
                  onSelect={(date) => date && setSelectedDate(date)}
                  initialFocus
                />
              </PopoverContent>
            </Popover>

            <NaturalLanguageConstraintsInput
              scheduleDate={dateStr}
              onConstraintsChange={setConstraints}
            />

            <div className="flex gap-2">
              <Button
                onClick={handlePreview}
                variant="outline"
                disabled={isGenerating}
                className="flex-1"
                data-testid="preview-btn"
              >
                {previewMutation.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Eye className="mr-2 h-4 w-4" />
                )}
                Preview
              </Button>
              <Button
                onClick={handleGenerate}
                disabled={isGenerating}
                className="flex-1"
                data-testid="generate-schedule-btn"
              >
                {generateMutation.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Zap className="mr-2 h-4 w-4" />
                )}
                Generate Schedule
              </Button>
            </div>
          </CardContent>
          </Card>

          {/* Capacity Card */}
          <Card>
            <CardHeader>
              <CardTitle>Capacity Overview</CardTitle>
              <CardDescription>
                Staff availability for {format(selectedDate, 'MMM d')}
              </CardDescription>
            </CardHeader>
            <CardContent>
            {capacityLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : capacity ? (
              <div className="grid grid-cols-2 gap-4">
                <div className="text-center">
                  <div className="text-2xl font-bold" data-testid="available-staff">
                    {capacity.available_staff}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Available
                  </div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold" data-testid="capacity-hours">
                    {Math.round(capacity.total_capacity_minutes / 60)}h
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Capacity
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                No capacity data available
              </div>
            )}
          </CardContent>
        </Card>
        </div>
      </div>

      {/* Scheduling Help Assistant */}
      <SchedulingHelpAssistant />

      {/* View Toggle and Results Section */}
      {results && (
        <div className="space-y-4">
          {/* View Toggle Buttons */}
          <div className="flex justify-between items-center">
            <ClearResultsButton onClear={() => setResults(null)} />
            <div className="bg-slate-100 rounded-lg p-1 flex" data-testid="view-toggle">
              <Button
                variant={viewMode === 'list' ? 'default' : 'ghost'}
                size="sm"
                onClick={() => setViewMode('list')}
                data-testid="view-toggle-list"
                className={cn(
                  viewMode === 'list' && 'bg-white shadow-sm'
                )}
              >
                <List className="mr-2 h-4 w-4" />
                List
              </Button>
              <Button
                variant={viewMode === 'map' ? 'default' : 'ghost'}
                size="sm"
                onClick={() => setViewMode('map')}
                data-testid="view-toggle-map"
                className={cn(
                  viewMode === 'map' && 'bg-white shadow-sm'
                )}
              >
                <Map className="mr-2 h-4 w-4" />
                Map
              </Button>
            </div>
          </div>

          {/* Conditional View Rendering */}
          {viewMode === 'list' ? (
            <ScheduleResults results={results} scheduleDate={dateStr} />
          ) : (
            <MapProvider>
              <ScheduleMap
                assignments={results.assignments}
                selectedJobId={selectedJobId}
                onJobSelect={setSelectedJobId}
                showRoutes={true}
              />
            </MapProvider>
          )}
        </div>
      )}

      {/* Error Display */}
      {(generateMutation.error || previewMutation.error) && (
        <Card className="border-red-200 bg-red-50 rounded-2xl shadow-sm">
          <CardContent className="pt-6">
            <p className="text-red-800" data-testid="error-message">
              {generateMutation.error?.message ||
                previewMutation.error?.message ||
                'An error occurred'}
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
