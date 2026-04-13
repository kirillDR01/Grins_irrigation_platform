import { useState, useCallback, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Filter, X, ChevronDown, ChevronUp } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/shared/components/ui/badge';
import { cn } from '@/shared/utils/cn';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

export type FilterAxisType =
  | 'text'
  | 'select'
  | 'multi-select'
  | 'date-range'
  | 'number-range';

export interface FilterOption {
  value: string;
  label: string;
}

export interface FilterAxis {
  /** URL param key (also used as state key) */
  key: string;
  label: string;
  type: FilterAxisType;
  /** For select / multi-select */
  options?: FilterOption[];
  /** Placeholder text */
  placeholder?: string;
  /** For date-range: keys for from/to params (defaults to `${key}_from` / `${key}_to`) */
  fromKey?: string;
  toKey?: string;
  /** For number-range: keys for min/max params */
  minKey?: string;
  maxKey?: string;
}

export interface FilterState {
  [key: string]: string;
}

export interface FilterPanelProps {
  axes: FilterAxis[];
  className?: string;
  /** Controlled mode: external state */
  value?: FilterState;
  onChange?: (state: FilterState) => void;
  /** If true, persist to URL search params (default true) */
  persistToUrl?: boolean;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function resolvedKeys(axis: FilterAxis) {
  if (axis.type === 'date-range') {
    return {
      from: axis.fromKey ?? `${axis.key}_from`,
      to: axis.toKey ?? `${axis.key}_to`,
    };
  }
  if (axis.type === 'number-range') {
    return {
      min: axis.minKey ?? `${axis.key}_min`,
      max: axis.maxKey ?? `${axis.key}_max`,
    };
  }
  return { single: axis.key };
}

function allParamKeys(axes: FilterAxis[]): string[] {
  const keys: string[] = [];
  for (const a of axes) {
    const r = resolvedKeys(a);
    if ('single' in r) keys.push(r.single);
    if ('from' in r) keys.push(r.from, r.to);
    if ('min' in r) keys.push(r.min, r.max);
  }
  return keys;
}

function labelForValue(axis: FilterAxis, val: string): string {
  if (axis.options) {
    const opt = axis.options.find((o) => o.value === val);
    if (opt) return opt.label;
  }
  return val;
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function FilterPanel({
  axes,
  className,
  value: controlledValue,
  onChange: controlledOnChange,
  persistToUrl = true,
}: FilterPanelProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  const [expanded, setExpanded] = useState(false);

  // Derive state from URL or controlled value
  const filterState: FilterState = useMemo(() => {
    if (controlledValue) return controlledValue;
    const state: FilterState = {};
    for (const key of allParamKeys(axes)) {
      const v = searchParams.get(key);
      if (v) state[key] = v;
    }
    return state;
  }, [controlledValue, searchParams, axes]);

  const setFilter = useCallback(
    (key: string, val: string) => {
      if (controlledOnChange) {
        const next = { ...filterState };
        if (val) next[key] = val;
        else delete next[key];
        controlledOnChange(next);
      }
      if (persistToUrl) {
        setSearchParams((prev) => {
          const next = new URLSearchParams(prev);
          if (val) next.set(key, val);
          else next.delete(key);
          return next;
        });
      }
    },
    [controlledOnChange, filterState, persistToUrl, setSearchParams],
  );

  const clearAll = useCallback(() => {
    if (controlledOnChange) controlledOnChange({});
    if (persistToUrl) {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        for (const key of allParamKeys(axes)) next.delete(key);
        return next;
      });
    }
  }, [axes, controlledOnChange, persistToUrl, setSearchParams]);

  const removeChip = useCallback(
    (key: string) => setFilter(key, ''),
    [setFilter],
  );

  // Active filter chips
  const activeChips = useMemo(() => {
    const chips: { key: string; label: string; displayValue: string }[] = [];
    for (const axis of axes) {
      const r = resolvedKeys(axis);
      if ('single' in r && filterState[r.single]) {
        chips.push({
          key: r.single,
          label: axis.label,
          displayValue: labelForValue(axis, filterState[r.single]),
        });
      }
      if ('from' in r) {
        if (filterState[r.from])
          chips.push({ key: r.from, label: `${axis.label} from`, displayValue: filterState[r.from] });
        if (filterState[r.to])
          chips.push({ key: r.to, label: `${axis.label} to`, displayValue: filterState[r.to] });
      }
      if ('min' in r) {
        if (filterState[r.min])
          chips.push({ key: r.min, label: `${axis.label} min`, displayValue: filterState[r.min] });
        if (filterState[r.max])
          chips.push({ key: r.max, label: `${axis.label} max`, displayValue: filterState[r.max] });
      }
    }
    return chips;
  }, [axes, filterState]);

  const hasActiveFilters = activeChips.length > 0;

