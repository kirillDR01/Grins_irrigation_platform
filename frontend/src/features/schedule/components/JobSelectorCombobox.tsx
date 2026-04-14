/**
 * Searchable combobox for selecting a job during appointment creation.
 * Replaces the plain <select> dropdown with rich job info display.
 *
 * Req 11.1: Customer name as primary text
 * Req 11.2: Searchable by customer name, job type, or address
 * Req 11.3: Customer address in each option
 * Req 11.4: Property tags as small badges
 * Req 11.5: Service preference notes as hint line
 * Req 11.6: Sort by Week Of (soonest first), customer name, or area
 */

import { useState, useMemo, useRef, useEffect } from 'react';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { ChevronsUpDown, Search, Check, ArrowUpDown } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Job } from '@/features/jobs/types';
import { formatJobType } from '@/features/jobs/types';

type SortOption = 'week_of' | 'customer_name' | 'area';

interface JobSelectorComboboxProps {
  jobs: Job[];
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  isLoading?: boolean;
}

/** Format the Week Of date as "M/D" from target_start_date */
function formatWeekOf(targetStartDate: string | null): string {
  if (!targetStartDate) return '';
  try {
    const [, month, day] = targetStartDate.split('-').map(Number);
    return `${month}/${day}`;
  } catch {
    return '';
  }
}

/** Build the primary display label for a job */
function getJobLabel(job: Job): string {
  const name = job.customer_name || 'Unknown Customer';
  const type = formatJobType(job.job_type);
  const weekOf = formatWeekOf(job.target_start_date);
  const weekPart = weekOf ? ` (Week of ${weekOf})` : '';
  return `${name} — ${type}${weekPart}`;
}

/** Get a short address string */
function getShortAddress(job: Job): string {
  if (job.customer_address) return job.customer_address;
  const parts = [job.property_address, job.property_city].filter(Boolean);
  return parts.join(', ') || '';
}

/** Build property tag list */
function getPropertyTags(job: Job): string[] {
  if (job.property_tags && job.property_tags.length > 0) return job.property_tags;
  const tags: string[] = [];
  if (job.property_type === 'residential') tags.push('Residential');
  if (job.property_type === 'commercial') tags.push('Commercial');
  if (job.property_is_hoa) tags.push('HOA');
  if (job.property_is_subscription) tags.push('Subscription');
  return tags;
}

