import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { FileText } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import { useSettings, useUpdateSettings } from '../hooks';

const schema = z.object({
  default_payment_terms_days: z.coerce.number().int().min(1, 'Must be at least 1 day').max(365),
  late_fee_percentage: z.coerce.number().min(0, 'Cannot be negative').max(100),
  lien_warning_days: z.coerce.number().int().min(1).max(365),
  lien_filing_days: z.coerce.number().int().min(1).max(365),
});

type FormData = z.infer<typeof schema>;

export function InvoiceDefaults() {
  const { data: settings } = useSettings();
  const updateSettings = useUpdateSettings();

  const form = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      default_payment_terms_days: 30,
      late_fee_percentage: 0,
      lien_warning_days: 45,
      lien_filing_days: 120,
    },
  });

  useEffect(() => {
    if (settings) {
      form.reset({
        default_payment_terms_days: settings.default_payment_terms_days ?? 30,
        late_fee_percentage: settings.late_fee_percentage ?? 0,
        lien_warning_days: settings.lien_warning_days ?? 45,
        lien_filing_days: settings.lien_filing_days ?? 120,
      });
    }
  }, [settings, form]);

  const onSubmit = async (data: FormData) => {
    try {
      await updateSettings.mutateAsync(data);
      toast.success('Invoice defaults saved');
    } catch {
      toast.error('Failed to save invoice defaults');
    }
  };

  return (
    <Card data-testid="invoice-defaults-section" className="bg-white rounded-2xl shadow-sm border border-slate-100 hover:shadow-md transition-shadow dark:bg-slate-800 dark:border-slate-700">
      <CardHeader className="p-6 border-b border-slate-100 dark:border-slate-700">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-emerald-50 rounded-lg dark:bg-emerald-900/30">
            <FileText className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
          </div>
          <div>
            <CardTitle className="font-bold text-slate-800 text-lg dark:text-slate-100">Invoice Defaults</CardTitle>
            <CardDescription className="text-slate-500 text-sm dark:text-slate-400">Default values for new invoices and lien tracking</CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-6">
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6" data-testid="invoice-defaults-form">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="id-payment-terms" className="text-sm font-medium text-slate-700 dark:text-slate-300">Payment Terms (days)</Label>
              <Input
                id="id-payment-terms"
                type="number"
                data-testid="id-payment-terms-input"
                {...form.register('default_payment_terms_days')}
                placeholder="30"
              />
              {form.formState.errors.default_payment_terms_days && (
                <p className="text-xs text-red-500">{form.formState.errors.default_payment_terms_days.message}</p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="id-late-fee" className="text-sm font-medium text-slate-700 dark:text-slate-300">Late Fee (%)</Label>
              <Input
                id="id-late-fee"
                type="number"
                step="0.1"
                data-testid="id-late-fee-input"
                {...form.register('late_fee_percentage')}
                placeholder="0"
              />
              {form.formState.errors.late_fee_percentage && (
                <p className="text-xs text-red-500">{form.formState.errors.late_fee_percentage.message}</p>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="id-lien-warning" className="text-sm font-medium text-slate-700 dark:text-slate-300">Lien Warning (days)</Label>
              <Input
                id="id-lien-warning"
                type="number"
                data-testid="id-lien-warning-input"
                {...form.register('lien_warning_days')}
                placeholder="45"
              />
              {form.formState.errors.lien_warning_days && (
                <p className="text-xs text-red-500">{form.formState.errors.lien_warning_days.message}</p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="id-lien-filing" className="text-sm font-medium text-slate-700 dark:text-slate-300">Lien Filing (days)</Label>
              <Input
                id="id-lien-filing"
                type="number"
                data-testid="id-lien-filing-input"
                {...form.register('lien_filing_days')}
                placeholder="120"
              />
              {form.formState.errors.lien_filing_days && (
                <p className="text-xs text-red-500">{form.formState.errors.lien_filing_days.message}</p>
              )}
            </div>
          </div>

          <div className="flex justify-end">
            <Button type="submit" disabled={updateSettings.isPending} data-testid="save-invoice-defaults-btn">
              {updateSettings.isPending ? 'Saving...' : 'Save Invoice Defaults'}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
