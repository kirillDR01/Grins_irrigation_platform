/**
 * Job Selection Controls component.
 * Provides "Select All" and "Deselect All" text links for job selection.
 */

interface JobSelectionControlsProps {
  jobIds: string[];
  excludedJobIds: Set<string>;
  onSelectAll: () => void;
  onDeselectAll: () => void;
}

export function JobSelectionControls({
  jobIds,
  excludedJobIds,
  onSelectAll,
  onDeselectAll,
}: JobSelectionControlsProps) {
  const selectedCount = jobIds.filter(id => !excludedJobIds.has(id)).length;
  const totalCount = jobIds.length;

  if (totalCount === 0) {
    return null;
  }

  return (
    <div className="flex items-center gap-3" data-testid="job-selection-controls">
      <span className="text-sm text-muted-foreground">
        {selectedCount} of {totalCount} selected
      </span>
      <button
        type="button"
        onClick={onSelectAll}
        className="text-sm text-blue-600 hover:underline"
        data-testid="select-all-btn"
      >
        Select All
      </button>
      <button
        type="button"
        onClick={onDeselectAll}
        className="text-sm text-blue-600 hover:underline"
        data-testid="deselect-all-btn"
      >
        Deselect All
      </button>
    </div>
  );
}
