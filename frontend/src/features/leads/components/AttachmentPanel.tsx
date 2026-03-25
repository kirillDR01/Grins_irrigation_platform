import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, Download, Trash2, FileText, File, Loader2, ExternalLink } from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useLeadAttachments, useUploadAttachment, useDeleteAttachment } from '../hooks';
import type { LeadAttachment, AttachmentType } from '../types';

const ACCEPTED_TYPES = '.pdf,.docx,.jpeg,.jpg,.png';
const MAX_FILE_SIZE = 25 * 1024 * 1024; // 25MB

const TYPE_LABELS: Record<AttachmentType, string> = {
  ESTIMATE: 'Estimates',
  CONTRACT: 'Contracts',
  OTHER: 'Other',
};

const TYPE_ICONS: Record<AttachmentType, typeof FileText> = {
  ESTIMATE: FileText,
  CONTRACT: File,
  OTHER: File,
};

interface AttachmentPanelProps {
  leadId: string;
}

export function AttachmentPanel({ leadId }: AttachmentPanelProps) {
  const navigate = useNavigate();
  const { data: attachments, isLoading } = useLeadAttachments(leadId);
  const uploadMutation = useUploadAttachment();
  const deleteMutation = useDeleteAttachment();
  const [uploadType, setUploadType] = useState<AttachmentType>('OTHER');
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);

  const handleFileUpload = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (!files?.length) return;

      const file = files[0];
      if (file.size > MAX_FILE_SIZE) {
        toast.error('File too large', { description: 'Maximum file size is 25MB.' });
        return;
      }

      try {
        await uploadMutation.mutateAsync({
          leadId,
          file,
          attachmentType: uploadType,
        });
        toast.success('File uploaded', { description: file.name });
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Upload failed';
        toast.error('Upload Failed', { description: msg });
      }
      // Reset input
      e.target.value = '';
    },
    [leadId, uploadType, uploadMutation]
  );

  const handleDelete = async (attachment: LeadAttachment) => {
    try {
      await deleteMutation.mutateAsync({
        leadId,
        attachmentId: attachment.id,
      });
      toast.success('File deleted', { description: attachment.file_name });
      setDeleteConfirmId(null);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Delete failed';
      toast.error('Delete Failed', { description: msg });
    }
  };

  const grouped = (attachments ?? []).reduce<Record<AttachmentType, LeadAttachment[]>>(
    (acc, att) => {
      const type = att.attachment_type as AttachmentType;
      if (!acc[type]) acc[type] = [];
      acc[type].push(att);
      return acc;
    },
    { ESTIMATE: [], CONTRACT: [], OTHER: [] }
  );

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <Card className="bg-white rounded-2xl shadow-sm border border-slate-100" data-testid="attachment-panel">
      <CardHeader className="border-b border-slate-100">
        <CardTitle className="font-bold text-slate-800">Attachments</CardTitle>
      </CardHeader>
      <CardContent className="p-6 space-y-6">
        {/* Upload Section */}
        <div className="flex items-center gap-3" data-testid="attachment-upload">
          <Select value={uploadType} onValueChange={(v) => setUploadType(v as AttachmentType)}>
            <SelectTrigger className="w-[140px]" data-testid="attachment-type-select">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ESTIMATE">Estimate</SelectItem>
              <SelectItem value="CONTRACT">Contract</SelectItem>
              <SelectItem value="OTHER">Other</SelectItem>
            </SelectContent>
          </Select>
          <label className="cursor-pointer">
            <input
              type="file"
              accept={ACCEPTED_TYPES}
              onChange={handleFileUpload}
              className="hidden"
              data-testid="attachment-file-input"
            />
            <Button
              variant="outline"
              size="sm"
              asChild
              disabled={uploadMutation.isPending}
            >
              <span>
                {uploadMutation.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Upload className="mr-2 h-4 w-4" />
                )}
                Upload File
              </span>
            </Button>
          </label>
        </div>

        {/* Grouped Attachments */}
        {isLoading ? (
          <p className="text-sm text-slate-400">Loading attachments...</p>
        ) : (
          (['ESTIMATE', 'CONTRACT', 'OTHER'] as AttachmentType[]).map((type) => {
            const items = grouped[type];
            if (items.length === 0) return null;
            const Icon = TYPE_ICONS[type];
            return (
              <div key={type} data-testid={`attachment-group-${type.toLowerCase()}`}>
                <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
                  {TYPE_LABELS[type]} ({items.length})
                  {type === 'ESTIMATE' && items.length > 0 && (
                    <button
                      type="button"
                      onClick={() => navigate(`/sales?tab=estimates`)}
                      className="ml-2 text-blue-500 hover:text-blue-700 normal-case font-medium inline-flex items-center gap-1"
                      data-testid="view-estimate-details-link"
                    >
                      <ExternalLink className="h-3 w-3" />
                      View Details
                    </button>
                  )}
                </h4>
                <div className="space-y-2">
                  {items.map((att) => (
                    <div
                      key={att.id}
                      className="flex items-center justify-between p-3 bg-slate-50 rounded-lg"
                      data-testid={`attachment-${att.id}`}
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <Icon className="h-4 w-4 text-slate-500 shrink-0" />
                        <div className="min-w-0">
                          <p className="text-sm font-medium text-slate-700 truncate">
                            {att.file_name}
                          </p>
                          <p className="text-xs text-slate-400">
                            {formatFileSize(att.file_size)}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-1 shrink-0">
                        {att.download_url && (
                          <Button
                            variant="ghost"
                            size="sm"
                            asChild
                            data-testid={`download-${att.id}`}
                          >
                            <a href={att.download_url} target="_blank" rel="noopener noreferrer">
                              <Download className="h-4 w-4" />
                            </a>
                          </Button>
                        )}
                        {deleteConfirmId === att.id ? (
                          <div className="flex items-center gap-1">
                            <Button
                              variant="destructive"
                              size="sm"
                              onClick={() => handleDelete(att)}
                              disabled={deleteMutation.isPending}
                              data-testid={`confirm-delete-${att.id}`}
                            >
                              {deleteMutation.isPending ? (
                                <Loader2 className="h-3 w-3 animate-spin" />
                              ) : (
                                'Delete'
                              )}
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => setDeleteConfirmId(null)}
                            >
                              Cancel
                            </Button>
                          </div>
                        ) : (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setDeleteConfirmId(att.id)}
                            data-testid={`delete-btn-${att.id}`}
                          >
                            <Trash2 className="h-4 w-4 text-slate-400 hover:text-red-500" />
                          </Button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })
        )}

        {!isLoading && (attachments ?? []).length === 0 && (
          <p className="text-sm text-slate-400 text-center py-4">
            No attachments yet. Upload files to get started.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
