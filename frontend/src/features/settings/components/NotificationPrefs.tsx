import { useEffect } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Bell } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import { useSettings, useUpdateSettings } from '../hooks';

const schema = z.object({
  day_of_reminder_time: z.string().regex(/^\d{2}:\d{2}$/, 'Must be HH:MM format'),
  sms_time_window_start: z.string().regex(/^\d{2}:\d{2}$/, 'Must be HH:MM format'),
  sms_time_window_end: z.string().regex(/^\d{2}:\d{2}$/, 'Must be HH:MM format'),
  enable_delay_notifications: z.boolean(),
});

type FormData = z.infer<typeof schema>;

export function NotificationPrefs() {
  const { data: settings } = useSettings();
  const updateSettings = useUpdateSettings();

  const form = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      day_of_reminder_time: '07:00',
      sms_time_window_start: '08:00',
      sms_time_window_end: '21:00',
      enable_delay_notifications: true,
    },
  });

  useEffect(() => {
    if (settings) {
      form.reset({
        day_of_reminder_time: settings.day_of_reminder_time ?? '07:00',
        sms_time_window_start: settings.sms_time_window_start ?? '08:00',
        sms_time_window_end: settings.sms_time_window_end ?? '21:00',
        enable_delay_notifications: settings.enable_delay_notifications ?? true,
      });
    }
  }, [settings, form]);

  const onSubmit = async (data: FormData) => {
    try {
      await updateSettings.mutateAsync(data);
      toast.success('Notification preferences saved');
    } catch {
      toast.error('Failed to save notification preferences');
    }
  };

  return (
    <Card data-testid="notification-prefs-section" className="bg-white rounded-2xl shadow-sm border border-slate-100 hover:shadow-md transition-shadow dark:bg-slate-800 dark:border-slate-700">
      <CardHeader className="p-6 border-b border-slate-100 dark:border-slate-700">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-violet-50 rounded-lg dark:bg-violet-900/30">
            <Bell className="w-5 h-5 text-violet-600 dark:text-violet-400" />
          </div>
          <div>
            <CardTitle className="font-bold text-slate-800 text-lg dark:text-slate-100">Notification Preferences</CardTitle>
            <CardDescription className="text-slate-500 text-sm dark:text-slate-400">Configure reminder times and SMS delivery windows</CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-6">
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6" data-testid="notification-prefs-form">
          <div className="space-y-2">
            <Label htmlFor="np-reminder-time" className="text-sm font-medium text-slate-700 dark:text-slate-300">Day-of Reminder Time (CT)</Label>
            <Input
              id="np-reminder-time"
              type="time"
              data-testid="np-reminder-time-input"
              {...form.register('day_of_reminder_time')}
            />
            <p className="text-xs text-slate-400">Time to send appointment reminders on the day of service</p>
            {form.formState.errors.day_of_reminder_time && (
              <p className="text-xs text-red-500">{form.formState.errors.day_of_reminder_time.message}</p>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="np-sms-start" className="text-sm font-medium text-slate-700 dark:text-slate-300">SMS Window Start</Label>
              <Input
                id="np-sms-start"
                type="time"
                data-testid="np-sms-start-input"
                {...form.register('sms_time_window_start')}
              />
              {form.formState.errors.sms_time_window_start && (
                <p className="text-xs text-red-500">{form.formState.errors.sms_time_window_start.message}</p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="np-sms-end" className="text-sm font-medium text-slate-700 dark:text-slate-300">SMS Window End</Label>
              <Input
                id="np-sms-end"
                type="time"
                data-testid="np-sms-end-input"
                {...form.register('sms_time_window_end')}
              />
              {form.formState.errors.sms_time_window_end && (
                <p className="text-xs text-red-500">{form.formState.errors.sms_time_window_end.message}</p>
              )}
            </div>
          </div>
          <p className="text-xs text-slate-400 -mt-4">SMS messages will only be sent within this time window</p>

          <div className="flex items-center justify-between py-3 border-t border-slate-100 dark:border-slate-700">
            <div className="space-y-0.5">
              <Label htmlFor="np-delay-toggle" className="text-sm font-medium text-slate-700 dark:text-slate-300">Delay Notifications</Label>
              <p className="text-xs text-slate-400">Send notifications when appointments are running behind schedule</p>
            </div>
            <Controller
              control={form.control}
              name="enable_delay_notifications"
              render={({ field }) => (
                <Switch
                  id="np-delay-toggle"
                  data-testid="np-delay-toggle"
                  checked={field.value}
                  onCheckedChange={field.onChange}
                />
              )}
            />
          </div>

          <div className="flex justify-end">
            <Button type="submit" disabled={updateSettings.isPending} data-testid="save-notification-prefs-btn">
              {updateSettings.isPending ? 'Saving...' : 'Save Notification Preferences'}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
