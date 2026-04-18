/**
 * AppointmentAttachments — file upload and preview for appointment modals.
 *
 * Supports multiple files, any MIME type, 25 MB cap per file.
 * Renders image thumbnails, PDF icons, and generic file icons.
 *
 * Validates: april-16th-fixes-enhancements Requirement 10C
 */

import { useRef } from 'react';
import { Paperclip, Trash2, FileText, Image, File, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { getErrorMessage } from '@/core/api';
import {
  useAppointmentAttachments,
  useUploadAppointmentAttachment,
  useDeleteAppointmentAttachment,
} from '@/shared/hooks/useAppointmentAttachments';
import type { AppointmentAttachment } from '@/shared/hooks/useAppointmentAttachments';

interface AppointmentAttachmentsProps {
  appointmentId: string;
}

function getFileIcon(contentType: string) {
  if (contentType.startsWith('image/')) return Image;
  if (contentType === 'application/pdf') return FileText;
  return File;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function AttachmentPreview({
  attachment,
  onDelete,
  isDeleting,
}: {
  attachment: AppointmentAttachment;
  onDelete: () => void;
  isDeleting: boolean;
}) {
  const Icon = getFileIcon(attachment.content_type);
  const isImage = attachment.content_type.startsWith('image/');

  return (
    <div
      className="flex items-center gap-2 p-2 rounded-lg border border-slate-200 bg-white group"
      data-testid={`attachment-${attachment.id}`}
    >
      {isImage && attachment.download_url ? (
        <a
          href={attachment.download_url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex-shrink-0"
        >
          <img
            src={attachment.download_url}
            alt={attachment.file_name}
            className="h-10 w-10 rounded object-cover"
          />
        </a>
      ) : (
        <div className="h-10 w-10 rounded bg-slate-100 flex items-center justify-center flex-shrink-0">
          <Icon className="h-5 w-5 text-slate-500" />
        </div>
      )}
      <div className="flex-1 min-w-0">
        <p className="text-xs font-medium text-slate-700 truncate">
          {attachment.file_name}
        </p>
        <p className="text-[10px] text-slate-400">
          {formatFileSize(attachment.file_size)}
        </p>
      </div>
      <Button
        variant="ghost"
        size="sm"
        className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100 transition-opacity text-red-500 hover:text-red-700"
        onClick={onDelete}
        disabled={isDeleting}
        data-testid={`delete-attachment-${attachment.id}`}
      >
        {isDeleting ? (
          <Loader2 className="h-3 w-3 animate-spin" />
        ) : (
          <Trash2 className="h-3 w-3" />
        )}
      </Button>
    </div>
  );
}

export function AppointmentAttachments({ appointmentId }: AppointmentAttachmentsProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { data: attachments, isLoading } = useAppointmentAttachments(appointmentId);
  const uploadMutation = useUploadAppointmentAttachment(appointmentId);
  const deleteMutation = useDeleteAppointmentAttachment(appointmentId);

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;

    for (const file of Array.from(files)) {
      try {
        await uploadMutation.mutateAsync(file);
        toast.success(`Uploaded ${file.name}`);
      } catch (err: unknown) {
        toast.error(`Failed to upload ${file.name}`, {
          description: getErrorMessage(err),
        });
      }
    }

    // Reset input so the same file can be re-selected
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleDelete = async (attachmentId: string) => {
    try {
      await deleteMutation.mutateAsync(attachmentId);
      toast.success('Attachment deleted');
    } catch (err: unknown) {
      toast.error('Failed to delete attachment', {
        description: getErrorMessage(err),
      });
    }
  };

  return (
    <div className="space-y-2" data-testid="appointment-attachments">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
          Attachments
        </p>
        <Button
          variant="outline"
          size="sm"
          className="h-7 text-xs"
          onClick={() => fileInputRef.current?.click()}
          disabled={uploadMutation.isPending}
          data-testid="attach-files-btn"
        >
          {uploadMutation.isPending ? (
            <Loader2 className="h-3 w-3 mr-1 animate-spin" />
          ) : (
            <Paperclip className="h-3 w-3 mr-1" />
          )}
          Attach files
        </Button>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          className="hidden"
          onChange={handleFileSelect}
          data-testid="file-input"
        />
      </div>

      {isLoading && (
        <div className="flex justify-center py-3">
          <Loader2 className="h-4 w-4 animate-spin text-slate-400" />
        </div>
      )}

      {attachments && attachments.length > 0 && (
        <div className="space-y-1.5">
          {attachments.map((att) => (
            <AttachmentPreview
              key={att.id}
              attachment={att}
              onDelete={() => handleDelete(att.id)}
              isDeleting={deleteMutation.isPending}
            />
          ))}
        </div>
      )}

      {!isLoading && (!attachments || attachments.length === 0) && (
        <p className="text-xs text-slate-400 italic">No attachments</p>
      )}
    </div>
  );
}
