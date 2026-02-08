import { useState, useCallback, useEffect } from 'react';
import { Search } from 'lucide-react';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useDebounce } from '@/shared/hooks/useDebounce';
import type { LeadListParams, LeadStatus, LeadSituation } from '../types';
import { LEAD_STATUS_LABELS, LEAD_SITUATION_LABELS } from '../types';

interface LeadFiltersProps {
  /** Current filter parameters */
  params: LeadListParams;
  /** Callback when any filter changes */
  onChange: (params: Partial<LeadListParams>) => void;
}

export function LeadFilters({ params, onChange }: LeadFiltersProps) {
  const [searchInput, setSearchInput] = useState(params.search ?? '');
  const debouncedSearch = useDebounce(searchInput, 300);

  // Sync debounced search value to parent
  useEffect(() => {
    const currentSearch = params.search ?? '';
    if (debouncedSearch !== currentSearch) {
      onChange({ search: debouncedSearch || undefined, page: 1 });
    }
  }, [debouncedSearch]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleStatusChange = useCallback(
    (value: string) => {
      onChange({
        status: value === 'all' ? undefined : (value as LeadStatus),
        page: 1,
      });
    },
    [onChange]
  );

  const handleSituationChange = useCallback(
    (value: string) => {
      onChange({
        situation: value === 'all' ? undefined : (value as LeadSituation),
        page: 1,
      });
    },
    [onChange]
  );

  const handleDateFromChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      onChange({ date_from: e.target.value || undefined, page: 1 });
    },
    [onChange]
  );

  const handleDateToChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      onChange({ date_to: e.target.value || undefined, page: 1 });
    },
    [onChange]
  );

  return (
    <div
      className="flex flex-wrap items-center gap-3"
      data-testid="lead-filters"
    >
      {/* Search Input */}
      <div className="relative flex-1 min-w-[200px] max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
        <Input
          placeholder="Search by name or phone..."
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          className="pl-10 bg-slate-50 border-slate-200 rounded-lg text-sm"
          data-testid="lead-search-input"
        />
      </div>

      {/* Status Filter */}
      <Select
        value={params.status ?? 'all'}
        onValueChange={handleStatusChange}
      >
        <SelectTrigger
          className="w-[160px] bg-white border-slate-200 rounded-lg text-sm"
          data-testid="lead-status-filter"
        >
          <SelectValue placeholder="All Statuses" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All Statuses</SelectItem>
          {(Object.keys(LEAD_STATUS_LABELS) as LeadStatus[]).map((status) => (
            <SelectItem key={status} value={status}>
              {LEAD_STATUS_LABELS[status]}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {/* Situation Filter */}
      <Select
        value={params.situation ?? 'all'}
        onValueChange={handleSituationChange}
      >
        <SelectTrigger
          className="w-[170px] bg-white border-slate-200 rounded-lg text-sm"
          data-testid="lead-situation-filter"
        >
          <SelectValue placeholder="All Situations" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All Situations</SelectItem>
          {(Object.keys(LEAD_SITUATION_LABELS) as LeadSituation[]).map(
            (situation) => (
              <SelectItem key={situation} value={situation}>
                {LEAD_SITUATION_LABELS[situation]}
              </SelectItem>
            )
          )}
        </SelectContent>
      </Select>

      {/* Date Range */}
      <div className="flex items-center gap-2">
        <Input
          type="date"
          value={params.date_from ?? ''}
          onChange={handleDateFromChange}
          className="w-[150px] bg-white border-slate-200 rounded-lg text-sm"
          data-testid="lead-date-from"
        />
        <span className="text-slate-400 text-sm">to</span>
        <Input
          type="date"
          value={params.date_to ?? ''}
          onChange={handleDateToChange}
          className="w-[150px] bg-white border-slate-200 rounded-lg text-sm"
          data-testid="lead-date-to"
        />
      </div>
    </div>
  );
}
