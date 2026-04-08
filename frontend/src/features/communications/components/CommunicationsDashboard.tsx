import { useState, useCallback } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { MessageSquarePlus } from 'lucide-react';
import { CommunicationsQueue } from './CommunicationsQueue';
import { SentMessagesLog } from './SentMessagesLog';
import { CampaignsList } from './CampaignsList';
import { FailedRecipientsDetail } from './FailedRecipientsDetail';
import { NewTextCampaignModal } from './NewTextCampaignModal';
import type { Campaign } from '../types/campaign';

export function CommunicationsDashboard() {
  const [activeTab, setActiveTab] = useState('needs-attention');
  const [campaignModalOpen, setCampaignModalOpen] = useState(false);
  const [selectedCampaign, setSelectedCampaign] = useState<Campaign | null>(null);

  const handleSelectCampaign = useCallback((campaign: Campaign) => {
    setSelectedCampaign(campaign);
  }, []);

  const handleBackFromDetail = useCallback(() => {
    setSelectedCampaign(null);
  }, []);

  return (
    <div data-testid="communications-page" className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Communications</h1>
          <p className="text-sm text-slate-500 mt-1">
            Manage inbound messages, outbound notifications, and text campaigns
          </p>
        </div>
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
          {selectedCampaign ? (
            <FailedRecipientsDetail
              campaign={selectedCampaign}
              onBack={handleBackFromDetail}
            />
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
