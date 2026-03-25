import { useState } from 'react';
import { Bell, Loader2 } from 'lucide-react';
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useBulkNotify } from '../hooks';
import { NOTIFICATION_TYPE_CONFIG, type NotificationType } from '../types';

interface BulkNotifyProps {
  selectedInvoiceIds: string[];
  onComplete?: () => void;
}

export function BulkNotify({ selectedInvoiceIds, onComplete }: BulkNotifyProps) {
  const [open, setOpen] = useState(false);
  const [notificationType, setNotificationType] = useState<NotificationType | ''>('');
  const bulkNotify = useBulkNotify();

  const handleSend = async () => {
    if (!notificationType) {
      toast.error('Please select a notification type');
      return;
    }
    try {
      const result = await bulkNotify.mutateAsync({
        invoice_ids: selectedInvoiceIds,
        notification_type: notificationType,
      });
      toast.success('Bulk Notification Complete', {
        description: `Sent: ${result.sent}, Skipped: ${result.skipped}, Failed: ${result.failed}`,
      });
      setOpen(false);
      setNotificationType('');
      onComplete?.();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to send notifications';
      toast.error('Notification Failed', { description: msg });
    }
  };

  return (
    <>
      <Button
        variant="outline"
        size="sm"
        onClick={() => setOpen(true)}
        disabled={selectedInvoiceIds.length === 0}
        data-testid="bulk-notify-btn"
      >
        <Bell className="mr-2 h-4 w-4" />
        Bulk Notify ({selectedInvoiceIds.length})
      </Button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-md" data-testid="bulk-notify-dialog">
          <DialogHeader>
            <DialogTitle>Bulk Notify</DialogTitle>
            <DialogDescription>
              Send notifications for {selectedInvoiceIds.length} selected invoice
              {selectedInvoiceIds.length !== 1 ? 's' : ''}.
              Customers without SMS consent will be skipped.
            </DialogDescription>
          </DialogHeader>

          <div className="py-4">
            <label className="text-sm font-medium text-slate-700 mb-1.5 block">
              Notification Type
            </label>
            <Select
              value={notificationType}
              onValueChange={(v) => setNotificationType(v as NotificationType)}
            >
              <SelectTrigger data-testid="notification-type-selector">
                <SelectValue placeholder="Select notification type..." />
              </SelectTrigger>
              <SelectContent>
                {(Object.entries(NOTIFICATION_TYPE_CONFIG) as [NotificationType, { label: string; description: string }][]).map(
                  ([key, config]) => (
                    <SelectItem key={key} value={key} data-testid={`notify-type-${key}`}>
                      {config.label} — {config.description}
                    </SelectItem>
                  ),
                )}
              </SelectContent>
            </Select>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleSend}
              disabled={bulkNotify.isPending || !notificationType}
              data-testid="send-bulk-notify-btn"
            >
              {bulkNotify.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Bell className="mr-2 h-4 w-4" />
              )}
              Send to {selectedInvoiceIds.length} Invoices
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
