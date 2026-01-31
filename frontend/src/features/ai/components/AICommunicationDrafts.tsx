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
import { Send, Clock, AlertTriangle, MessageSquare, Sparkles, Pencil, Trash2 } from 'lucide-react';
import { AILoadingState } from './AILoadingState';
import { AIErrorState } from './AIErrorState';
import type { CommunicationDraft } from '../types';

interface AICommunicationDraftsProps {
  draft: CommunicationDraft | null;
  drafts?: CommunicationDraft[];
  isLoading?: boolean;
  error?: Error | null;
  onSendNow?: (draftId: string) => void;
  onEdit?: (draftId: string) => void;
  onScheduleLater?: (draftId: string) => void;
  onDelete?: (draftId: string) => void;
  onGenerateNew?: () => void;
}

export function AICommunicationDrafts({
  draft,
  drafts = [],
  isLoading = false,
  error = null,
  onSendNow,
  onEdit,
  onScheduleLater,
  onDelete,
  onGenerateNew,
}: AICommunicationDraftsProps) {
  if (isLoading) {
    return <AILoadingState />;
  }

  if (error) {
    return <AIErrorState error={error} onRetry={() => window.location.reload()} />;
  }

  // Use drafts array if provided, otherwise use single draft
  const draftList = drafts.length > 0 ? drafts : (draft ? [draft] : []);

  // Empty state
  if (draftList.length === 0) {
    return (
      <Card 
        data-testid="ai-communication-drafts-empty" 
        className="bg-white rounded-2xl shadow-sm border border-slate-100"
      >
        <CardHeader className="p-6 border-b border-slate-100">
          <CardTitle className="flex items-center justify-between">
            <span className="flex items-center gap-2 font-bold text-slate-800 text-lg">
              <MessageSquare className="h-5 w-5 text-teal-500" />
              AI Communication Drafts
            </span>
            <Button
              data-testid="generate-draft-btn"
              onClick={onGenerateNew}
              size="sm"
              className="bg-teal-500 hover:bg-teal-600 text-white"
            >
              <Sparkles className="mr-2 h-4 w-4" />
              Generate New
            </Button>
          </CardTitle>
        </CardHeader>
        <CardContent className="text-center py-8">
          <MessageSquare className="h-12 w-12 text-slate-300 mx-auto mb-3" />
          <p className="text-slate-500 text-sm">No draft available. Generate a communication draft to get started.</p>
        </CardContent>
      </Card>
    );
  }

  // Format message type for display
  const formatMessageType = (type: string) => {
    return type.replace(/_/g, ' ');
  };

  return (
    <Card 
      data-testid="ai-communication-drafts" 
      className="bg-white rounded-2xl shadow-sm border border-slate-100"
    >
      <CardHeader className="p-6 border-b border-slate-100">
        <CardTitle className="flex items-center justify-between">
          <span className="flex items-center gap-2 font-bold text-slate-800 text-lg">
            <MessageSquare className="h-5 w-5 text-teal-500" />
            AI Communication Drafts
          </span>
          <Button
            data-testid="generate-draft-btn"
            onClick={onGenerateNew}
            size="sm"
            className="bg-teal-500 hover:bg-teal-600 text-white"
          >
            <Sparkles className="mr-2 h-4 w-4" />
            Generate New
          </Button>
        </CardTitle>
      </CardHeader>
      <CardContent className="p-6 space-y-4">
        {draftList.map((draftItem) => (
          <div
            key={draftItem.draft_id}
            data-testid="draft-item"
            className="bg-slate-50 rounded-xl p-4 hover:bg-slate-100 transition-colors"
          >
            {/* Draft Header */}
            <div className="flex items-start justify-between mb-3">
              <div>
                <div className="font-medium text-slate-700">{draftItem.customer_name}</div>
                <div className="text-xs text-slate-400">{draftItem.customer_phone}</div>
              </div>
              <Badge variant="outline" className="text-xs">
                {formatMessageType(draftItem.message_type)}
              </Badge>
            </div>

            {/* Draft Message */}
            <div 
              data-testid="draft-message"
              className="text-sm text-slate-500 line-clamp-2 mb-3"
            >
              {draftItem.message_content}
            </div>

            {/* AI Notes */}
            {draftItem.ai_notes && (
              <Alert className="mb-3 py-2">
                <AlertDescription data-testid="ai-notes" className="text-xs">
                  <strong>AI Note:</strong> {draftItem.ai_notes}
                </AlertDescription>
              </Alert>
            )}

            {/* Slow Payer Warning */}
            {draftItem.is_slow_payer && (
              <Alert variant="destructive" className="mb-3 py-2">
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription data-testid="slow-payer-warning" className="text-xs">
                  Slow payer - follow up promptly
                </AlertDescription>
              </Alert>
            )}

            {/* Actions */}
            <div className="flex items-center gap-2">
              <Button
                data-testid="edit-draft-btn"
                variant="ghost"
                size="sm"
                onClick={() => onEdit?.(draftItem.draft_id)}
                className="text-slate-600 hover:text-slate-800"
              >
                <Pencil className="h-4 w-4" />
              </Button>
              <Button
                data-testid="send-now-btn"
                size="sm"
                onClick={() => onSendNow?.(draftItem.draft_id)}
                className="bg-teal-500 hover:bg-teal-600 text-white"
              >
                <Send className="mr-1 h-3 w-3" />
                Send Now
              </Button>
              <Button
                data-testid="schedule-later-btn"
                variant="ghost"
                size="sm"
                onClick={() => onScheduleLater?.(draftItem.draft_id)}
                className="text-slate-600 hover:text-slate-800"
              >
                <Clock className="h-4 w-4" />
              </Button>
              <Button
                data-testid="delete-draft-btn"
                variant="ghost"
                size="sm"
                onClick={() => onDelete?.(draftItem.draft_id)}
                className="text-red-500 hover:text-red-600 hover:bg-red-50 ml-auto"
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
