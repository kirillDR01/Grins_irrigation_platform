import { useState } from 'react';
import { Send, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useBulkOutreach } from '../hooks';

const MESSAGE_TEMPLATES = [
  {
    id: 'follow_up',
    label: 'Follow Up',
    body: "Hi {name}, this is Grin's Irrigation. We wanted to follow up on your inquiry. Are you still interested in our services? Reply YES to schedule a consultation.",
  },
  {
    id: 'estimate_ready',
    label: 'Estimate Ready',
    body: "Hi {name}, your estimate from Grin's Irrigation is ready! Please check your email for details or reply to this message with any questions.",
  },
  {
    id: 'seasonal',
    label: 'Seasonal Reminder',
    body: "Hi {name}, it's time to prepare your irrigation system for the season. Contact Grin's Irrigation to schedule your service. Reply YES to get started.",
  },
  {
    id: 'custom',
    label: 'Custom Message',
    body: '',
  },
];

interface BulkOutreachProps {
  selectedLeadIds: string[];
  onComplete?: () => void;
}

export function BulkOutreach({ selectedLeadIds, onComplete }: BulkOutreachProps) {
  const [open, setOpen] = useState(false);
  const [templateId, setTemplateId] = useState('');
  const [message, setMessage] = useState('');
  const bulkOutreach = useBulkOutreach();

  const handleTemplateChange = (id: string) => {
    setTemplateId(id);
    const template = MESSAGE_TEMPLATES.find((t) => t.id === id);
    if (template && template.id !== 'custom') {
      setMessage(template.body);
    } else {
      setMessage('');
    }
  };

  const handleSend = async () => {
    if (!message.trim()) {
      toast.error('Please enter a message');
      return;
    }
    try {
      const result = await bulkOutreach.mutateAsync({
        lead_ids: selectedLeadIds,
        message_template: message,
      });
      toast.success('Bulk Outreach Complete', {
        description: `Sent: ${result.sent_count}, Skipped: ${result.skipped_count}, Failed: ${result.failed_count}`,
      });
      setOpen(false);
      setTemplateId('');
      setMessage('');
      onComplete?.();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to send outreach';
      toast.error('Outreach Failed', { description: msg });
    }
  };

  return (
    <>
      <Button
        variant="outline"
        size="sm"
        onClick={() => setOpen(true)}
        disabled={selectedLeadIds.length === 0}
        data-testid="bulk-outreach-btn"
      >
        <Send className="mr-2 h-4 w-4" />
        Bulk Outreach ({selectedLeadIds.length})
      </Button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-lg" data-testid="bulk-outreach-dialog">
          <DialogHeader>
            <DialogTitle>Bulk Outreach</DialogTitle>
            <DialogDescription>
              Send a message to {selectedLeadIds.length} selected lead{selectedLeadIds.length !== 1 ? 's' : ''}.
              Leads without SMS consent will be skipped.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div>
              <label className="text-sm font-medium text-slate-700 mb-1.5 block">
                Message Template
              </label>
              <Select value={templateId} onValueChange={handleTemplateChange}>
                <SelectTrigger data-testid="template-selector">
                  <SelectValue placeholder="Select a template..." />
                </SelectTrigger>
                <SelectContent>
                  {MESSAGE_TEMPLATES.map((t) => (
                    <SelectItem key={t.id} value={t.id}>
                      {t.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <label className="text-sm font-medium text-slate-700 mb-1.5 block">
                Message
              </label>
              <Textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="Enter your message..."
                rows={5}
                data-testid="outreach-message"
              />
              <p className="text-xs text-slate-400 mt-1">
                Use {'{name}'} to personalize with the lead's name.
              </p>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleSend}
              disabled={bulkOutreach.isPending || !message.trim()}
              data-testid="send-outreach-btn"
            >
              {bulkOutreach.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Send className="mr-2 h-4 w-4" />
              )}
              Send to {selectedLeadIds.length} Leads
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
