import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { LoadingSpinner } from '@/shared/components';
import { Link2, RefreshCw, CheckCircle2, Clock } from 'lucide-react';
import { toast } from 'sonner';
import {
  useConnectedAccounts,
  usePendingTransactions,
  useApproveTransaction,
} from '../hooks';
import type { ExpenseCategory } from '../types';

const EXPENSE_CATEGORIES: { value: ExpenseCategory; label: string }[] = [
  { value: 'MATERIALS', label: 'Materials' },
  { value: 'FUEL', label: 'Fuel' },
  { value: 'MAINTENANCE', label: 'Maintenance' },
  { value: 'LABOR', label: 'Labor' },
  { value: 'MARKETING', label: 'Marketing' },
  { value: 'INSURANCE', label: 'Insurance' },
  { value: 'EQUIPMENT', label: 'Equipment' },
  { value: 'OFFICE', label: 'Office' },
  { value: 'SUBCONTRACTING', label: 'Subcontracting' },
  { value: 'OTHER', label: 'Other' },
];

export function ConnectedAccounts() {
  const { data: accounts, isLoading: accountsLoading } = useConnectedAccounts();
  const { data: transactions, isLoading: txnLoading } = usePendingTransactions();
  const approveTransaction = useApproveTransaction();
  const [selectedCategories, setSelectedCategories] = useState<Record<string, string>>({});

  const handleConnectPlaid = async () => {
    // In production, this would open the Plaid Link modal
    // For now, show a placeholder message
    toast.info('Plaid Link', { description: 'Plaid Link integration will open here' });
  };

  const handleApprove = async (txnId: string) => {
    const category = selectedCategories[txnId];
    if (!category) {
      toast.error('Please select a category first');
      return;
    }
    try {
      await approveTransaction.mutateAsync({ id: txnId, category });
      toast.success('Transaction approved');
    } catch {
      toast.error('Failed to approve transaction');
    }
  };

  return (
    <div className="space-y-6">
      {/* Connected Accounts */}
      <Card data-testid="connected-accounts">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg flex items-center gap-2">
              <Link2 className="h-5 w-5 text-blue-500" />
              Connected Accounts
            </CardTitle>
            <Button size="sm" onClick={handleConnectPlaid} data-testid="connect-plaid-btn">
              <Link2 className="h-4 w-4 mr-1" /> Connect Account
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {accountsLoading ? (
            <div className="flex justify-center py-4"><LoadingSpinner /></div>
          ) : (accounts ?? []).length === 0 ? (
            <div className="text-center py-8">
              <Link2 className="h-10 w-10 text-slate-300 mx-auto mb-3" />
              <p className="text-sm text-slate-500">No accounts connected yet</p>
              <p className="text-xs text-slate-400 mt-1">Connect your bank or credit card for automatic expense tracking</p>
            </div>
          ) : (
            <div className="divide-y">
              {accounts?.map((account) => (
                <div key={account.id} className="flex items-center justify-between py-3" data-testid="connected-account-row">
                  <div>
                    <p className="font-medium text-slate-800">{account.institution_name}</p>
                    <p className="text-sm text-slate-500">
                      {account.account_name} •••• {account.mask}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    {account.last_synced_at ? (
                      <Badge variant="outline" className="text-xs flex items-center gap-1">
                        <CheckCircle2 className="h-3 w-3 text-emerald-500" />
                        Synced {new Date(account.last_synced_at).toLocaleDateString()}
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="text-xs flex items-center gap-1">
                        <Clock className="h-3 w-3 text-amber-500" />
                        Pending sync
                      </Badge>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Transaction Review Queue */}
      <Card data-testid="transaction-review">
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <RefreshCw className="h-5 w-5 text-amber-500" />
            Transaction Review Queue
          </CardTitle>
          <p className="text-sm text-slate-500">Review and categorize imported transactions</p>
        </CardHeader>
        <CardContent>
          {txnLoading ? (
            <div className="flex justify-center py-4"><LoadingSpinner /></div>
          ) : (transactions?.items ?? []).length === 0 ? (
            <p className="text-sm text-slate-500 text-center py-8">No transactions pending review</p>
          ) : (
            <Table data-testid="transaction-table">
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead>Merchant</TableHead>
                  <TableHead className="text-right">Amount</TableHead>
                  <TableHead>Category</TableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {transactions?.items.map((txn) => (
                  <TableRow key={txn.id} data-testid="transaction-row">
                    <TableCell className="text-sm">{new Date(txn.date).toLocaleDateString()}</TableCell>
                    <TableCell className="text-sm max-w-[200px] truncate">{txn.description}</TableCell>
                    <TableCell className="text-sm text-slate-500">{txn.merchant_name ?? '—'}</TableCell>
                    <TableCell className="text-right font-medium">
                      ${txn.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </TableCell>
                    <TableCell>
                      <Select
                        value={selectedCategories[txn.id] ?? txn.suggested_category ?? ''}
                        onValueChange={(v) => setSelectedCategories((prev) => ({ ...prev, [txn.id]: v }))}
                      >
                        <SelectTrigger className="w-36" data-testid="transaction-category-select">
                          <SelectValue placeholder="Category" />
                        </SelectTrigger>
                        <SelectContent>
                          {EXPENSE_CATEGORIES.map((c) => (
                            <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </TableCell>
                    <TableCell>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleApprove(txn.id)}
                        data-testid="approve-transaction-btn"
                      >
                        <CheckCircle2 className="h-4 w-4 mr-1" /> Approve
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
