import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { LoadingSpinner, ErrorMessage } from '@/shared/components';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { Plus, Trash2 } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import { useBudgets, useCreateBudget, useDeleteBudget } from '../hooks';
import type { MarketingBudgetCreateRequest } from '../types';

const budgetSchema = z.object({
  channel: z.string().min(1, 'Channel is required'),
  budget_amount: z.number().positive('Budget must be positive'),
  period_start: z.string().min(1, 'Start date is required'),
  period_end: z.string().min(1, 'End date is required'),
  notes: z.string().optional(),
});

type BudgetFormData = z.infer<typeof budgetSchema>;

export function BudgetTracker() {
  const [dialogOpen, setDialogOpen] = useState(false);
  const { data: budgets, isLoading, error } = useBudgets();
  const createBudget = useCreateBudget();
  const deleteBudget = useDeleteBudget();

  const form = useForm<BudgetFormData>({
    resolver: zodResolver(budgetSchema),
    defaultValues: { channel: '', budget_amount: 0, period_start: '', period_end: '', notes: '' },
  });

  const onSubmit = async (data: BudgetFormData) => {
    try {
      const req: MarketingBudgetCreateRequest = {
        channel: data.channel,
        budget_amount: data.budget_amount,
        period_start: data.period_start,
        period_end: data.period_end,
        notes: data.notes || undefined,
      };
      await createBudget.mutateAsync(req);
      toast.success('Budget entry created');
      form.reset();
      setDialogOpen(false);
    } catch {
      toast.error('Failed to create budget entry');
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteBudget.mutateAsync(id);
      toast.success('Budget entry deleted');
    } catch {
      toast.error('Failed to delete budget entry');
    }
  };

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorMessage error={error} />;

  const items = budgets?.items ?? [];

  const chartData = items.map((b) => ({
    channel: b.channel,
    budget: b.budget_amount,
    actual: b.actual_spend,
  }));

  return (
    <div className="space-y-6" data-testid="budget-tracker">
      {/* Budget vs Actual Chart */}
      <Card data-testid="budget-vs-actual-chart">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg">Budget vs Actual Spend</CardTitle>
            <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
              <DialogTrigger asChild>
                <Button size="sm" data-testid="add-budget-btn">
                  <Plus className="h-4 w-4 mr-1" /> Add Budget
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Add Budget Entry</DialogTitle>
                </DialogHeader>
                <form
                  onSubmit={form.handleSubmit(onSubmit)}
                  className="space-y-4"
                  data-testid="budget-form"
                >
                  <div className="space-y-1">
                    <Label>Channel</Label>
                    <Input
                      {...form.register('channel')}
                      placeholder="e.g., Google Ads"
                      data-testid="budget-channel-input"
                    />
                    {form.formState.errors.channel && (
                      <p className="text-sm text-red-500">{form.formState.errors.channel.message}</p>
                    )}
                  </div>
                  <div className="space-y-1">
                    <Label>Budget Amount ($)</Label>
                    <Input
                      type="number"
                      step="0.01"
                      {...form.register('budget_amount', { valueAsNumber: true })}
                      data-testid="budget-amount-input"
                    />
                    {form.formState.errors.budget_amount && (
                      <p className="text-sm text-red-500">
                        {form.formState.errors.budget_amount.message}
                      </p>
                    )}
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1">
                      <Label>Period Start</Label>
                      <Input
                        type="date"
                        {...form.register('period_start')}
                        data-testid="budget-start-input"
                      />
                    </div>
                    <div className="space-y-1">
                      <Label>Period End</Label>
                      <Input
                        type="date"
                        {...form.register('period_end')}
                        data-testid="budget-end-input"
                      />
                    </div>
                  </div>
                  <div className="space-y-1">
                    <Label>Notes (optional)</Label>
                    <Textarea
                      {...form.register('notes')}
                      data-testid="budget-notes-input"
                    />
                  </div>
                  <Button
                    type="submit"
                    className="w-full"
                    disabled={createBudget.isPending}
                    data-testid="submit-budget-btn"
                  >
                    {createBudget.isPending ? 'Creating...' : 'Create Budget Entry'}
                  </Button>
                </form>
              </DialogContent>
            </Dialog>
          </div>
        </CardHeader>
        <CardContent>
          {chartData.length === 0 ? (
            <p className="text-sm text-slate-500 text-center py-8">
              No budget entries yet. Add one to get started.
            </p>
          ) : (
            <ResponsiveContainer width="100%" height={350}>
              <BarChart data={chartData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis
                  dataKey="channel"
                  tick={{ fontSize: 12, fill: '#64748b' }}
                  tickLine={false}
                  axisLine={{ stroke: '#e2e8f0' }}
                />
                <YAxis
                  tick={{ fontSize: 12, fill: '#64748b' }}
                  tickLine={false}
                  axisLine={{ stroke: '#e2e8f0' }}
                  tickFormatter={(v: number) => `$${v}`}
                />
                <Tooltip
                  formatter={(value) => [`$${Number(value).toFixed(2)}`]}
                  contentStyle={{
                    borderRadius: '8px',
                    border: '1px solid #e2e8f0',
                    boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
                  }}
                />
                <Legend />
                <Bar dataKey="budget" name="Budget" fill="#6366f1" radius={[4, 4, 0, 0]} />
                <Bar dataKey="actual" name="Actual Spend" fill="#14b8a6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      {/* Budget Entries Table */}
      <Card data-testid="budget-entries-table">
        <CardHeader>
          <CardTitle className="text-lg">Budget Entries</CardTitle>
        </CardHeader>
        <CardContent>
          {items.length === 0 ? (
            <p className="text-sm text-slate-500 text-center py-4">No budget entries</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Channel</TableHead>
                  <TableHead>Budget</TableHead>
                  <TableHead>Actual Spend</TableHead>
                  <TableHead>Remaining</TableHead>
                  <TableHead>Period</TableHead>
                  <TableHead className="w-12" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((entry) => (
                  <TableRow key={entry.id} data-testid="budget-entry-row">
                    <TableCell className="font-medium">{entry.channel}</TableCell>
                    <TableCell>${entry.budget_amount.toFixed(2)}</TableCell>
                    <TableCell>${entry.actual_spend.toFixed(2)}</TableCell>
                    <TableCell
                      className={
                        entry.budget_amount - entry.actual_spend < 0
                          ? 'text-red-600 font-medium'
                          : 'text-emerald-600'
                      }
                    >
                      ${(entry.budget_amount - entry.actual_spend).toFixed(2)}
                    </TableCell>
                    <TableCell className="text-sm text-slate-500">
                      {new Date(entry.period_start).toLocaleDateString()} –{' '}
                      {new Date(entry.period_end).toLocaleDateString()}
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleDelete(entry.id)}
                        data-testid="delete-budget-btn"
                      >
                        <Trash2 className="h-4 w-4 text-red-500" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