  return (
    <div className={cn('space-y-3', className)} data-testid="filter-panel">
      {/* Toggle + chip bar */}
      <div className="flex flex-wrap items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setExpanded((p) => !p)}
          className="bg-white hover:bg-slate-50 border-slate-200 text-slate-700 rounded-lg"
          data-testid="filter-toggle"
        >
          <Filter className="h-4 w-4 mr-2" />
          Filters
          {hasActiveFilters && (
            <Badge variant="teal" className="ml-2 px-1.5 py-0 text-[10px]">
              {activeChips.length}
            </Badge>
          )}
          {expanded ? (
            <ChevronUp className="h-3 w-3 ml-1" />
          ) : (
            <ChevronDown className="h-3 w-3 ml-1" />
          )}
        </Button>

        {/* Active filter chips */}
        {activeChips.map((chip) => (
          <Badge
            key={chip.key}
            variant="info-outline"
            className="gap-1 cursor-default"
            data-testid={`filter-chip-${chip.key}`}
          >
            <span className="text-slate-500">{chip.label}:</span> {chip.displayValue}
            <button
              onClick={() => removeChip(chip.key)}
              className="ml-0.5 hover:text-red-500 transition-colors"
              aria-label={`Remove ${chip.label} filter`}
              data-testid={`remove-filter-${chip.key}`}
            >
              <X className="h-3 w-3" />
            </button>
          </Badge>
        ))}

        {hasActiveFilters && (
          <Button
            variant="ghost"
            size="sm"
            onClick={clearAll}
            className="text-slate-500 hover:text-red-500 text-xs"
            data-testid="clear-all-filters"
          >
            Clear all
          </Button>
        )}
      </div>

      {/* Collapsible filter axes */}
      {expanded && (
        <div
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3 p-4 bg-slate-50 rounded-xl border border-slate-100"
          data-testid="filter-axes"
        >
          {axes.map((axis) => (
            <FilterAxisControl
              key={axis.key}
              axis={axis}
              state={filterState}
              onSet={setFilter}
            />
          ))}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Per-axis control                                                   */
/* ------------------------------------------------------------------ */

function FilterAxisControl({
  axis,
  state,
  onSet,
}: {
  axis: FilterAxis;
  state: FilterState;
  onSet: (key: string, val: string) => void;
}) {
  const r = resolvedKeys(axis);

  if (axis.type === 'text') {
    const key = 'single' in r ? r.single : axis.key;
    return (
      <div className="space-y-1">
        <label className="text-xs font-medium text-slate-500">{axis.label}</label>
        <Input
          value={state[key] ?? ''}
          onChange={(e) => onSet(key, e.target.value)}
          placeholder={axis.placeholder ?? `Filter by ${axis.label.toLowerCase()}`}
          className="h-8 text-sm bg-white"
          data-testid={`filter-${key}`}
        />
      </div>
    );
  }

  if (axis.type === 'select') {
    const key = 'single' in r ? r.single : axis.key;
    return (
      <div className="space-y-1">
        <label className="text-xs font-medium text-slate-500">{axis.label}</label>
        <Select
          value={state[key] ?? ''}
          onValueChange={(v) => onSet(key, v === '__all__' ? '' : v)}
        >
          <SelectTrigger className="h-8 text-sm bg-white" data-testid={`filter-${key}`}>
            <SelectValue placeholder={axis.placeholder ?? 'All'} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="__all__">All</SelectItem>
            {axis.options?.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    );
  }

  if (axis.type === 'multi-select') {
    const key = 'single' in r ? r.single : axis.key;
    const selected = state[key] ? state[key].split(',') : [];
    const toggle = (val: string) => {
      const next = selected.includes(val)
        ? selected.filter((v) => v !== val)
        : [...selected, val];
      onSet(key, next.join(','));
    };
    return (
      <div className="space-y-1">
        <label className="text-xs font-medium text-slate-500">{axis.label}</label>
        <div className="flex flex-wrap gap-1" data-testid={`filter-${key}`}>
          {axis.options?.map((opt) => (
            <button
              key={opt.value}
              onClick={() => toggle(opt.value)}
              className={cn(
                'px-2 py-0.5 rounded-full text-xs border transition-colors',
                selected.includes(opt.value)
                  ? 'bg-teal-50 border-teal-200 text-teal-700'
                  : 'bg-white border-slate-200 text-slate-500 hover:border-slate-300',
              )}
              data-testid={`filter-${key}-${opt.value}`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>
    );
  }

  if (axis.type === 'date-range' && 'from' in r) {
    return (
      <div className="space-y-1">
        <label className="text-xs font-medium text-slate-500">{axis.label}</label>
        <div className="flex items-center gap-1">
          <Input
            type="date"
            value={state[r.from] ?? ''}
            onChange={(e) => onSet(r.from, e.target.value)}
            className="h-8 text-sm bg-white flex-1"
            data-testid={`filter-${r.from}`}
          />
          <span className="text-slate-400 text-xs">–</span>
          <Input
            type="date"
            value={state[r.to] ?? ''}
            onChange={(e) => onSet(r.to, e.target.value)}
            className="h-8 text-sm bg-white flex-1"
            data-testid={`filter-${r.to}`}
          />
        </div>
      </div>
    );
  }

  if (axis.type === 'number-range' && 'min' in r) {
    return (
      <div className="space-y-1">
        <label className="text-xs font-medium text-slate-500">{axis.label}</label>
        <div className="flex items-center gap-1">
          <Input
            type="number"
            value={state[r.min] ?? ''}
            onChange={(e) => onSet(r.min, e.target.value)}
            placeholder="Min"
            className="h-8 text-sm bg-white flex-1"
            data-testid={`filter-${r.min}`}
          />
          <span className="text-slate-400 text-xs">–</span>
          <Input
            type="number"
            value={state[r.max] ?? ''}
            onChange={(e) => onSet(r.max, e.target.value)}
            placeholder="Max"
            className="h-8 text-sm bg-white flex-1"
            data-testid={`filter-${r.max}`}
          />
        </div>
      </div>
    );
  }

  return null;
}
