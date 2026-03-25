import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { LoadingSpinner } from '@/shared/components';
import { Calculator, TrendingUp, TrendingDown, DollarSign } from 'lucide-react';
import { cn } from '@/shared/utils/cn';
import { useTaxEstimate, useProjectTax } from '../hooks';
import type { TaxProjectionResponse } from '../types';

const projectionSchema = z.object({
  hypothetical_revenue: z.number().min(0, 'Must be 0 or greater'),
  hypothetical_expenses: z.number().min(0, 'Must be 0 or greater'),
});

type ProjectionFormData = z.infer<typeof projectionSchema>;

export function TaxProjection() {
  const { data: taxEstimate, isLoading } = useTaxEstimate();
  const projectTax = useProjectTax();
  const [projection, setProjection] = useState<TaxProjectionResponse | null>(null);

  const form = useForm<ProjectionFormData>({
    resolver: zodResolver(projectionSchema),
    defaultValues: { hypothetical_revenue: 0, hypothetical_expenses: 0 },
  });

  const onSubmit = async (data: ProjectionFormData) => {
    try {
      const result = await projectTax.mutateAsync(data);
      setProjection(result);
    } catch {
      // Error handled by mutation
    }
  };

  return (
    <div className="space-y-6">
      {/* Current Tax Estimate */}
      <Card data-testid="tax-estimate">
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <DollarSign className="h-5 w-5 text-amber-500" />
            Estimated Tax Due
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-4"><LoadingSpinner /></div>
          ) : (
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="space-y-1">
                <p className="text-sm text-slate-500">Estimated Tax Due</p>
                <p className="text-xl font-bold text-slate-800" data-testid="estimated-tax-due">
                  ${(taxEstimate?.estimated_tax_due ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </p>
              </div>
              <div className="space-y-1">
                <p className="text-sm text-slate-500">Effective Tax Rate</p>
                <p className="text-xl font-bold text-slate-800" data-testid="effective-tax-rate">
                  {(taxEstimate?.effective_tax_rate ?? 0).toFixed(1)}%
                </p>
              </div>
              <div className="space-y-1">
                <p className="text-sm text-slate-500">Taxable Income</p>
                <p className="text-xl font-bold text-slate-800" data-testid="taxable-income">
                  ${(taxEstimate?.taxable_income ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </p>
              </div>
              <div className="space-y-1">
                <p className="text-sm text-slate-500">Total Deductions</p>
                <p className="text-xl font-bold text-emerald-600" data-testid="total-deductions">
                  ${(taxEstimate?.total_deductions ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* What-If Projection */}
      <Card data-testid="tax-projection">
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Calculator className="h-5 w-5 text-violet-500" />
            What-If Tax Projection
          </CardTitle>
          <p className="text-sm text-slate-500">
            Enter hypothetical revenue and expenses to see the projected tax impact
          </p>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4" data-testid="tax-projection-form">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <FormField control={form.control} name="hypothetical_revenue" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Additional Revenue ($)</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        step="0.01"
                        data-testid="projection-revenue-input"
                        value={field.value}
                        onChange={(e) => field.onChange(e.target.valueAsNumber || 0)}
                        onBlur={field.onBlur}
                        name={field.name}
                        ref={field.ref}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
                <FormField control={form.control} name="hypothetical_expenses" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Additional Expenses ($)</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        step="0.01"
                        data-testid="projection-expenses-input"
                        value={field.value}
                        onChange={(e) => field.onChange(e.target.valueAsNumber || 0)}
                        onBlur={field.onBlur}
                        name={field.name}
                        ref={field.ref}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
              </div>
              <Button type="submit" disabled={projectTax.isPending} data-testid="projection-submit-btn">
                {projectTax.isPending ? 'Calculating...' : 'Calculate Projection'}
              </Button>
            </form>
          </Form>

          {projection && (
            <div className="mt-6 grid grid-cols-2 lg:grid-cols-4 gap-4 p-4 bg-slate-50 rounded-lg" data-testid="projection-results">
              <div className="space-y-1">
                <p className="text-sm text-slate-500">Current Tax Due</p>
                <p className="text-lg font-bold text-slate-800">
                  ${projection.current_tax_due.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </p>
              </div>
              <div className="space-y-1">
                <p className="text-sm text-slate-500">Projected Tax Due</p>
                <p className="text-lg font-bold text-slate-800">
                  ${projection.projected_tax_due.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </p>
              </div>
              <div className="space-y-1">
                <p className="text-sm text-slate-500">Tax Impact</p>
                <p className={cn('text-lg font-bold flex items-center gap-1', projection.tax_impact > 0 ? 'text-red-600' : 'text-emerald-600')}>
                  {projection.tax_impact > 0 ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
                  ${Math.abs(projection.tax_impact).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </p>
              </div>
              <div className="space-y-1">
                <p className="text-sm text-slate-500">Projected Taxable Income</p>
                <p className="text-lg font-bold text-slate-800">
                  ${projection.projected_taxable_income.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
