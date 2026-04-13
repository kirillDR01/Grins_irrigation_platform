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
  const [lienDaysPastDue, setLienDaysPastDue] = useState(60);
  const [lienMinAmount, setLienMinAmount] = useState(500);
  const massNotify = useMassNotify();

  const handleSend = async () => {
    if (!notificationType) return;
    try {
      const result = await massNotify.mutateAsync({
        notification_type: notificationType,
        due_soon_days: dueSoonDays,
        lien_days_past_due: lienDaysPastDue,
        lien_min_amount: lienMinAmount,
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

            {notificationType === 'lien_eligible' && (
              <div className="space-y-3">
                <div className="space-y-1">
                  <label className="text-sm font-medium text-slate-700">Min Days Past Due</label>
                  <Input
                    type="number"
                    value={lienDaysPastDue}
                    onChange={(e) => setLienDaysPastDue(Number(e.target.value))}
                    min={1}
                    data-testid="mass-notify-lien-days"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-sm font-medium text-slate-700">Min Amount ($)</label>
                  <Input
                    type="number"
                    value={lienMinAmount}
                    onChange={(e) => setLienMinAmount(Number(e.target.value))}
                    min={0}
                    data-testid="mass-notify-lien-amount"
                  />
                </div>
              </div>
            )}
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
