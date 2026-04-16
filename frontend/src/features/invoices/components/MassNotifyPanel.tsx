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
import { Input } from '@/components/ui/input';
import { useMassNotify } from '../hooks';
import { MASS_NOTIFICATION_CONFIG, type MassNotificationType } from '../types';

export function MassNotifyPanel() {
  const [open, setOpen] = useState(false);
  const [notificationType, setNotificationType] = useState<MassNotificationType | ''>('');
  const [dueSoonDays, setDueSoonDays] = useState(7);
  const massNotify = useMassNotify();

  const handleSend = async () => {
    if (!notificationType) return;
    try {
      const result = await massNotify.mutateAsync({
        notification_type: notificationType,
        due_soon_days: dueSoonDays,
      });
      toast.success('Mass Notification Sent', {
        description: `Targeted: ${result.targeted}, Sent: ${result.sent}, Skipped: ${result.skipped}, Failed: ${result.failed}`,
      });
      setOpen(false);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to send mass notifications';
      toast.error('Mass Notification Failed', { description: msg });
    }
  };

  return (
    <>
      <Button
        variant="outline"
        size="sm"
        onClick={() => setOpen(true)}
        data-testid="mass-notify-btn"
      >
        <Bell className="mr-2 h-4 w-4" />
        Mass Notify
      </Button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-md" data-testid="mass-notify-dialog">
          <DialogHeader>
            <DialogTitle>Mass Notify Customers</DialogTitle>
            <DialogDescription>
              Send bulk SMS/email to customers based on invoice criteria.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-1">
              <label className="text-sm font-medium text-slate-700">Notification Type</label>
              <Select
                value={notificationType}
                onValueChange={(v) => setNotificationType(v as MassNotificationType)}
              >
                <SelectTrigger data-testid="mass-notify-type">
                  <SelectValue placeholder="Select type..." />
                </SelectTrigger>
                <SelectContent>
                  {(Object.entries(MASS_NOTIFICATION_CONFIG) as [MassNotificationType, { label: string; description: string }][]).map(
                    ([key, config]) => (
                      <SelectItem key={key} value={key}>
                        {config.label} — {config.description}
                      </SelectItem>
                    ),
                  )}
                </SelectContent>
              </Select>
            </div>

            {notificationType === 'due_soon' && (
              <div className="space-y-1">
                <label className="text-sm font-medium text-slate-700">Days Until Due</label>
                <Input
                  type="number"
                  value={dueSoonDays}
                  onChange={(e) => setDueSoonDays(Number(e.target.value))}
                  min={1}
                  max={90}
                  data-testid="mass-notify-due-soon-days"
                />
              </div>
            )}
            {/* CR-5: lien_eligible option removed — use /invoices?tab=lien-review instead. */}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
            <Button
              onClick={handleSend}
              disabled={massNotify.isPending || !notificationType}
              data-testid="send-mass-notify-btn"
            >
              {massNotify.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Bell className="mr-2 h-4 w-4" />
              )}
              Send Notifications
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
