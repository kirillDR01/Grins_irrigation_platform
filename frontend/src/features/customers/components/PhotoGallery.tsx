import { useState, useCallback } from 'react';
import { Upload, Trash2, Edit2, Check, X, ImageIcon } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Skeleton } from '@/components/ui/skeleton';
import { useCustomerPhotos, useUploadCustomerPhotos, useUpdatePhotoCaption, useDeleteCustomerPhoto } from '../hooks';
import { toast } from 'sonner';

const ACCEPTED_TYPES = ['image/jpeg', 'image/png', 'image/heic', 'image/heif'];
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

interface PhotoGalleryProps {
  customerId: string;
}

export function PhotoGallery({ customerId }: PhotoGalleryProps) {
  const { data: photos, isLoading, error } = useCustomerPhotos(customerId);
  const uploadMutation = useUploadCustomerPhotos(customerId);
  const captionMutation = useUpdatePhotoCaption(customerId);
  const deleteMutation = useDeleteCustomerPhoto(customerId);

  const [editingCaptionId, setEditingCaptionId] = useState<string | null>(null);
  const [captionValue, setCaptionValue] = useState('');
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);

  const validateAndUpload = useCallback(
    async (files: FileList | File[]) => {
      const validFiles: File[] = [];
      for (const file of Array.from(files)) {
        if (!ACCEPTED_TYPES.includes(file.type)) {
          toast.error(`${file.name}: unsupported file type. Use JPEG, PNG, or HEIC.`);
          continue;
        }
        if (file.size > MAX_FILE_SIZE) {
          toast.error(`${file.name}: exceeds 10MB limit.`);
          continue;
        }
        validFiles.push(file);
      }
      if (validFiles.length === 0) return;
      if (validFiles.length > 5) {
        toast.error('Maximum 5 files per upload.');
        return;
      }
      try {
        await uploadMutation.mutateAsync({ files: validFiles });
        toast.success(`${validFiles.length} photo(s) uploaded`);
      } catch {
        toast.error('Failed to upload photos');
      }
    },
    [uploadMutation]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      if (e.dataTransfer.files.length > 0) {
        validateAndUpload(e.dataTransfer.files);
      }
    },
    [validateAndUpload]
  );

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files && e.target.files.length > 0) {
        validateAndUpload(e.target.files);
        e.target.value = '';
      }
    },
    [validateAndUpload]
  );

  const handleSaveCaption = async (photoId: string) => {
    try {
      await captionMutation.mutateAsync({ photoId, caption: captionValue });
      setEditingCaptionId(null);
      toast.success('Caption updated');
    } catch {
      toast.error('Failed to update caption');
    }
  };

  const handleDelete = async (photoId: string) => {
    try {
      await deleteMutation.mutateAsync(photoId);
      setDeleteConfirmId(null);
      toast.success('Photo deleted');
    } catch {
      toast.error('Failed to delete photo');
    }
  };

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4" data-testid="photos-loading">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="aspect-square rounded-lg" />
        ))}
      </div>
    );
  }

  if (error) {
    return <p className="text-red-600 text-sm" data-testid="photos-error">Failed to load photos.</p>;
  }

  return (
    <div data-testid="photo-gallery" className="space-y-4">
      {/* Upload dropzone */}
      <div
        data-testid="photo-dropzone"
        onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
          isDragOver ? 'border-teal-400 bg-teal-50' : 'border-slate-200 hover:border-slate-300'
        }`}
      >
        <Upload className="h-8 w-8 text-slate-400 mx-auto mb-2" />
        <p className="text-sm text-slate-600 mb-2">
          Drag & drop photos here, or{' '}
          <label className="text-teal-600 cursor-pointer hover:underline">
            browse
            <input
              type="file"
              className="hidden"
              multiple
              accept=".jpg,.jpeg,.png,.heic,.heif"
              onChange={handleFileInput}
              data-testid="photo-file-input"
            />
          </label>
        </p>
        <p className="text-xs text-slate-400">JPEG, PNG, HEIC — max 10MB, up to 5 files</p>
        {uploadMutation.isPending && (
          <p className="text-sm text-teal-600 mt-2">Uploading...</p>
        )}
      </div>

      {/* Photo grid */}
      {photos && photos.length > 0 ? (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4" data-testid="photo-grid">
          {photos.map((photo) => (
            <div
              key={photo.id}
              className="group relative rounded-lg overflow-hidden border border-slate-100 bg-white"
              data-testid={`photo-${photo.id}`}
            >
              <img
                src={photo.download_url}
                alt={photo.caption || photo.file_name}
                className="aspect-square object-cover w-full"
                loading="lazy"
              />
              {/* Overlay actions */}
              <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition-colors flex items-end">
                <div className="w-full p-2 opacity-0 group-hover:opacity-100 transition-opacity flex justify-between items-center">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-white hover:bg-white/20 h-7 px-2"
                    onClick={() => {
                      setEditingCaptionId(photo.id);
                      setCaptionValue(photo.caption || '');
                    }}
                    data-testid={`edit-caption-${photo.id}`}
                  >
                    <Edit2 className="h-3.5 w-3.5" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-red-300 hover:bg-white/20 h-7 px-2"
                    onClick={() => setDeleteConfirmId(photo.id)}
                    data-testid={`delete-photo-${photo.id}`}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>
              {/* Caption display */}
              {editingCaptionId === photo.id ? (
                <div className="p-2 flex gap-1">
                  <Input
                    value={captionValue}
                    onChange={(e) => setCaptionValue(e.target.value)}
                    className="h-7 text-xs"
                    placeholder="Add caption..."
                    data-testid={`caption-input-${photo.id}`}
                  />
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 px-1.5"
                    onClick={() => handleSaveCaption(photo.id)}
                    disabled={captionMutation.isPending}
                  >
                    <Check className="h-3.5 w-3.5 text-emerald-600" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 px-1.5"
                    onClick={() => setEditingCaptionId(null)}
                  >
                    <X className="h-3.5 w-3.5 text-slate-400" />
                  </Button>
                </div>
              ) : photo.caption ? (
                <p className="p-2 text-xs text-slate-600 truncate">{photo.caption}</p>
              ) : null}
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-8">
          <ImageIcon className="h-10 w-10 text-slate-300 mx-auto mb-2" />
          <p className="text-sm text-slate-500">No photos yet</p>
          <p className="text-xs text-slate-400 mt-1">Upload property or job photos above</p>
        </div>
      )}

      {/* Delete confirmation dialog */}
      <Dialog open={!!deleteConfirmId} onOpenChange={() => setDeleteConfirmId(null)}>
        <DialogContent data-testid="delete-photo-dialog">
          <DialogHeader>
            <DialogTitle>Delete Photo</DialogTitle>
            <DialogDescription>
              This action cannot be undone. The photo will be permanently removed.
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-2 mt-4">
            <Button variant="outline" onClick={() => setDeleteConfirmId(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => deleteConfirmId && handleDelete(deleteConfirmId)}
              disabled={deleteMutation.isPending}
              data-testid="confirm-delete-photo-btn"
            >
              {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
