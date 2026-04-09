/**
 * DraftCampaignDetail — lightweight detail view for draft campaigns.
 *
 * Shows campaign info and allows deletion. Full resume/edit
 * (pre-populating the wizard) is a larger feature left for later.
 */

import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useDeleteCampaign } from '../hooks';
import type { Campaign } from '../types/campaign';

export interface DraftCampaignDetailProps {
  campaign: Campaign;
  onBack: () => void;
}

export function DraftCampaignDetail({ campaign, onBack }: DraftCampaignDetailProps) {
  const deleteMutation = useDeleteCampaign();

  const handleDelete = async () => {
    try {
      await deleteMutation.mutateAsync(campaign.id);
      toast.success('Draft campaign deleted.');
      onBack();
    } catch {
      toast.error('Failed to delete draft campaign.');
    }
  };

  return (
    <Card data-testid="draft-campaign-detail">
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={onBack} data-testid="back-btn">
            ← Back
          </Button>
          <CardTitle className="text-base font-semibold">{campaign.name}</CardTitle>
          <Badge variant="secondary">Draft</Badge>
        </div>
        <Button
          size="sm"
          variant="destructive"
          onClick={handleDelete}
          disabled={deleteMutation.isPending}
          data-testid="delete-draft-btn"
        >
          {deleteMutation.isPending ? 'Deleting...' : 'Delete Draft'}
        </Button>
      </CardHeader>

      <CardContent className="space-y-4">
        <div className="text-sm text-slate-600">
          <p>
            <span className="font-medium text-slate-700">Created:</span>{' '}
            {new Date(campaign.created_at).toLocaleString()}
          </p>
        </div>

        {campaign.body && (
          <div className="rounded-lg border border-slate-200 p-4 space-y-2">
            <h4 className="text-sm font-semibold text-slate-700">Message</h4>
            <p className="text-sm text-slate-600 whitespace-pre-wrap">{campaign.body}</p>
          </div>
        )}

        {!campaign.body && (
          <p className="text-sm text-slate-400 italic">No message body yet.</p>
        )}
      </CardContent>
    </Card>
  );
}
