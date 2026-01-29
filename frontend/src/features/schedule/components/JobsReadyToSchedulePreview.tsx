import { useState, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card';
import { Badge } from '@/shared/components/ui/badge';
import { Checkbox } from '@/shared/components/ui/checkbox';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/shared/components/ui/select';
import { Loader2, AlertCircle } from 'lucide-react';
import { Alert, AlertDescription } from '@/shared/components/ui/alert';
import { JobSelectionControls } from './JobSelectionControls';
import type { JobReadyToSchedule } from '../types';

interface JobsReadyToSchedulePreviewProps {
  jobs: JobReadyToSchedule[];
  isLoading: boolean;
  error: Error | null;
  excludedJobIds: Set<string>;
  onToggleExclude: (jobId: string) => void;
  onSelectAll?: () => void;
  onDeselectAll?: () => void;
}

export function JobsReadyToSchedulePreview({
  jobs,
  isLoading,
  error,
  excludedJobIds,
  onToggleExclude,
  onSelectAll,
  onDeselectAll,
}: JobsReadyToSchedulePreviewProps) {
  const [filterJobType, setFilterJobType] = useState<string>('all');
  const [filterPriority, setFilterPriority] = useState<string>('all');
  const [filterCity, setFilterCity] = useState<string>('all');

  // Extract unique values for filters
  const jobTypes = useMemo(() => {
    const types = new Set(jobs.map(j => j.job_type));
    return Array.from(types).sort();
  }, [jobs]);

  const priorities = useMemo(() => {
    const prios = new Set(jobs.map(j => j.priority));
    return Array.from(prios).sort();
  }, [jobs]);

  const cities = useMemo(() => {
    const citySet = new Set(jobs.map(j => j.city).filter(Boolean) as string[]);
    return Array.from(citySet).sort();
  }, [jobs]);

  // Apply filters
  const filteredJobs = useMemo(() => {
    return jobs.filter(job => {
      if (filterJobType !== 'all' && job.job_type !== filterJobType) return false;
      if (filterPriority !== 'all' && job.priority !== filterPriority) return false;
      if (filterCity !== 'all' && job.city !== filterCity) return false;
      return true;
    });
  }, [jobs, filterJobType, filterPriority, filterCity]);

  const selectedCount = filteredJobs.filter(j => !excludedJobIds.has(j.job_id)).length;
  const excludedCount = filteredJobs.filter(j => excludedJobIds.has(j.job_id)).length;

  if (isLoading) {
    return (
      <Card data-testid="jobs-preview-section">
        <CardHeader>
          <CardTitle>Jobs to Schedule</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            <span className="ml-2 text-muted-foreground">Loading jobs...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card data-testid="jobs-preview-section">
        <CardHeader>
          <CardTitle>Jobs to Schedule</CardTitle>
        </CardHeader>
        <CardContent>
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              Failed to load jobs: {error.message}
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  if (jobs.length === 0) {
    return (
      <Card data-testid="jobs-preview-section">
        <CardHeader>
          <CardTitle>Jobs to Schedule</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-muted-foreground">
            <p>No jobs available for scheduling on the selected date.</p>
            <p className="text-sm mt-2">
              Jobs with status "approved" or "requested" will appear here.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card data-testid="jobs-preview-section">
      <CardHeader>
        <CardTitle>Jobs to Schedule</CardTitle>
        <div className="flex gap-2 mt-4">
          <Select value={filterJobType} onValueChange={setFilterJobType}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Job Type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Job Types</SelectItem>
              {jobTypes.map(type => (
                <SelectItem key={type} value={type}>{type}</SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={filterPriority} onValueChange={setFilterPriority}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Priority" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Priorities</SelectItem>
              {priorities.map(priority => (
                <SelectItem key={priority} value={priority}>{priority}</SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={filterCity} onValueChange={setFilterCity}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="City" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Cities</SelectItem>
              {cities.map(city => (
                <SelectItem key={city} value={city}>{city}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </CardHeader>
      <CardContent>
        <div className="mb-4 flex items-center justify-between" data-testid="jobs-summary">
          <p className="text-sm text-muted-foreground">
            {selectedCount} jobs selected for scheduling
            {excludedCount > 0 && ` (${excludedCount} excluded)`}
          </p>
          {onSelectAll && onDeselectAll && (
            <JobSelectionControls
              jobIds={filteredJobs.map(j => j.job_id)}
              excludedJobIds={excludedJobIds}
              onSelectAll={onSelectAll}
              onDeselectAll={onDeselectAll}
            />
          )}
        </div>

        <div className="space-y-2 max-h-[400px] overflow-y-auto">
          {filteredJobs.map(job => {
            const isExcluded = excludedJobIds.has(job.job_id);
            return (
              <div
                key={job.job_id}
                data-testid={`job-preview-${job.job_id}`}
                className={`flex items-start gap-3 p-3 border rounded-lg ${
                  isExcluded ? 'opacity-50 bg-muted' : 'bg-background'
                }`}
              >
                <Checkbox
                  checked={!isExcluded}
                  onCheckedChange={() => onToggleExclude(job.job_id)}
                  data-testid={`exclude-job-${job.job_id}`}
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`font-medium ${isExcluded ? 'line-through' : ''}`}>
                      {job.customer_name}
                    </span>
                    <Badge variant="outline">{job.job_type}</Badge>
                    <Badge variant={job.priority === 'high' ? 'destructive' : 'secondary'}>
                      {job.priority}
                    </Badge>
                  </div>
                  <div className="text-sm text-muted-foreground">
                    {job.city && <span>{job.city} • </span>}
                    <span>{job.estimated_duration_minutes} min</span>
                    {job.status && <span> • {job.status}</span>}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
