import { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { CommunicationsQueue } from './CommunicationsQueue';
import { SentMessagesLog } from './SentMessagesLog';

export function CommunicationsDashboard() {
  const [activeTab, setActiveTab] = useState('needs-attention');

  return (
    <div data-testid="communications-page" className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Communications</h1>
        <p className="text-sm text-slate-500 mt-1">
          Manage inbound messages and view outbound notification history
        </p>
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
        </TabsList>

        <TabsContent value="needs-attention" className="mt-4">
          <CommunicationsQueue />
        </TabsContent>

        <TabsContent value="sent-messages" className="mt-4">
          <SentMessagesLog />
        </TabsContent>
      </Tabs>
    </div>
  );
}
