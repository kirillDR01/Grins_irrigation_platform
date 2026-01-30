/**
 * ClearResultsButton component.
 * Button to clear schedule generation results with confirmation dialog.
 */

import { useState } from 'react';
import { Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

interface ClearResultsButtonProps {
  onClear: () => void;
}

export function ClearResultsButton({ onClear }: ClearResultsButtonProps) {
  const [showDialog, setShowDialog] = useState(false);

  const handleConfirm = () => {
    onClear();
    setShowDialog(false);
  };

  return (
    <>
      <Button
        variant="secondary"
        size="sm"
        onClick={() => setShowDialog(true)}
        data-testid="clear-results-btn"
        className="hover:bg-red-50 hover:text-red-600 hover:border-red-200"
      >
        <Trash2 className="mr-2 h-4 w-4" />
        Clear Results
      </Button>

      <Dialog open={showDialog} onOpenChange={setShowDialog}>
        <DialogContent data-testid="clear-confirmation-dialog">
          <DialogHeader>
            <DialogTitle>Clear Schedule Results?</DialogTitle>
            <DialogDescription>
              This will remove all generated schedule results. You can regenerate the schedule at any time.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="secondary"
              onClick={() => setShowDialog(false)}
              data-testid="cancel-clear-btn"
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleConfirm}
              data-testid="confirm-clear-btn"
            >
              Clear Results
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
