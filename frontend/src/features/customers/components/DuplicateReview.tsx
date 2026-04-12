import { Users, Merge, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { useState } from 'react';
import { useCustomerDuplicates, useMergeCustomers } from '../hooks';
import { getCustomerFullName } from '../types';
import { toast } from 'sonner';

interface DuplicateReviewProps {
  customerId: string;
}

export function DuplicateReview({ customerId }: DuplicateReviewProps) {
  const { data: duplicateGroup, isLoading } = useCustomerDuplicates(customerId);
  const mergeMutation = useMergeCustomers(customerId);
  const [mergeDialogOpen, setMergeDialogOpen] = useState(false);
  const [selectedDuplicateId, setSelectedDuplicateId] = useState<string | null>(null);

  // Don't render anything if no duplicates or still loading
  if (isLoading || !duplicateGroup || duplicateGroup.duplicates.length === 0) {
    return null;
  }

  const handleMerge = async (duplicateId: string) => {
    try {
      await mergeMutation.mutateAsync({
        duplicate_id: duplicateId,
        field_selections: [],
      });
      toast.success('Customers merged successfully');
      setMergeDialogOpen(false);
      setSelectedDuplicateId(null);
    } catch {
      toast.error('Failed to merge customers');
    }
  };

  const selectedDuplicate = duplicateGroup.duplicates.find((d) => d.id === selectedDuplicateId);
  const primary = duplicateGroup.primary;

  return (
    <div data-testid="duplicate-review" className="space-y-4">
      <div className="flex items-center gap-2 text-amber-600">
        <AlertTriangle className="h-4 w-4" />
        <span className="text-sm font-medium">
          {duplicateGroup.duplicates.length} potential duplicate{duplicateGroup.duplicates.length > 1 ? 's' : ''} found
        </span>
      </div>

      <div className="space-y-3">
        {duplicateGroup.duplicates.map((dup) => (
          <Card key={dup.id} className="border-amber-100" data-testid={`duplicate-${dup.id}`}>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="space-y-1">
                  <p className="font-medium text-slate-800">{getCustomerFullName(dup)}</p>
                  <div className="flex items-center gap-3 text-xs text-slate-500">
                    {dup.phone && <span>{dup.phone}</span>}
                    {dup.email && <span>{dup.email}</span>}
                  </div>
                  <div className="flex gap-1.5 mt-1">
                    {duplicateGroup.match_reasons.map((reason) => (
                      <Badge key={reason} variant="outline" className="text-xs">
                        {reason}
                      </Badge>
                    ))}
                  </div>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setSelectedDuplicateId(dup.id);
                    setMergeDialogOpen(true);
                  }}
                  data-testid={`merge-btn-${dup.id}`}
                >
                  <Merge className="h-3.5 w-3.5 mr-1" />
                  Merge
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Merge confirmation dialog with side-by-side comparison */}
      <Dialog open={mergeDialogOpen} onOpenChange={setMergeDialogOpen}>
        <DialogContent className="max-w-lg" data-testid="merge-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Users className="h-5 w-5" />
              Merge Customers
            </DialogTitle>
            <DialogDescription>
              The duplicate record will be merged into the primary customer. All jobs, invoices, and communications will be transferred.
            </DialogDescription>
          </DialogHeader>

          {selectedDuplicate && (
            <div className="grid grid-cols-2 gap-4 py-4" data-testid="merge-comparison">
              {/* Primary */}
              <div className="p-3 rounded-lg border-2 border-teal-200 bg-teal-50/50">
                <Badge variant="teal" className="text-xs mb-2">Primary (Keep)</Badge>
                <p className="font-medium text-slate-800">{getCustomerFullName(primary)}</p>
                <p className="text-xs text-slate-500 mt-1">{primary.phone}</p>
                {primary.email && <p className="text-xs text-slate-500">{primary.email}</p>}
              </div>
              {/* Duplicate */}
              <div className="p-3 rounded-lg border border-red-200 bg-red-50/50">
                <Badge variant="destructive" className="text-xs mb-2">Duplicate (Remove)</Badge>
                <p className="font-medium text-slate-800">{getCustomerFullName(selectedDuplicate)}</p>
                <p className="text-xs text-slate-500 mt-1">{selectedDuplicate.phone}</p>
                {selectedDuplicate.email && <p className="text-xs text-slate-500">{selectedDuplicate.email}</p>}
              </div>
            </div>
          )}

          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setMergeDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => selectedDuplicateId && handleMerge(selectedDuplicateId)}
              disabled={mergeMutation.isPending}
              data-testid="confirm-merge-btn"
            >
              {mergeMutation.isPending ? 'Merging...' : 'Confirm Merge'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
