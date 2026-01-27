/**
 * AICommunicationDrafts Component
 * 
 * AI-powered communication draft interface
 * Displays draft messages with recipient info and provides
 * send, edit, and schedule actions
 */

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Send, Edit, Clock, AlertTriangle } from 'lucide-react';
import { AILoadingState } from './AILoadingState';
import { AIErrorState } from './AIErrorState';
import type { CommunicationDraft } from '../types';

interface AICommunicationDraftsProps {
  draft: CommunicationDraft | null;
  isLoading?: boolean;
  error?: Error | null;
  onSendNow?: (draftId: string) => void;
  onEdit?: (draftId: string) => void;
  onScheduleLater?: (draftId: string) => void;
}

export function AICommunicationDrafts({
  draft,
  isLoading = false,
  error = null,
  onSendNow,
  onEdit,
  onScheduleLater,
}: AICommunicationDraftsProps) {
  if (isLoading) {
    return <AILoadingState message="AI is drafting message..." />;
  }

  if (error) {
    return <AIErrorState error={error} onRetry={() => window.location.reload()} />;
  }

  if (!draft) {
    return (
      <Card data-testid="ai-communication-drafts">
        <CardContent className="py-8 text-center text-muted-foreground">
          No draft available. Generate a communication draft to get started.
        </CardContent>
      </Card>
    );
  }

  return (
    <Card data-testid="ai-communication-drafts">
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>AI Communication Draft</span>
          <Badge variant="outline">{draft.message_type.replace(/_/g, ' ')}</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Recipient Info */}
        <div className="space-y-2">
          <div className="text-sm font-medium">Recipient</div>
          <div className="text-sm text-muted-foreground">
            <div>{draft.customer_name}</div>
            <div>{draft.customer_phone}</div>
          </div>
        </div>

        {/* Draft Message */}
        <div className="space-y-2">
          <div className="text-sm font-medium">Message</div>
          <div 
            data-testid="draft-message"
            className="rounded-md border bg-muted/50 p-4 text-sm"
          >
            {draft.message_content}
          </div>
        </div>

        {/* AI Notes */}
        {draft.ai_notes && (
          <Alert>
            <AlertDescription data-testid="ai-notes">
              <strong>AI Note:</strong> {draft.ai_notes}
            </AlertDescription>
          </Alert>
        )}

        {/* Slow Payer Warning */}
        {draft.is_slow_payer && (
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription data-testid="slow-payer-warning">
              This customer has a history of slow payments. Consider following up promptly.
            </AlertDescription>
          </Alert>
        )}

        {/* Actions */}
        <div className="flex gap-2">
          <Button
            data-testid="send-now-btn"
            onClick={() => onSendNow?.(draft.draft_id)}
            className="flex-1"
          >
            <Send className="mr-2 h-4 w-4" />
            Send Now
          </Button>
          <Button
            data-testid="edit-draft-btn"
            variant="outline"
            onClick={() => onEdit?.(draft.draft_id)}
          >
            <Edit className="mr-2 h-4 w-4" />
            Edit
          </Button>
          <Button
            data-testid="schedule-later-btn"
            variant="outline"
            onClick={() => onScheduleLater?.(draft.draft_id)}
          >
            <Clock className="mr-2 h-4 w-4" />
            Schedule
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
