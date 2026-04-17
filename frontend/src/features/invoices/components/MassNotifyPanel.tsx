import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Bell, ChevronDown, ChevronUp, Loader2, Settings as SettingsIcon } from 'lucide-react';
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
import { useBusinessSettings } from '@/features/settings';
import { useMassNotify } from '../hooks';
import { MASS_NOTIFICATION_CONFIG, type MassNotificationType } from '../types';

export function MassNotifyPanel() {
  const [open, setOpen] = useState(false);
  const [notificationType, setNotificationType] = useState<MassNotificationType | ''>('');
  // H-12: upcoming_due_days now lives in business_settings. Default below is
  // a best-effort client fallback used only if the GET /settings/business
  // query is still loading when the dialog opens.
  const { data: thresholds } = useBusinessSettings();
  const defaultUpcomingDueDays = thresholds?.upcoming_due_days ?? 7;
  const [overrideOnce, setOverrideOnce] = useState(false);
  const [overrideDueSoonDays, setOverrideDueSoonDays] = useState<number>(defaultUpcomingDueDays);
  const massNotify = useMassNotify();

  const handleSend = async () => {
    if (!notificationType) return;
    try {
      const result = await massNotify.mutateAsync({
        notification_type: notificationType,
        // Only pass an explicit due_soon_days when the admin flipped the
        // override — otherwise the backend reads upcoming_due_days from
        // business_settings (H-12).
        ...(overrideOnce && notificationType === 'due_soon'
          ? { due_soon_days: overrideDueSoonDays }
          : {}),
      });
      toast.success('Mass Notification Sent', {
        description: `Targeted: ${result.targeted}, Sent: ${result.sent}, Skipped: ${result.skipped}, Failed: ${result.failed}`,
      });
      setOpen(false);
      setOverrideOnce(false);
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
              <div className="space-y-2">
                <p
                  className="text-xs text-slate-500"
                  data-testid="mass-notify-threshold-note"
                >
                  Current due-soon window: <strong>{defaultUpcomingDueDays} days</strong>.{' '}
                  <Link
                    to="/settings?tab=business"
                    className="inline-flex items-center gap-1 text-sky-600 hover:underline dark:text-sky-400"
                    data-testid="mass-notify-configure-link"
                  >
                    <SettingsIcon className="h-3 w-3" />
                    configure in Business Settings
                  </Link>
                </p>
                <Button
                  variant="ghost"
                  size="sm"
                  type="button"
                  className="h-7 px-2 text-xs"
                  onClick={() => setOverrideOnce((v) => !v)}
                  data-testid="mass-notify-override-toggle"
                >
                  {overrideOnce ? (
                    <ChevronUp className="mr-1 h-3 w-3" />
                  ) : (
                    <ChevronDown className="mr-1 h-3 w-3" />
                  )}
                  Override once
                </Button>
                {overrideOnce && (
                  <div className="space-y-1 rounded-md border border-dashed border-slate-200 p-2 dark:border-slate-700">
                    <label className="text-xs font-medium text-slate-600">
                      Days Until Due (this send only)
                    </label>
                    <Input
                      type="number"
                      value={overrideDueSoonDays}
                      onChange={(e) => setOverrideDueSoonDays(Number(e.target.value))}
                      min={1}
                      max={90}
                      data-testid="mass-notify-due-soon-days"
                    />
                  </div>
                )}
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
