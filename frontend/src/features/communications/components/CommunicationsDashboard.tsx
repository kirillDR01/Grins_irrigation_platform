import { useState, useCallback } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { MessageSquarePlus } from 'lucide-react';
import { CommunicationsQueue } from './CommunicationsQueue';
import { SentMessagesLog } from './SentMessagesLog';
import { CampaignsList } from './CampaignsList';
import { FailedRecipientsDetail } from './FailedRecipientsDetail';
import { CampaignResponsesView } from './CampaignResponsesView';
import { DraftCampaignDetail } from './DraftCampaignDetail';
import { NewTextCampaignModal } from './NewTextCampaignModal';
import { useCampaign } from '../hooks/useCampaigns';
import type { Campaign } from '../types/campaign';

export function CommunicationsDashboard() {
  const [activeTab, setActiveTab] = useState('needs-attention');
  const [campaignModalOpen, setCampaignModalOpen] = useState(false);
  const [selectedCampaignId, setSelectedCampaignId] = useState<string | null>(null);
  const { data: selectedCampaign } = useCampaign(selectedCampaignId ?? '');

  const handleSelectCampaign = useCallback((campaign: Campaign) => {
    setSelectedCampaignId(campaign.id);
  }, []);

  const handleBackFromDetail = useCallback(() => {
    setSelectedCampaignId(null);
  }, []);

  return (
    <div data-testid="communications-page" className="space-y-6">
      <div className="flex items-center justify-end">
        <Button
          onClick={() => setCampaignModalOpen(true)}
          data-testid="new-text-campaign-btn"
        >
          <MessageSquarePlus className="mr-2 h-4 w-4" />
          New Text Campaign
        </Button>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList data-testid="communications-tabs">
          <TabsTrigger
            value="needs-attention"
            data-testid="tab-needs-attention"
          >
            Needs Attention
          </TabsTrigger>
          <TabsTrigger
            value="sent-messages"
            data-testid="tab-sent-messages"
          >
            Sent Messages
          </TabsTrigger>
          <TabsTrigger
            value="campaigns"
            data-testid="tab-campaigns"
          >
            Campaigns
          </TabsTrigger>
        </TabsList>

        <TabsContent value="needs-attention" className="mt-4">
          <CommunicationsQueue />
        </TabsContent>

        <TabsContent value="sent-messages" className="mt-4">
          <SentMessagesLog />
        </TabsContent>

        <TabsContent value="campaigns" className="mt-4">
          {selectedCampaignId ? (
            selectedCampaign ? (
              selectedCampaign.status === 'draft' ? (
                <DraftCampaignDetail
                  campaign={selectedCampaign}
                  onBack={handleBackFromDetail}
                />
              ) : selectedCampaign.poll_options != null ? (
                <CampaignResponsesView
                  campaign={selectedCampaign}
                  onBack={handleBackFromDetail}
                />
              ) : (
                <FailedRecipientsDetail
                  campaign={selectedCampaign}
                  onBack={handleBackFromDetail}
                />
              )
            ) : null
          ) : (
            <CampaignsList onSelectCampaign={handleSelectCampaign} />
          )}
        </TabsContent>
      </Tabs>

      <NewTextCampaignModal
        open={campaignModalOpen}
        onOpenChange={setCampaignModalOpen}
      />
    </div>
  );
}
