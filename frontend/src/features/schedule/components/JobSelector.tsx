/**
 * Job selector modal for adding unscheduled jobs to the schedule (Req 26).
 * Filterable DataTable with multi-select and "Add to Schedule" action.
 */

import { useState, useMemo } from 'react';
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Search, CalendarPlus } from 'lucide-react';
import { useJobsReadyToSchedule } from '../hooks/useJobsReadyToSchedule';
import { useCreateAppointment } from '../hooks/useAppointmentMutations';
import { toast } from 'sonner';
import { LoadingSpinner } from '@/shared/components/LoadingSpinner';
import type { JobReadyToSchedule } from '../types';

interface JobSelectorProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  defaultDate?: string;
  defaultStaffId?: string;
}

export function JobSelector({
  open,
  onOpenChange,
  defaultDate,
  defaultStaffId,
}: JobSelectorProps) {
  const [selectedJobIds, setSelectedJobIds] = useState<Set<string>>(new Set());
  const [cityFilter, setCityFilter] = useState('');
  const [jobTypeFilter, setJobTypeFilter] = useState('all');
  const [customerFilter, setCustomerFilter] = useState('');

  const { data, isLoading } = useJobsReadyToSchedule();
  const createAppointment = useCreateAppointment();

  const jobs = data?.jobs ?? [];

  // Extract unique job types and cities for filter dropdowns
  const jobTypes = useMemo(() => {
    const types = new Set(jobs.map((j) => j.job_type));
    return Array.from(types).sort();
  }, [jobs]);

  // Filter jobs
  const filteredJobs = useMemo(() => {
    return jobs.filter((job) => {
      if (cityFilter && !job.city.toLowerCase().includes(cityFilter.toLowerCase())) {
        return false;
      }
      if (jobTypeFilter !== 'all' && job.job_type !== jobTypeFilter) {
        return false;
      }
      if (
        customerFilter &&
        !job.customer_name.toLowerCase().includes(customerFilter.toLowerCase())
      ) {
        return false;
      }
      return true;
    });
  }, [jobs, cityFilter, jobTypeFilter, customerFilter]);

  const toggleJob = (jobId: string) => {
    setSelectedJobIds((prev) => {
      const next = new Set(prev);
      if (next.has(jobId)) {
        next.delete(jobId);
      } else {
        next.add(jobId);
      }
      return next;
    });
  };

  const toggleAll = () => {
    if (selectedJobIds.size === filteredJobs.length) {
      setSelectedJobIds(new Set());
    } else {
      setSelectedJobIds(new Set(filteredJobs.map((j) => j.job_id)));
    }
  };

  const handleAddToSchedule = async () => {
    if (selectedJobIds.size === 0) return;

    const date = defaultDate || new Date().toISOString().split('T')[0];
    const staffId = defaultStaffId || '';

    let successCount = 0;
    let failCount = 0;

    for (const jobId of selectedJobIds) {
      try {
        await createAppointment.mutateAsync({
          job_id: jobId,
          staff_id: staffId,
          scheduled_date: date,
          time_window_start: '08:00:00',
          time_window_end: '10:00:00',
        });
        successCount++;
      } catch {
        failCount++;
      }
    }

    if (successCount > 0) {
      toast.success(`Added ${successCount} job${successCount > 1 ? 's' : ''} to schedule`);
    }
    if (failCount > 0) {
      toast.error(`Failed to add ${failCount} job${failCount > 1 ? 's' : ''}`);
    }

    setSelectedJobIds(new Set());
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="max-w-[100vw] h-full max-h-[100vh] flex flex-col rounded-none md:max-w-3xl md:h-auto md:max-h-[80vh] md:rounded-lg"
        data-testid="job-selector-modal"
      >
        <DialogHeader className="sticky top-0 z-10 bg-white pb-2 border-b border-slate-100 md:static md:border-b-0 md:pb-0">
          <DialogTitle>Select Jobs to Schedule</DialogTitle>
          <DialogDescription>
            Filter and select unscheduled jobs to add to the calendar.
          </DialogDescription>
        </DialogHeader>

        {/* Filters */}
        <div className="flex gap-3 flex-wrap" data-testid="job-selector-filters">
          <div className="relative w-full md:flex-1 md:min-w-[150px]">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <Input
              placeholder="Filter by customer..."
              value={customerFilter}
              onChange={(e) => setCustomerFilter(e.target.value)}
              className="pl-9 min-h-[44px] text-sm md:min-h-0 md:h-auto md:text-sm"
              data-testid="job-filter-customer"
            />
          </div>
          <div className="relative w-full md:flex-1 md:min-w-[150px]">
            <Input
              placeholder="Filter by city/zip..."
              value={cityFilter}
              onChange={(e) => setCityFilter(e.target.value)}
              className="min-h-[44px] text-sm md:min-h-0 md:h-auto md:text-sm"
              data-testid="job-filter-city"
            />
          </div>
          <Select value={jobTypeFilter} onValueChange={setJobTypeFilter}>
            <SelectTrigger className="w-full min-h-[44px] text-sm md:w-[180px] md:min-h-0 md:h-auto md:text-sm" data-testid="job-filter-type">
              <SelectValue placeholder="Job type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Types</SelectItem>
              {jobTypes.map((type) => (
                <SelectItem key={type} value={type}>
                  {type}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Job list */}
        <div className="flex-1 overflow-y-auto border rounded-lg" data-testid="job-selector-list">
          {isLoading ? (
            <div className="flex items-center justify-center h-32">
              <LoadingSpinner />
            </div>
          ) : filteredJobs.length === 0 ? (
            <div className="p-8 text-center text-slate-500 text-sm">
              No unscheduled jobs found
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-slate-50 sticky top-0">
                <tr>
                  <th className="p-3 text-left w-10">
                    <Checkbox
                      checked={
                        filteredJobs.length > 0 &&
                        selectedJobIds.size === filteredJobs.length
                      }
                      onCheckedChange={toggleAll}
                      data-testid="job-select-all"
                    />
                  </th>
                  <th className="p-3 text-left font-medium text-slate-600">Customer</th>
                  <th className="p-3 text-left font-medium text-slate-600">Job Type</th>
                  <th className="p-3 text-left font-medium text-slate-600">City</th>
                  <th className="p-3 text-left font-medium text-slate-600">Priority</th>
                </tr>
              </thead>
              <tbody>
                {filteredJobs.map((job: JobReadyToSchedule) => (
                  <tr
                    key={job.job_id}
                    className="border-t border-slate-100 hover:bg-slate-50 cursor-pointer"
                    onClick={() => toggleJob(job.job_id)}
                    data-testid={`job-row-${job.job_id}`}
                  >
                    <td className="p-3">
                      <Checkbox
                        checked={selectedJobIds.has(job.job_id)}
                        onCheckedChange={() => toggleJob(job.job_id)}
                      />
                    </td>
                    <td className="p-3 font-medium text-slate-800">
                      {job.customer_name}
                    </td>
                    <td className="p-3 text-slate-600">{job.job_type}</td>
                    <td className="p-3 text-slate-600">{job.city}</td>
                    <td className="p-3 text-slate-600">{job.priority}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Footer */}
        <div className="flex flex-col gap-2 pt-3 border-t md:flex-row md:items-center md:justify-between">
          <span className="text-sm text-slate-500 text-center md:text-left">
            {selectedJobIds.size} of {filteredJobs.length} selected
          </span>
          <Button
            onClick={handleAddToSchedule}
            disabled={selectedJobIds.size === 0 || createAppointment.isPending}
            data-testid="add-to-schedule-btn"
            className="w-full min-h-[48px] text-sm bg-teal-500 hover:bg-teal-600 text-white md:w-auto md:min-h-0 md:h-auto md:text-sm"
          >
            <CalendarPlus className="mr-2 h-4 w-4" />
            {createAppointment.isPending
              ? 'Adding...'
              : `Add to Schedule (${selectedJobIds.size})`}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
