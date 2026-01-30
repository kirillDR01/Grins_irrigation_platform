/**
 * Job Selection Controls component.
 * Provides select all checkbox, selection count, filter buttons, and clear selection.
 */

import { Checkbox } from '@/components/ui/checkbox';
import { Button } from '@/components/ui/button';

type FilterType = 'all' | 'ready' | 'needs_estimate';

interface JobSelectionControlsProps {
  jobIds: string[];
  excludedJobIds: Set<string>;
  onSelectAll: () => void;
  onDeselectAll: () => void;
  activeFilter?: FilterType;
  onFilterChange?: (filter: FilterType) => void;
}

export function JobSelectionControls({
  jobIds,
  excludedJobIds,
  onSelectAll,
  onDeselectAll,
  activeFilter = 'all',
  onFilterChange,
}: JobSelectionControlsProps) {
  const selectedCount = jobIds.filter(id => !excludedJobIds.has(id)).length;
  const totalCount = jobIds.length;
  const allSelected = selectedCount === totalCount && totalCount > 0;
  const someSelected = selectedCount > 0 && selectedCount < totalCount;

  if (totalCount === 0) {
    return null;
  }

  const handleSelectAllChange = (checked: boolean | 'indeterminate') => {
    if (checked === true) {
      onSelectAll();
    } else {
      onDeselectAll();
    }
  };

  return (
    <div 
      className="flex items-center gap-4 p-4 bg-slate-50 rounded-xl" 
      data-testid="job-selection-controls"
    >
      {/* Select All Checkbox */}
      <div className="flex items-center gap-2">
        <Checkbox
          id="select-all"
          checked={allSelected ? true : someSelected ? 'indeterminate' : false}
          onCheckedChange={handleSelectAllChange}
          data-testid="select-all-checkbox"
          className="data-[state=checked]:bg-teal-500 data-[state=checked]:border-teal-500"
        />
        <label 
          htmlFor="select-all" 
          className="text-sm font-medium text-slate-700 cursor-pointer"
        >
          Select All
        </label>
      </div>

      {/* Selection Count */}
      <span className="text-sm text-slate-600" data-testid="selection-count">
        {selectedCount} of {totalCount} jobs selected
      </span>

      {/* Filter Buttons */}
      {onFilterChange && (
        <div className="flex items-center gap-2 ml-auto">
          <Button
            type="button"
            variant={activeFilter === 'all' ? 'default' : 'secondary'}
            size="sm"
            onClick={() => onFilterChange('all')}
            data-testid="filter-all-btn"
            className={activeFilter === 'all' 
              ? 'bg-teal-500 hover:bg-teal-600 text-white' 
              : 'bg-white hover:bg-slate-50 border border-slate-200 text-slate-700'
            }
          >
            All
          </Button>
          <Button
            type="button"
            variant={activeFilter === 'ready' ? 'default' : 'secondary'}
            size="sm"
            onClick={() => onFilterChange('ready')}
            data-testid="filter-ready-btn"
            className={activeFilter === 'ready' 
              ? 'bg-teal-500 hover:bg-teal-600 text-white' 
              : 'bg-white hover:bg-slate-50 border border-slate-200 text-slate-700'
            }
          >
            Ready
          </Button>
          <Button
            type="button"
            variant={activeFilter === 'needs_estimate' ? 'default' : 'secondary'}
            size="sm"
            onClick={() => onFilterChange('needs_estimate')}
            data-testid="filter-needs-estimate-btn"
            className={activeFilter === 'needs_estimate' 
              ? 'bg-teal-500 hover:bg-teal-600 text-white' 
              : 'bg-white hover:bg-slate-50 border border-slate-200 text-slate-700'
            }
          >
            Needs Estimate
          </Button>
        </div>
      )}

      {/* Clear Selection Button */}
      {selectedCount > 0 && (
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={onDeselectAll}
          data-testid="clear-selection-btn"
          className="text-slate-500 hover:text-slate-700 hover:bg-slate-100"
        >
          Clear Selection
        </Button>
      )}

      {/* Legacy buttons for backward compatibility */}
      <button
        type="button"
        onClick={onSelectAll}
        className="hidden"
        data-testid="select-all-btn"
      >
        Select All
      </button>
      <button
        type="button"
        onClick={onDeselectAll}
        className="hidden"
        data-testid="deselect-all-btn"
      >
        Deselect All
      </button>
    </div>
  );
}