export function JobSelectorCombobox({
  jobs,
  value,
  onChange,
  disabled = false,
  isLoading = false,
}: JobSelectorComboboxProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [sortBy, setSortBy] = useState<SortOption>('week_of');
  const inputRef = useRef<HTMLInputElement>(null);

  // Focus search input when popover opens
  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 0);
    }
  }, [open]);

  // Sort jobs
  const sortedJobs = useMemo(() => {
    const sorted = [...jobs];
    switch (sortBy) {
      case 'week_of':
        sorted.sort((a, b) => {
          const dateA = a.target_start_date || '9999-12-31';
          const dateB = b.target_start_date || '9999-12-31';
          return dateA.localeCompare(dateB);
        });
        break;
      case 'customer_name':
        sorted.sort((a, b) =>
          (a.customer_name || '').localeCompare(b.customer_name || '')
        );
        break;
      case 'area':
        sorted.sort((a, b) => {
          const cityA = a.property_city || '';
          const cityB = b.property_city || '';
          return cityA.localeCompare(cityB);
        });
        break;
    }
    return sorted;
  }, [jobs, sortBy]);

  // Filter by search term
  const filteredJobs = useMemo(() => {
    if (!search.trim()) return sortedJobs;
    const q = search.toLowerCase();
    return sortedJobs.filter((job) => {
      const name = (job.customer_name || '').toLowerCase();
      const type = job.job_type.toLowerCase();
      const addr = getShortAddress(job).toLowerCase();
      return name.includes(q) || type.includes(q) || addr.includes(q);
    });
  }, [sortedJobs, search]);

  // Find selected job for display
  const selectedJob = jobs.find((j) => j.id === value);

  const sortLabels: Record<SortOption, string> = {
    week_of: 'Week Of',
    customer_name: 'Customer',
    area: 'Area',
  };

  const cycleSortOption = () => {
    const options: SortOption[] = ['week_of', 'customer_name', 'area'];
    const idx = options.indexOf(sortBy);
    setSortBy(options[(idx + 1) % options.length]);
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          disabled={disabled}
          className={cn(
            'w-full justify-between font-normal text-left h-auto min-h-[40px] py-2',
            !value && 'text-muted-foreground'
          )}
          data-testid="job-combobox-trigger"
        >
          <span className="truncate">
            {isLoading
              ? 'Loading jobs...'
              : selectedJob
                ? getJobLabel(selectedJob)
                : 'Select a job...'}
          </span>
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent
        className="w-[var(--radix-popover-trigger-width)] p-0"
        align="start"
        sideOffset={4}
      >
        {/* Search + Sort header */}
        <div className="flex items-center gap-2 p-2 border-b border-slate-100">
          <div className="relative flex-1">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400" />
            <Input
              ref={inputRef}
              placeholder="Search by name, type, or address..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-8 h-8 text-sm"
              data-testid="job-combobox-search"
            />
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="h-8 px-2 text-xs text-slate-500 shrink-0"
            onClick={cycleSortOption}
            type="button"
            data-testid="job-combobox-sort"
          >
            <ArrowUpDown className="h-3 w-3 mr-1" />
            {sortLabels[sortBy]}
          </Button>
        </div>

        {/* Job list */}
        <ScrollArea className="max-h-[300px]">
          {filteredJobs.length === 0 ? (
            <div className="p-4 text-center text-sm text-slate-500">
              {jobs.length === 0 ? 'No jobs ready to schedule' : 'No matching jobs'}
            </div>
          ) : (
            <div className="p-1" role="listbox" data-testid="job-combobox-list">
              {filteredJobs.map((job) => {
                const isSelected = job.id === value;
                const address = getShortAddress(job);
                const tags = getPropertyTags(job);
                const prefNotes = job.service_preference_notes;

                return (
                  <button
                    key={job.id}
                    type="button"
                    role="option"
                    aria-selected={isSelected}
                    className={cn(
                      'w-full text-left rounded-md px-2 py-2 cursor-pointer transition-colors',
                      'hover:bg-slate-50 focus:bg-slate-50 focus:outline-none',
                      isSelected && 'bg-teal-50'
                    )}
                    onClick={() => {
                      onChange(job.id);
                      setOpen(false);
                      setSearch('');
                    }}
                    data-testid={`job-option-${job.id}`}
                  >
                    <div className="flex items-start gap-2">
                      <div className="flex-1 min-w-0">
                        {/* Primary: Customer Name — Job Type (Week of M/D) */}
                        <div className="flex items-center gap-1.5">
                          <span className="text-sm font-medium text-slate-800 truncate">
                            {getJobLabel(job)}
                          </span>
                        </div>

                        {/* Secondary: Address */}
                        {address && (
                          <p className="text-xs text-slate-500 mt-0.5 truncate">
                            {address}
                          </p>
                        )}

                        {/* Tags + Preference notes row */}
                        <div className="flex flex-wrap items-center gap-1 mt-1">
                          {tags.map((tag) => (
                            <Badge
                              key={tag}
                              variant="outline"
                              className="text-[10px] px-1.5 py-0 h-4 font-normal"
                            >
                              {tag}
                            </Badge>
                          ))}
                        </div>

                        {/* Service preference notes hint */}
                        {prefNotes && (
                          <p className="text-[11px] text-amber-600 mt-0.5 italic truncate">
                            {prefNotes}
                          </p>
                        )}
                      </div>

                      {/* Check icon for selected */}
                      {isSelected && (
                        <Check className="h-4 w-4 text-teal-600 shrink-0 mt-0.5" />
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </ScrollArea>
      </PopoverContent>
    </Popover>
  );
}
