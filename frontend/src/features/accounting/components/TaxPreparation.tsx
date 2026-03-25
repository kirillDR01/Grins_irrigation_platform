import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
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
import { Download, FileSpreadsheet } from 'lucide-react';
import { toast } from 'sonner';
import { useTaxSummary } from '../hooks';
import { accountingApi } from '../api/accountingApi';

const currentYear = new Date().getFullYear();
const yearOptions = Array.from({ length: 5 }, (_, i) => currentYear - i);

export function TaxPreparation() {
  const [taxYear, setTaxYear] = useState(currentYear);
  const { data: taxSummary, isLoading } = useTaxSummary(taxYear);

  const handleExportCsv = async () => {
    try {
      const blob = await accountingApi.exportTaxCsv(taxYear);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `tax-summary-${taxYear}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success('CSV exported');
    } catch {
      toast.error('Failed to export CSV');
    }
  };

  return (
    <Card data-testid="tax-preparation">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <FileSpreadsheet className="h-5 w-5 text-teal-500" />
            Tax Preparation
          </CardTitle>
          <div className="flex items-center gap-2">
            <Select value={String(taxYear)} onValueChange={(v) => setTaxYear(Number(v))}>
              <SelectTrigger className="w-28" data-testid="tax-year-select">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {yearOptions.map((y) => (
                  <SelectItem key={y} value={String(y)}>{y}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button variant="outline" size="sm" onClick={handleExportCsv} data-testid="export-csv-btn">
              <Download className="h-4 w-4 mr-1" /> Export CSV
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex justify-center py-8"><LoadingSpinner /></div>
        ) : (
          <div className="space-y-6">
            {/* Tax Categories Table */}
            <div>
              <h3 className="text-sm font-medium text-slate-500 mb-3">Deductible Expenses by Category</h3>
              <Table data-testid="tax-categories-table">
                <TableHeader>
                  <TableRow>
                    <TableHead>Category</TableHead>
                    <TableHead className="text-right">YTD Total</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(taxSummary?.categories ?? []).length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={2} className="text-center text-slate-500 py-4">
                        No expense data for {taxYear}
                      </TableCell>
                    </TableRow>
                  ) : (
                    <>
                      {taxSummary?.categories.map((cat) => (
                        <TableRow key={cat.category} data-testid="tax-category-row">
                          <TableCell className="font-medium">{cat.category}</TableCell>
                          <TableCell className="text-right">
                            ${cat.total.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                          </TableCell>
                        </TableRow>
                      ))}
                      <TableRow className="font-bold border-t-2">
                        <TableCell>Total Deductions</TableCell>
                        <TableCell className="text-right">
                          ${(taxSummary?.total_deductions ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                        </TableCell>
                      </TableRow>
                    </>
                  )}
                </TableBody>
              </Table>
            </div>

            {/* Revenue by Job Type */}
            {(taxSummary?.revenue_by_job_type?.length ?? 0) > 0 && (
              <div>
                <h3 className="text-sm font-medium text-slate-500 mb-3">Revenue by Job Type</h3>
                <Table data-testid="revenue-by-job-type-table">
                  <TableHeader>
                    <TableRow>
                      <TableHead>Job Type</TableHead>
                      <TableHead className="text-right">Revenue</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {taxSummary?.revenue_by_job_type.map((item) => (
                      <TableRow key={item.job_type} data-testid="revenue-job-type-row">
                        <TableCell className="font-medium">{item.job_type}</TableCell>
                        <TableCell className="text-right">
                          ${item.total.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
