import { useState } from 'react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  useAdvanceSalesEntry,
  useForceConvertToJob,
  useMarkSalesLost,
} from '../hooks/useSalesPipeline';
import {
  SALES_STATUS_CONFIG,
  TERMINAL_STATUSES,
  type SalesEntry,
} from '../types/pipeline';

interface StatusActionButtonProps {
  entry: SalesEntry;
}

export function StatusActionButton({ entry }: StatusActionButtonProps) {
  const advance = useAdvanceSalesEntry();
  const forceConvert = useForceConvertToJob();
  const markLost = useMarkSalesLost();
  const [showForceConfirm, setShowForceConfirm] = useState(false);
  const [showLostConfirm, setShowLostConfirm] = useState(false);

  const config = SALES_STATUS_CONFIG[entry.status];
  const isTerminal = TERMINAL_STATUSES.includes(entry.status);

  if (isTerminal) return null;

  const handleAdvance = (e: React.MouseEvent) => {
    e.stopPropagation();
    advance.mutate(entry.id, {
      onSuccess: () => {
        toast.success('Status advanced');
      },
      onError: (err) => {
        const msg =
          (err as { response?: { data?: { detail?: string } } })?.response
            ?.data?.detail ?? 'Failed to advance';
        if (msg.includes('signature')) {
          setShowForceConfirm(true);
        } else {
          toast.error('Error', { description: msg });
        }
      },
    });
  };

  const handleForceConvert = () => {
    forceConvert.mutate(entry.id, {
      onSuccess: () => {
        toast.success('Converted to job (forced)');
        setShowForceConfirm(false);
      },
      onError: () => {
        toast.error('Failed to force convert');
        setShowForceConfirm(false);
      },
    });
  };

  const handleMarkLost = (e: React.MouseEvent) => {
    e.stopPropagation();
    setShowLostConfirm(true);
  };

  const confirmMarkLost = () => {
    markLost.mutate(
      { id: entry.id },
      {
        onSuccess: () => {
          toast.success('Marked as lost');
          setShowLostConfirm(false);
        },
        onError: () => {
          toast.error('Failed to mark as lost');
          setShowLostConfirm(false);
        },
      },
    );
  };

  return (
    <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
      {config.action && (
        <Button
          size="sm"
          variant="outline"
          onClick={handleAdvance}
          disabled={advance.isPending}
          data-testid={`advance-btn-${entry.id}`}
        >
          {advance.isPending ? 'Processing...' : config.action}
        </Button>
      )}
      <Button
        size="sm"
        variant="ghost"
        className="text-red-500 hover:text-red-700 hover:bg-red-50"
        onClick={handleMarkLost}
        disabled={markLost.isPending}
        data-testid={`mark-lost-btn-${entry.id}`}
      >
        Mark Lost
      </Button>

      {/* Force convert confirmation */}
      <Dialog open={showForceConfirm} onOpenChange={setShowForceConfirm}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Force Convert to Job?</DialogTitle>
            <DialogDescription>
              No customer signature is on file. Converting without a signature
              will be logged as an override. Continue?
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowForceConfirm(false)}>
              Cancel
            </Button>
            <Button onClick={handleForceConvert}>Force Convert</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Mark lost confirmation */}
      <Dialog open={showLostConfirm} onOpenChange={setShowLostConfirm}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Mark as Lost?</DialogTitle>
            <DialogDescription>
              This will close the sales entry as lost. This action cannot be
              undone via the action button.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowLostConfirm(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={confirmMarkLost}
            >
              Mark Lost
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
