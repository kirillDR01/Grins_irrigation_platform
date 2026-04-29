// @ts-nocheck — pre-existing TS errors documented in bughunt/2026-04-29-pre-existing-tsc-errors.md
import { useEffect } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Calculator } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import { useSettings, useUpdateSettings } from '../hooks';

const schema = z.object({
  default_valid_days: z.coerce.number().int().min(1, 'Must be at least 1 day').max(365),
  follow_up_intervals_days: z
    .string()
    .min(1, 'At least one interval is required')
    .regex(/^\d+(,\d+)*$/, 'Must be comma-separated numbers (e.g. 3,7,14,21)'),
  enable_auto_follow_ups: z.boolean(),
});

type FormData = z.infer<typeof schema>;

export function EstimateDefaults() {
  const { data: settings } = useSettings();
  const updateSettings = useUpdateSettings();

  const form = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      default_valid_days: 30,
      follow_up_intervals_days: '3,7,14,21',
      enable_auto_follow_ups: true,
    },
  });

  useEffect(() => {
    if (settings) {
      form.reset({
        default_valid_days: settings.default_valid_days ?? 30,
        follow_up_intervals_days: settings.follow_up_intervals_days ?? '3,7,14,21',
        enable_auto_follow_ups: settings.enable_auto_follow_ups ?? true,
      });
    }
  }, [settings, form]);

  const onSubmit = async (data: FormData) => {
    try {
      await updateSettings.mutateAsync(data);
      toast.success('Estimate defaults saved');
    } catch {
      toast.error('Failed to save estimate defaults');
    }
  };

  return (
    <Card data-testid="estimate-defaults-section" className="bg-white rounded-2xl shadow-sm border border-slate-100 hover:shadow-md transition-shadow dark:bg-slate-800 dark:border-slate-700">
      <CardHeader className="p-6 border-b border-slate-100 dark:border-slate-700">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-amber-50 rounded-lg dark:bg-amber-900/30">
            <Calculator className="w-5 h-5 text-amber-600 dark:text-amber-400" />
          </div>
          <div>
            <CardTitle className="font-bold text-slate-800 text-lg dark:text-slate-100">Estimate Defaults</CardTitle>
            <CardDescription className="text-slate-500 text-sm dark:text-slate-400">Default values for new estimates and follow-up scheduling</CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-6">
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6" data-testid="estimate-defaults-form">
          <div className="space-y-2">
            <Label htmlFor="ed-valid-days" className="text-sm font-medium text-slate-700 dark:text-slate-300">Estimate Valid For (days)</Label>
            <Input
              id="ed-valid-days"
              type="number"
              data-testid="ed-valid-days-input"
              {...form.register('default_valid_days')}
              placeholder="30"
            />
            <p className="text-xs text-slate-400">Number of days before an estimate expires</p>
            {form.formState.errors.default_valid_days && (
              <p className="text-xs text-red-500">{form.formState.errors.default_valid_days.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="ed-follow-up-intervals" className="text-sm font-medium text-slate-700 dark:text-slate-300">Follow-up Intervals (days)</Label>
            <Input
              id="ed-follow-up-intervals"
              data-testid="ed-follow-up-intervals-input"
              {...form.register('follow_up_intervals_days')}
              placeholder="3,7,14,21"
            />
            <p className="text-xs text-slate-400">Comma-separated days after sending to follow up (e.g. 3,7,14,21)</p>
            {form.formState.errors.follow_up_intervals_days && (
              <p className="text-xs text-red-500">{form.formState.errors.follow_up_intervals_days.message}</p>
            )}
          </div>

          <div className="flex items-center justify-between py-3 border-t border-slate-100 dark:border-slate-700">
            <div className="space-y-0.5">
              <Label htmlFor="ed-auto-followups-toggle" className="text-sm font-medium text-slate-700 dark:text-slate-300">Auto Follow-ups</Label>
              <p className="text-xs text-slate-400">Automatically send follow-up reminders for unanswered estimates</p>
            </div>
            <Controller
              control={form.control}
              name="enable_auto_follow_ups"
              render={({ field }) => (
                <Switch
                  id="ed-auto-followups-toggle"
                  data-testid="ed-auto-followups-toggle"
                  checked={field.value}
                  onCheckedChange={field.onChange}
                />
              )}
            />
          </div>

          <div className="flex justify-end">
            <Button type="submit" disabled={updateSettings.isPending} data-testid="save-estimate-defaults-btn">
              {updateSettings.isPending ? 'Saving...' : 'Save Estimate Defaults'}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
