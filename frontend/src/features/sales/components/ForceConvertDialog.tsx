import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

interface ForceConvertDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  isPending: boolean;
  onConfirm: () => void;
}

export function ForceConvertDialog({
  open,
  onOpenChange,
  isPending,
  onConfirm,
}: ForceConvertDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="force-convert-dialog">
        <DialogHeader>
          <DialogTitle>Force Convert to Job?</DialogTitle>
          <DialogDescription>
            No customer signature is on file. Converting without a signature
            will be logged as an override. Continue?
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button
            variant="outline"
            data-testid="cancel-force-convert-btn"
            onClick={() => onOpenChange(false)}
            disabled={isPending}
          >
            Cancel
          </Button>
          <Button
            data-testid="confirm-force-convert-btn"
            onClick={onConfirm}
            disabled={isPending}
          >
            {isPending ? 'Converting…' : 'Force Convert'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
