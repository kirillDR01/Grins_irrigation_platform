import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
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
import { Plus, Send, BarChart3, Trash2 } from 'lucide-react';
import { cn } from '@/shared/utils/cn';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import {
  useCampaigns,
  useCreateCampaign,
  useDeleteCampaign,
  useSendCampaign,
  useCampaignStats,
} from '../hooks';
import type { CampaignType, CampaignStatus, Campaign } from '../types';

const campaignSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  campaign_type: z.enum(['EMAIL', 'SMS', 'BOTH']),
  subject: z.string().optional(),
  body: z.string().min(1, 'Message body is required'),
  scheduled_at: z.string().optional(),
});

type CampaignFormData = z.infer<typeof campaignSchema>;

const statusColors: Record<CampaignStatus, string> = {
  DRAFT: 'bg-slate-100 text-slate-700',
  SCHEDULED: 'bg-blue-100 text-blue-700',
  SENDING: 'bg-amber-100 text-amber-700',
  SENT: 'bg-emerald-100 text-emerald-700',
  CANCELLED: 'bg-red-100 text-red-700',
};

const typeLabels: Record<CampaignType, string> = {
  EMAIL: 'Email',
  SMS: 'SMS',
  BOTH: 'Email + SMS',
};

function CampaignStatsView({ campaignId }: { campaignId: string }) {
  const { data: stats, isLoading } = useCampaignStats(campaignId);

  if (isLoading) return <LoadingSpinner />;
  if (!stats) return <p className="text-sm text-slate-500">No stats available</p>;

  const statItems = [
    { label: 'Total', value: stats.total_recipients, color: 'text-slate-700' },
    { label: 'Sent', value: stats.sent, color: 'text-blue-600' },
    { label: 'Delivered', value: stats.delivered, color: 'text-emerald-600' },
    { label: 'Failed', value: stats.failed, color: 'text-red-600' },
    { label: 'Bounced', value: stats.bounced, color: 'text-amber-600' },
    { label: 'Opted Out', value: stats.opted_out, color: 'text-slate-500' },
  ];

  return (
    <div className="grid grid-cols-3 gap-3" data-testid="campaign-stats">
      {statItems.map((item) => (
        <div key={item.label} className="text-center p-2 rounded-lg bg-slate-50">
          <p className={cn('text-lg font-bold', item.color)}>{item.value}</p>
          <p className="text-xs text-slate-500">{item.label}</p>
        </div>
      ))}
    </div>
  );
}

