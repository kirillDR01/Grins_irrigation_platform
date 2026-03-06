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
import type {
  WorkRequestListParams,
  ProcessingStatus,
  SheetClientType,
} from '../types';
import { PROCESSING_STATUS_LABELS, CLIENT_TYPE_LABELS } from '../types';

interface WorkRequestFiltersProps {
  params: WorkRequestListParams;
  onChange: (params: Partial<WorkRequestListParams>) => void;
}

export function WorkRequestFilters({
  params,
  onChange,
}: WorkRequestFiltersProps) {
  const [searchInput, setSearchInput] = useState(params.search ?? '');
  const debouncedSearch = useDebounce(searchInput, 300);

  useEffect(() => {
    const currentSearch = params.search ?? '';
    if (debouncedSearch !== currentSearch) {
      onChange({ search: debouncedSearch || undefined, page: 1 });
    }
  }, [debouncedSearch]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleStatusChange = useCallback(
    (value: string) => {
      onChange({
        processing_status:
          value === 'all' ? undefined : (value as ProcessingStatus),
        page: 1,
      });
    },
    [onChange]
  );

  const handleClientTypeChange = useCallback(
    (value: string) => {
      onChange({
        client_type: value === 'all' ? undefined : (value as SheetClientType),
        page: 1,
      });
    },
    [onChange]
  );

  return (
    <div className="flex flex-wrap items-center gap-3">
      {/* Search Input */}
      <div className="relative flex-1 min-w-[200px] max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
        <Input
          placeholder="Search by name, phone, or email..."
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          className="pl-10 bg-slate-50 border-slate-200 rounded-lg text-sm"
          data-testid="search-input"
        />
      </div>

      {/* Processing Status Filter */}
      <Select
        value={params.processing_status ?? 'all'}
        onValueChange={handleStatusChange}
      >
        <SelectTrigger
          className="w-[170px] bg-white border-slate-200 rounded-lg text-sm"
          data-testid="filter-processing-status"
        >
          <SelectValue placeholder="All Statuses" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All Statuses</SelectItem>
          {(Object.keys(PROCESSING_STATUS_LABELS) as ProcessingStatus[]).map(
            (status) => (
              <SelectItem key={status} value={status}>
                {PROCESSING_STATUS_LABELS[status]}
              </SelectItem>
            )
          )}
        </SelectContent>
      </Select>

      {/* Client Type Filter */}
      <Select
        value={params.client_type ?? 'all'}
        onValueChange={handleClientTypeChange}
      >
        <SelectTrigger
          className="w-[160px] bg-white border-slate-200 rounded-lg text-sm"
          data-testid="filter-client-type"
        >
          <SelectValue placeholder="All Types" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All Types</SelectItem>
          {(Object.keys(CLIENT_TYPE_LABELS) as SheetClientType[]).map(
            (type) => (
              <SelectItem key={type} value={type}>
                {CLIENT_TYPE_LABELS[type]}
              </SelectItem>
            )
          )}
        </SelectContent>
      </Select>
    </div>
  );
}
