import { useRef, useCallback } from 'react';
import { toast } from 'sonner';
import { Upload, Download, Trash2, FileText } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  useSalesDocuments,
  useUploadSalesDocument,
  useDownloadSalesDocument,
  useDeleteSalesDocument,
} from '../hooks/useSalesPipeline';

const MAX_SIZE = 25 * 1024 * 1024; // 25 MB
const ALLOWED_TYPES = [
  'application/pdf',
  'image/jpeg',
  'image/png',
  'image/webp',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
];

interface DocumentsSectionProps {
  customerId: string;
}

export function DocumentsSection({ customerId }: DocumentsSectionProps) {
  const fileRef = useRef<HTMLInputElement>(null);
  const { data: documents, isLoading } = useSalesDocuments(customerId);
  const upload = useUploadSalesDocument();
  const download = useDownloadSalesDocument();
  const remove = useDeleteSalesDocument();

  const handleUpload = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;
      if (file.size > MAX_SIZE) {
        toast.error('File too large (max 25 MB)');
        return;
      }
      if (!ALLOWED_TYPES.includes(file.type)) {
        toast.error('Unsupported file type');
        return;
      }
      try {
        await upload.mutateAsync({
          customerId,
          file,
          documentType: file.type.startsWith('image/') ? 'photo' : 'contract',
        });
        toast.success('Document uploaded');
      } catch {
        toast.error('Upload failed');
      }
      if (fileRef.current) fileRef.current.value = '';
    },
    [customerId, upload],
  );

  const handleDownload = useCallback(
    async (docId: string) => {
      try {
        const result = await download.mutateAsync({
          customerId,
          documentId: docId,
        });
        window.open(result.download_url, '_blank');
      } catch {
        toast.error('Download failed');
      }
    },
    [customerId, download],
  );

  const handleDelete = useCallback(
    async (docId: string) => {
      try {
        await remove.mutateAsync({ customerId, documentId: docId });
        toast.success('Document deleted');
      } catch {
        toast.error('Delete failed');
      }
    },
    [customerId, remove],
  );

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <Card data-testid="documents-section">
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <CardTitle className="text-base">Documents</CardTitle>
        <div>
          <input
            ref={fileRef}
            type="file"
            className="hidden"
            accept=".pdf,.jpg,.jpeg,.png,.webp,.doc,.docx"
            onChange={handleUpload}
            data-testid="document-upload-input"
          />
          <Button
            size="sm"
            variant="outline"
            onClick={() => fileRef.current?.click()}
            disabled={upload.isPending}
            data-testid="upload-document-btn"
          >
            <Upload className="mr-1 h-3.5 w-3.5" />
            {upload.isPending ? 'Uploading…' : 'Upload'}
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <p className="text-sm text-slate-400">Loading…</p>
        ) : !documents?.length ? (
          <p className="text-sm text-slate-400">No documents yet.</p>
        ) : (
          <ul className="divide-y divide-slate-100">
            {documents.map((doc) => (
              <li
                key={doc.id}
                className="flex items-center justify-between py-2"
                data-testid="document-row"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <FileText className="h-4 w-4 text-slate-400 shrink-0" />
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-slate-700 truncate">
                      {doc.file_name}
                    </p>
                    <p className="text-xs text-slate-400">
                      {doc.document_type} · {formatSize(doc.size_bytes)}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleDownload(doc.id)}
                    data-testid={`download-doc-${doc.id}`}
                  >
                    <Download className="h-3.5 w-3.5" />
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="text-red-500 hover:text-red-700"
                    onClick={() => handleDelete(doc.id)}
                    data-testid={`delete-doc-${doc.id}`}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