export function CampaignManager() {
  const [createOpen, setCreateOpen] = useState(false);
  const [statsId, setStatsId] = useState<string | null>(null);
  const [confirmSendId, setConfirmSendId] = useState<string | null>(null);

  const { data: campaigns, isLoading, error } = useCampaigns();
  const createCampaign = useCreateCampaign();
  const deleteCampaign = useDeleteCampaign();
  const sendCampaign = useSendCampaign();

  const form = useForm<CampaignFormData>({
    resolver: zodResolver(campaignSchema),
    defaultValues: {
      name: '',
      campaign_type: 'EMAIL',
      subject: '',
      body: '',
      scheduled_at: '',
    },
  });

  const onSubmit = async (data: CampaignFormData) => {
    try {
      await createCampaign.mutateAsync({
        name: data.name,
        campaign_type: data.campaign_type,
        subject: data.subject || undefined,
        body: data.body,
        target_audience: {},
        scheduled_at: data.scheduled_at || undefined,
      });
      toast.success('Campaign created');
      form.reset();
      setCreateOpen(false);
    } catch {
      toast.error('Failed to create campaign');
    }
  };

  const handleSend = async (id: string) => {
    try {
      await sendCampaign.mutateAsync(id);
      toast.success('Campaign sent');
      setConfirmSendId(null);
    } catch {
      toast.error('Failed to send campaign');
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteCampaign.mutateAsync(id);
      toast.success('Campaign deleted');
    } catch {
      toast.error('Failed to delete campaign');
    }
  };

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorMessage error={error} />;

  const items: Campaign[] = campaigns?.items ?? [];

  return (
    <div className="space-y-6" data-testid="campaign-manager">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg">Campaigns</CardTitle>
            <Dialog open={createOpen} onOpenChange={setCreateOpen}>
              <DialogTrigger asChild>
                <Button size="sm" data-testid="create-campaign-btn">
                  <Plus className="h-4 w-4 mr-1" /> New Campaign
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-lg">
                <DialogHeader>
                  <DialogTitle>Create Campaign</DialogTitle>
                </DialogHeader>
                <form
                  onSubmit={form.handleSubmit(onSubmit)}
                  className="space-y-4"
                  data-testid="campaign-form"
                >
                  <div className="space-y-1">
                    <Label>Campaign Name</Label>
                    <Input
                      {...form.register('name')}
                      placeholder="Spring Promotion 2025"
                      data-testid="campaign-name-input"
                    />
                    {form.formState.errors.name && (
                      <p className="text-sm text-red-500">{form.formState.errors.name.message}</p>
                    )}
                  </div>

                  <div className="space-y-1">
                    <Label>Type</Label>
                    <Controller
                      control={form.control}
                      name="campaign_type"
                      render={({ field }) => (
                        <Select value={field.value} onValueChange={field.onChange}>
                          <SelectTrigger data-testid="campaign-type-select">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="EMAIL">Email</SelectItem>
                            <SelectItem value="SMS">SMS</SelectItem>
                            <SelectItem value="BOTH">Email + SMS</SelectItem>
                          </SelectContent>
                        </Select>
                      )}
                    />
                  </div>

                  <div className="space-y-1">
                    <Label>Subject (for email)</Label>
                    <Input
                      {...form.register('subject')}
                      placeholder="Check out our spring deals!"
                      data-testid="campaign-subject-input"
                    />
                  </div>

                  <div className="space-y-1">
                    <Label>Message Body</Label>
                    <Textarea
                      {...form.register('body')}
                      rows={4}
                      placeholder="Write your campaign message..."
                      data-testid="campaign-body-input"
                    />
                    {form.formState.errors.body && (
                      <p className="text-sm text-red-500">{form.formState.errors.body.message}</p>
                    )}
                  </div>

                  <div className="space-y-1">
                    <Label>Schedule (optional)</Label>
                    <Input
                      type="datetime-local"
                      {...form.register('scheduled_at')}
                      data-testid="campaign-schedule-input"
                    />
                  </div>

                  <Button
                    type="submit"
                    className="w-full"
                    disabled={createCampaign.isPending}
                    data-testid="submit-campaign-btn"
                  >
                    {createCampaign.isPending ? 'Creating...' : 'Create Campaign'}
                  </Button>
                </form>
              </DialogContent>
            </Dialog>
          </div>
        </CardHeader>
        <CardContent>
          {items.length === 0 ? (
            <p className="text-sm text-slate-500 text-center py-8">
              No campaigns yet. Create one to get started.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Scheduled</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((campaign) => (
                  <TableRow key={campaign.id} data-testid="campaign-row">
                    <TableCell className="font-medium">{campaign.name}</TableCell>
                    <TableCell>{typeLabels[campaign.campaign_type]}</TableCell>
                    <TableCell>
                      <Badge
                        className={cn('text-xs', statusColors[campaign.status])}
                        variant="secondary"
                        data-testid={`status-${campaign.status.toLowerCase()}`}
                      >
                        {campaign.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm text-slate-500">
                      {campaign.scheduled_at
                        ? new Date(campaign.scheduled_at).toLocaleString()
                        : '—'}
                    </TableCell>
                    <TableCell className="text-sm text-slate-500">
                      {new Date(campaign.created_at).toLocaleDateString()}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center justify-end gap-1">
                        {campaign.status === 'DRAFT' && (
                          <>
                            {confirmSendId === campaign.id ? (
                              <div className="flex items-center gap-1">
                                <Button
                                  size="sm"
                                  variant="destructive"
                                  onClick={() => handleSend(campaign.id)}
                                  disabled={sendCampaign.isPending}
                                  data-testid="confirm-send-btn"
                                >
                                  Confirm
                                </Button>
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => setConfirmSendId(null)}
                                  data-testid="cancel-send-btn"
                                >
                                  Cancel
                                </Button>
                              </div>
                            ) : (
                              <Button
                                size="icon"
                                variant="ghost"
                                onClick={() => setConfirmSendId(campaign.id)}
                                data-testid="send-campaign-btn"
                              >
                                <Send className="h-4 w-4 text-teal-500" />
                              </Button>
                            )}
                          </>
                        )}
                        {(campaign.status === 'SENT' || campaign.status === 'SENDING') && (
                          <Button
                            size="icon"
                            variant="ghost"
                            onClick={() =>
                              setStatsId(statsId === campaign.id ? null : campaign.id)
                            }
                            data-testid="view-stats-btn"
                          >
                            <BarChart3 className="h-4 w-4 text-blue-500" />
                          </Button>
                        )}
                        {campaign.status === 'DRAFT' && (
                          <Button
                            size="icon"
                            variant="ghost"
                            onClick={() => handleDelete(campaign.id)}
                            data-testid="delete-campaign-btn"
                          >
                            <Trash2 className="h-4 w-4 text-red-500" />
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Stats panel */}
      {statsId && (
        <Card data-testid="campaign-stats-panel">
          <CardHeader>
            <CardTitle className="text-lg">Campaign Delivery Stats</CardTitle>
          </CardHeader>
          <CardContent>
            <CampaignStatsView campaignId={statsId} />
          </CardContent>
        </Card>
      )}
    </div>
  );
}
