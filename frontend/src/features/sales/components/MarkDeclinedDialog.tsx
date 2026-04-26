import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

interface MarkDeclinedDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: (reason: string) => void;
  isPending?: boolean;
}

export function MarkDeclinedDialog({
  open,
  onOpenChange,
  onConfirm,
  isPending,
}: MarkDeclinedDialogProps) {
  const [reason, setReason] = useState('');

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        if (!o) setReason('');
        onOpenChange(o);
      }}
    >
      <DialogContent data-testid="mark-declined-dialog">
        <DialogHeader>
          <DialogTitle>Mark as Declined?</DialogTitle>
          <DialogDescription>
            Capture the reason the customer declined. This will close the
            sales entry as lost.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-2">
          <Label htmlFor="decline-reason">Reason (required)</Label>
          <Textarea
            id="decline-reason"
            data-testid="decline-reason-input"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="e.g. Went with competitor"
            rows={3}
          />
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            data-testid="confirm-mark-declined-btn"
            onClick={() => onConfirm(reason.trim())}
            disabled={isPending || !reason.trim()}
          >
            {isPending ? 'Saving…' : 'Mark Declined'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
