// @ts-nocheck — pre-existing TS errors documented in bughunt/2026-04-29-pre-existing-tsc-errors.md
import { RefreshCw } from 'lucide-react';
import { toast } from 'sonner';
import { useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { useSyncStatus, useTriggerSync } from '@/features/work-requests/hooks/useWorkRequests';
import { leadKeys } from '../hooks/useLeads';
import { SyncStatusBar } from '@/features/work-requests/components/SyncStatusBar';

export function SheetsSync() {
  const queryClient = useQueryClient();
  const triggerSync = useTriggerSync();
  const { data: status } = useSyncStatus();

  const handleSync = () => {
    triggerSync.mutate(undefined, {
      onSuccess: (data) => {
        queryClient.invalidateQueries({ queryKey: leadKeys.lists() });
        if (data.new_rows_imported > 0) {
          toast.success('Sync Complete', {
            description: `${data.new_rows_imported} new row(s) imported from Google Sheets.`,
          });
        } else {
          toast.info('No New Data', {
            description: 'Google Sheet is already up to date.',
          });
        }
      },
      onError: () => {
        toast.error('Sync Failed', {
          description: 'Could not sync Google Sheets. Please try again.',
        });
      },
    });
  };

  return (
    <div className="flex items-center gap-3">
      <SyncStatusBar />
      <Button
        variant="outline"
        size="sm"
        onClick={handleSync}
        disabled={triggerSync.isPending}
        data-testid="leads-sync-sheets-btn"
      >
        <RefreshCw className={`h-4 w-4 mr-2 ${triggerSync.isPending ? 'animate-spin' : ''}`} />
        {triggerSync.isPending ? 'Syncing...' : 'Sync Sheets'}
      </Button>
    </div>
  );
}
