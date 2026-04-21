/**
 * @deprecated Use /schedule/pick-jobs
 *
 * Job picker popup for manual schedule assignment (Req 22, 23).
 * Mirrors Jobs tab columns/filters/search. Supports bulk assignment
 * with date + staff + global time allocation and per-job time adjustments.
 */

import { useState, useMemo, useCallback } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Search, CalendarPlus, Clock, ChevronDown, ChevronUp } from 'lucide-react';
import { useJobsReadyToSchedule } from '../hooks/useJobsReadyToSchedule';
import { useCreateAppointment } from '../hooks/useAppointmentMutations';
import { useStaff } from '@/features/staff/hooks/useStaff';
import { toast } from 'sonner';
import { LoadingSpinner } from '@/shared/components/LoadingSpinner';
import type { JobReadyToSchedule } from '../types';

interface JobPickerPopupProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  defaultDate?: string;
  defaultStaffId?: string;
}

interface PerJobTime {
  start: string;
  end: string;
}

export function JobPickerPopup({
  open,
  onOpenChange,
  defaultDate,
  defaultStaffId,
}: JobPickerPopupProps) {
  const [selectedJobIds, setSelectedJobIds] = useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const [cityFilter, setCityFilter] = useState('');
  const [jobTypeFilter, setJobTypeFilter] = useState('all');
  const [priorityFilter, setPriorityFilter] = useState('all');

  // Bulk assignment fields
  const [assignDate, setAssignDate] = useState(defaultDate || new Date().toISOString().split('T')[0]);
  const [assignStaffId, setAssignStaffId] = useState(defaultStaffId || '');
  const [globalStartTime, setGlobalStartTime] = useState('08:00');
  const [globalDurationMinutes, setGlobalDurationMinutes] = useState(60);

  // Per-job time overrides
  const [perJobTimes, setPerJobTimes] = useState<Record<string, PerJobTime>>({});
  const [showTimeAdjust, setShowTimeAdjust] = useState(false);

  const { data, isLoading } = useJobsReadyToSchedule();
  const createAppointment = useCreateAppointment();
  const { data: staffData } = useStaff({ page_size: 100 });

  const jobs = useMemo(() => data?.jobs ?? [], [data?.jobs]);
  const staffList = staffData?.items ?? [];

  // Extract unique values for filter dropdowns
  const jobTypes = useMemo(() => {
    const types = new Set(jobs.map((j) => j.job_type));
    return Array.from(types).sort();
  }, [jobs]);

  // Filter jobs by all axes
  const filteredJobs = useMemo(() => {
    return jobs.filter((job) => {
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        const match =
          job.customer_name.toLowerCase().includes(q) ||
          job.job_type.toLowerCase().includes(q) ||
          job.city.toLowerCase().includes(q) ||
          job.job_id.toLowerCase().includes(q);
        if (!match) return false;
      }
      if (cityFilter && !job.city.toLowerCase().includes(cityFilter.toLowerCase())) return false;
      if (jobTypeFilter !== 'all' && job.job_type !== jobTypeFilter) return false;
      if (priorityFilter !== 'all' && job.priority !== priorityFilter) return false;
      return true;
    });
  }, [jobs, searchQuery, cityFilter, jobTypeFilter, priorityFilter]);

  const toggleJob = (jobId: string) => {
    setSelectedJobIds((prev) => {
      const next = new Set(prev);
      if (next.has(jobId)) {
        next.delete(jobId);
        // Clean up per-job time override
        setPerJobTimes((pt) => {
          const copy = { ...pt };
          delete copy[jobId];
          return copy;
        });
      } else {
        next.add(jobId);
      }
      return next;
    });
  };

  const toggleAll = () => {
    if (selectedJobIds.size === filteredJobs.length) {
      setSelectedJobIds(new Set());
      setPerJobTimes({});
    } else {
      setSelectedJobIds(new Set(filteredJobs.map((j) => j.job_id)));
    }
  };

  // Compute scheduled times for each selected job
  const computeJobTimes = useCallback(() => {
    const selectedJobs = filteredJobs.filter((j) => selectedJobIds.has(j.job_id));
    const result: Record<string, { start: string; end: string }> = {};

    // Parse global start time
    const [startH, startM] = globalStartTime.split(':').map(Number);
    let currentMinutes = startH * 60 + startM;

    for (const job of selectedJobs) {
      // Use per-job override if set, otherwise compute sequentially
      if (perJobTimes[job.job_id]) {
        result[job.job_id] = perJobTimes[job.job_id];
      } else {
        const jobDuration = job.estimated_duration_minutes || globalDurationMinutes;
        const endMinutes = currentMinutes + jobDuration;
        const sh = Math.floor(currentMinutes / 60).toString().padStart(2, '0');
        const sm = (currentMinutes % 60).toString().padStart(2, '0');
        const eh = Math.floor(endMinutes / 60).toString().padStart(2, '0');
        const em = (endMinutes % 60).toString().padStart(2, '0');
        result[job.job_id] = { start: `${sh}:${sm}`, end: `${eh}:${em}` };
        currentMinutes = endMinutes;
      }
    }
    return result;
  }, [filteredJobs, selectedJobIds, globalStartTime, globalDurationMinutes, perJobTimes]);

  const updatePerJobTime = (jobId: string, field: 'start' | 'end', value: string) => {
    setPerJobTimes((prev) => ({
      ...prev,
      [jobId]: {
        ...prev[jobId],
        [field]: value,
        // Initialize the other field from computed if not set
        ...(prev[jobId] ? {} : { start: globalStartTime, end: '' }),
      },
    }));
  };

  const handleBulkAssign = async () => {
    if (selectedJobIds.size === 0 || !assignStaffId) return;

    const times = computeJobTimes();
    let successCount = 0;
    let failCount = 0;

    for (const jobId of selectedJobIds) {
      const t = times[jobId];
      if (!t) continue;
      try {
        await createAppointment.mutateAsync({
          job_id: jobId,
          staff_id: assignStaffId,
          scheduled_date: assignDate,
          time_window_start: `${t.start}:00`,
          time_window_end: `${t.end}:00`,
        });
        successCount++;
      } catch {
        failCount++;
      }
    }

    if (successCount > 0) {
      toast.success(`Assigned ${successCount} job${successCount > 1 ? 's' : ''} to schedule`);
    }
    if (failCount > 0) {
      toast.error(`Failed to assign ${failCount} job${failCount > 1 ? 's' : ''}`);
    }

    setSelectedJobIds(new Set());
    setPerJobTimes({});
    onOpenChange(false);
  };

  const computedTimes = computeJobTimes();
  const selectedJobs = filteredJobs.filter((j) => selectedJobIds.has(j.job_id));

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="max-w-[100vw] h-full max-h-[100vh] flex flex-col rounded-none md:max-w-5xl md:h-auto md:max-h-[90vh] md:rounded-lg"
        data-testid="job-picker-popup"
      >
        <DialogHeader className="sticky top-0 z-10 bg-white pb-2 border-b border-slate-100 md:static md:border-b-0 md:pb-0">
          <DialogTitle>Pick Jobs to Schedule</DialogTitle>
          <DialogDescription>
            Search, filter, and bulk-assign jobs to a date and staff member.
          </DialogDescription>
        </DialogHeader>

        {/* Filters row */}
        <div className="flex gap-2 flex-wrap" data-testid="job-picker-filters">
          <div className="relative flex-1 min-w-[180px]">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <Input
              placeholder="Search customer, type, city..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 text-sm"
              data-testid="job-picker-search"
            />
          </div>
          <Input
            placeholder="City"
            value={cityFilter}
            onChange={(e) => setCityFilter(e.target.value)}
            className="w-[120px] text-sm"
            data-testid="job-picker-city"
          />
          <Select value={jobTypeFilter} onValueChange={setJobTypeFilter}>
            <SelectTrigger className="w-[150px] text-sm" data-testid="job-picker-type">
              <SelectValue placeholder="Job type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Types</SelectItem>
              {jobTypes.map((t) => (
                <SelectItem key={t} value={t}>{t}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={priorityFilter} onValueChange={setPriorityFilter}>
            <SelectTrigger className="w-[120px] text-sm" data-testid="job-picker-priority">
              <SelectValue placeholder="Priority" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All</SelectItem>
              {['1', '2', '3', '4', '5'].map((p) => (
                <SelectItem key={p} value={p}>Priority {p}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Job table */}
        <div className="flex-1 overflow-y-auto border rounded-lg min-h-0" data-testid="job-picker-list">
          {isLoading ? (
            <div className="flex items-center justify-center h-32"><LoadingSpinner /></div>
          ) : filteredJobs.length === 0 ? (
            <div className="p-8 text-center text-slate-500 text-sm">No unscheduled jobs found</div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-slate-50 sticky top-0">
                <tr>
                  <th className="p-2 text-left w-10">
                    <Checkbox
                      checked={filteredJobs.length > 0 && selectedJobIds.size === filteredJobs.length}
                      onCheckedChange={toggleAll}
                      data-testid="job-picker-select-all"
                    />
                  </th>
                  <th className="p-2 text-left font-medium text-slate-600">Customer</th>
                  <th className="p-2 text-left font-medium text-slate-600">Job Type</th>
                  <th className="p-2 text-left font-medium text-slate-600">City</th>
                  <th className="p-2 text-left font-medium text-slate-600">Priority</th>
                  <th className="p-2 text-left font-medium text-slate-600">Est. Duration</th>
                  <th className="p-2 text-left font-medium text-slate-600">Equipment</th>
                </tr>
              </thead>
              <tbody>
                {filteredJobs.map((job: JobReadyToSchedule) => (
                  <tr
                    key={job.job_id}
                    className={`border-t border-slate-100 hover:bg-slate-50 cursor-pointer ${selectedJobIds.has(job.job_id) ? 'bg-teal-50' : ''}`}
                    onClick={() => toggleJob(job.job_id)}
                    data-testid={`job-picker-row-${job.job_id}`}
                  >
                    <td className="p-2">
                      <Checkbox checked={selectedJobIds.has(job.job_id)} onCheckedChange={() => toggleJob(job.job_id)} />
                    </td>
                    <td className="p-2 font-medium text-slate-800">{job.customer_name}</td>
                    <td className="p-2 text-slate-600">{job.job_type}</td>
                    <td className="p-2 text-slate-600">{job.city}</td>
                    <td className="p-2 text-slate-600">{job.priority}</td>
                    <td className="p-2 text-slate-600">{job.estimated_duration_minutes ? `${job.estimated_duration_minutes}m` : '—'}</td>
                    <td className="p-2 text-slate-600 text-xs">{job.requires_equipment?.length ? job.requires_equipment.join(', ') : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Bulk assignment controls */}
        {selectedJobIds.size > 0 && (
          <div className="border-t pt-3 space-y-3">
            {/* Assignment row: date, staff, global time */}
            <div className="flex gap-3 flex-wrap items-end">
              <div className="space-y-1">
                <Label className="text-xs text-slate-500">Date</Label>
                <Input
                  type="date"
                  value={assignDate}
                  onChange={(e) => setAssignDate(e.target.value)}
                  className="w-[150px] text-sm"
                  data-testid="job-picker-date"
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs text-slate-500">Staff Member</Label>
                <Select value={assignStaffId} onValueChange={setAssignStaffId}>
                  <SelectTrigger className="w-[180px] text-sm" data-testid="job-picker-staff">
                    <SelectValue placeholder="Select staff" />
                  </SelectTrigger>
                  <SelectContent>
                    {staffList.map((s) => (
                      <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <Label className="text-xs text-slate-500">Start Time</Label>
                <Input
                  type="time"
                  value={globalStartTime}
                  onChange={(e) => setGlobalStartTime(e.target.value)}
                  className="w-[120px] text-sm"
                  data-testid="job-picker-start-time"
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs text-slate-500">Default Duration (min)</Label>
                <Input
                  type="number"
                  min={15}
                  step={15}
                  value={globalDurationMinutes}
                  onChange={(e) => setGlobalDurationMinutes(Number(e.target.value) || 60)}
                  className="w-[100px] text-sm"
                  data-testid="job-picker-duration"
                />
              </div>
            </div>

            {/* Per-job time adjustments toggle */}
            <button
              type="button"
              className="flex items-center gap-1 text-xs text-teal-600 hover:text-teal-700"
              onClick={() => setShowTimeAdjust(!showTimeAdjust)}
              data-testid="job-picker-time-adjust-toggle"
            >
              <Clock className="h-3 w-3" />
              Per-job time adjustments
              {showTimeAdjust ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            </button>

            {showTimeAdjust && selectedJobs.length > 0 && (
              <div className="border rounded-lg overflow-y-auto max-h-[150px]" data-testid="job-picker-time-adjustments">
                <table className="w-full text-xs">
                  <thead className="bg-slate-50 sticky top-0">
                    <tr>
                      <th className="p-2 text-left font-medium text-slate-600">Customer</th>
                      <th className="p-2 text-left font-medium text-slate-600">Job Type</th>
                      <th className="p-2 text-left font-medium text-slate-600">Start</th>
                      <th className="p-2 text-left font-medium text-slate-600">End</th>
                    </tr>
                  </thead>
                  <tbody>
                    {selectedJobs.map((job) => {
                      const t = computedTimes[job.job_id] || { start: globalStartTime, end: '' };
                      return (
                        <tr key={job.job_id} className="border-t border-slate-100">
                          <td className="p-2 text-slate-800">{job.customer_name}</td>
                          <td className="p-2 text-slate-600">{job.job_type}</td>
                          <td className="p-2">
                            <Input
                              type="time"
                              value={perJobTimes[job.job_id]?.start ?? t.start}
                              onChange={(e) => updatePerJobTime(job.job_id, 'start', e.target.value)}
                              className="w-[100px] h-7 text-xs"
                              data-testid={`job-time-start-${job.job_id}`}
                            />
                          </td>
                          <td className="p-2">
                            <Input
                              type="time"
                              value={perJobTimes[job.job_id]?.end ?? t.end}
                              onChange={(e) => updatePerJobTime(job.job_id, 'end', e.target.value)}
                              className="w-[100px] h-7 text-xs"
                              data-testid={`job-time-end-${job.job_id}`}
                            />
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}

            {/* Action row */}
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-500">
                {selectedJobIds.size} job{selectedJobIds.size !== 1 ? 's' : ''} selected
              </span>
              <Button
                onClick={handleBulkAssign}
                disabled={selectedJobIds.size === 0 || !assignStaffId || createAppointment.isPending}
                data-testid="job-picker-assign-btn"
                className="bg-teal-500 hover:bg-teal-600 text-white"
              >
                <CalendarPlus className="mr-2 h-4 w-4" />
                {createAppointment.isPending
                  ? 'Assigning...'
                  : `Assign ${selectedJobIds.size} Job${selectedJobIds.size !== 1 ? 's' : ''}`}
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
