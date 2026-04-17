/**
 * BusinessSettingsPanel — admin panel for the four H-12 firm-wide knobs.
 *
 * H-12 (bughunt 2026-04-16): lien thresholds + upcoming-due window + no-reply
 * window are persisted in ``business_settings`` and read by
 * ``InvoiceService.compute_lien_candidates`` / ``mass_notify``. The admin
 * edits them here once and every subsequent service call uses the new values.
 */

import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Scale } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';

import {
  useBusinessSettings,
  useUpdateBusinessSettings,
} from '../hooks/useBusinessSettings';

const schema = z.object({
  lien_days_past_due: z.coerce
    .number()
    .int()
    .min(1, 'Must be at least 1 day')
    .max(3650, 'At most 10 years'),
  lien_min_amount: z.coerce
    .number()
    .min(0, 'Cannot be negative'),
  upcoming_due_days: z.coerce
    .number()
    .int()
    .min(1, 'Must be at least 1 day')
    .max(365),
  confirmation_no_reply_days: z.coerce
    .number()
    .int()
    .min(1, 'Must be at least 1 day')
    .max(365),
});

type FormData = z.infer<typeof schema>;

export function BusinessSettingsPanel() {
  const { data: settings, isLoading } = useBusinessSettings();
  const updateMutation = useUpdateBusinessSettings();

  const form = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      lien_days_past_due: 60,
      lien_min_amount: 500,
      upcoming_due_days: 7,
      confirmation_no_reply_days: 3,
    },
  });

  useEffect(() => {
    if (settings) {
      form.reset({
        lien_days_past_due: settings.lien_days_past_due ?? 60,
        lien_min_amount: Number(settings.lien_min_amount ?? 500),
        upcoming_due_days: settings.upcoming_due_days ?? 7,
        confirmation_no_reply_days: settings.confirmation_no_reply_days ?? 3,
      });
    }
  }, [settings, form]);

  const onSubmit = async (data: FormData) => {
    try {
      await updateMutation.mutateAsync({
        lien_days_past_due: data.lien_days_past_due,
        lien_min_amount: String(data.lien_min_amount),
        upcoming_due_days: data.upcoming_due_days,
        confirmation_no_reply_days: data.confirmation_no_reply_days,
      });
      toast.success('Business settings saved');
    } catch {
      toast.error('Failed to save business settings');
    }
  };

  return (
    <Card
      data-testid="business-settings-panel"
      className="bg-white rounded-2xl shadow-sm border border-slate-100 hover:shadow-md transition-shadow dark:bg-slate-800 dark:border-slate-700"
    >
      <CardHeader className="p-6 border-b border-slate-100 dark:border-slate-700">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-sky-50 rounded-lg dark:bg-sky-900/30">
            <Scale className="w-5 h-5 text-sky-600 dark:text-sky-400" />
          </div>
          <div>
            <CardTitle className="font-bold text-slate-800 text-lg dark:text-slate-100">
              Business Thresholds
            </CardTitle>
            <CardDescription className="text-slate-500 text-sm dark:text-slate-400">
              Firm-wide defaults used by the lien review queue, mass
              notifications, and confirmation no-reply review queue.
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-6">
        <form
          onSubmit={form.handleSubmit(onSubmit)}
          className="space-y-6"
          data-testid="business-settings-form"
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label
                htmlFor="id-lien-days-past-due"
                className="text-sm font-medium text-slate-700 dark:text-slate-300"
              >
                Lien Days Past Due
              </Label>
              <Input
                id="id-lien-days-past-due"
                type="number"
                data-testid="input-lien-days-past-due"
                {...form.register('lien_days_past_due')}
                placeholder="60"
                disabled={isLoading}
              />
              {form.formState.errors.lien_days_past_due && (
                <p className="text-xs text-red-500">
                  {form.formState.errors.lien_days_past_due.message}
                </p>
              )}
            </div>
            <div className="space-y-2">
              <Label
                htmlFor="id-lien-min-amount"
                className="text-sm font-medium text-slate-700 dark:text-slate-300"
              >
                Lien Minimum Amount ($)
              </Label>
              <Input
                id="id-lien-min-amount"
                type="number"
                step="0.01"
                data-testid="input-lien-min-amount"
                {...form.register('lien_min_amount')}
                placeholder="500"
                disabled={isLoading}
              />
              {form.formState.errors.lien_min_amount && (
                <p className="text-xs text-red-500">
                  {form.formState.errors.lien_min_amount.message}
                </p>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label
                htmlFor="id-upcoming-due-days"
                className="text-sm font-medium text-slate-700 dark:text-slate-300"
              >
                Upcoming Due Window (days)
              </Label>
              <Input
                id="id-upcoming-due-days"
                type="number"
                data-testid="input-upcoming-due-days"
                {...form.register('upcoming_due_days')}
                placeholder="7"
                disabled={isLoading}
              />
              {form.formState.errors.upcoming_due_days && (
                <p className="text-xs text-red-500">
                  {form.formState.errors.upcoming_due_days.message}
                </p>
              )}
            </div>
            <div className="space-y-2">
              <Label
                htmlFor="id-confirmation-no-reply-days"
                className="text-sm font-medium text-slate-700 dark:text-slate-300"
              >
                Confirmation No-Reply (days)
              </Label>
              <Input
                id="id-confirmation-no-reply-days"
                type="number"
                data-testid="input-confirmation-no-reply-days"
                {...form.register('confirmation_no_reply_days')}
                placeholder="3"
                disabled={isLoading}
              />
              {form.formState.errors.confirmation_no_reply_days && (
                <p className="text-xs text-red-500">
                  {form.formState.errors.confirmation_no_reply_days.message}
                </p>
              )}
            </div>
          </div>

          <div className="flex justify-end">
            <Button
              type="submit"
              disabled={updateMutation.isPending || isLoading}
              data-testid="save-business-settings-btn"
            >
              {updateMutation.isPending ? 'Saving…' : 'Save Business Settings'}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
