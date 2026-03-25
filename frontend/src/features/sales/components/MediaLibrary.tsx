import { useState, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { LoadingSpinner } from '@/shared/components';
import { Grid3X3, List, Upload, Image, Film, MessageSquare, Paperclip } from 'lucide-react';
import { toast } from 'sonner';
import { useMedia, useUploadMedia } from '../hooks';
import type { MediaListParams, MediaItem } from '../types';

const CATEGORIES = ['spring_startup', 'installation', 'repair', 'maintenance', 'winterization', 'other'];
const MEDIA_TYPES = ['PHOTO', 'VIDEO', 'TESTIMONIAL'];

const mediaTypeIcon = (type: string) => {
  switch (type) {
    case 'VIDEO': return <Film className="h-4 w-4" />;
    case 'TESTIMONIAL': return <MessageSquare className="h-4 w-4" />;
    default: return <Image className="h-4 w-4" />;
  }
};

export function MediaLibrary() {
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [filters, setFilters] = useState<MediaListParams>({});
  const [isDragging, setIsDragging] = useState(false);

  const { data, isLoading } = useMedia(filters);
  const uploadMedia = useUploadMedia();

  const handleFileUpload = useCallback(async (files: FileList | null) => {
    if (!files?.length) return;
    for (const file of Array.from(files)) {
      try {
        await uploadMedia.mutateAsync({
          file,
          metadata: {
            category: filters.category || 'other',
            media_type: file.type.startsWith('video/') ? 'VIDEO' : 'PHOTO',
          },
        });
        toast.success(`Uploaded ${file.name}`);
      } catch {
        toast.error(`Failed to upload ${file.name}`);
      }
    }
  }, [uploadMedia, filters.category]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    handleFileUpload(e.dataTransfer.files);
  }, [handleFileUpload]);

  const items = data?.items ?? [];

  return (
    <Card data-testid="media-library">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Media Library</CardTitle>
          <div className="flex items-center gap-2">
            <Button
              variant={viewMode === 'grid' ? 'default' : 'outline'}
              size="icon"
              onClick={() => setViewMode('grid')}
              data-testid="view-grid-btn"
            >
              <Grid3X3 className="h-4 w-4" />
            </Button>
            <Button
              variant={viewMode === 'list' ? 'default' : 'outline'}
              size="icon"
              onClick={() => setViewMode('list')}
              data-testid="view-list-btn"
            >
              <List className="h-4 w-4" />
            </Button>
          </div>
        </div>
        {/* Filters */}
        <div className="flex gap-2 mt-2">
          <Select
            value={filters.category || ''}
            onValueChange={(v) => setFilters((f) => ({ ...f, category: v || undefined }))}
          >
            <SelectTrigger className="w-40" data-testid="filter-category">
              <SelectValue placeholder="Category" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Categories</SelectItem>
              {CATEGORIES.map((c) => (
                <SelectItem key={c} value={c}>{c.replace(/_/g, ' ')}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select
            value={filters.media_type || ''}
            onValueChange={(v) => setFilters((f) => ({ ...f, media_type: v || undefined }))}
          >
            <SelectTrigger className="w-40" data-testid="filter-media-type">
              <SelectValue placeholder="Media Type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Types</SelectItem>
              {MEDIA_TYPES.map((t) => (
                <SelectItem key={t} value={t}>{t.charAt(0) + t.slice(1).toLowerCase()}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Drag-drop upload zone */}
        <div
          className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
            isDragging ? 'border-teal-400 bg-teal-50' : 'border-slate-200 hover:border-slate-300'
          }`}
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          data-testid="upload-dropzone"
        >
          <Upload className="h-8 w-8 mx-auto text-slate-400 mb-2" />
          <p className="text-sm text-slate-500">Drag & drop files here, or</p>
          <label className="inline-block mt-2">
            <Input
              type="file"
              multiple
              accept="image/*,video/*"
              className="hidden"
              onChange={(e) => handleFileUpload(e.target.files)}
              data-testid="file-input"
            />
            <Button variant="outline" size="sm" asChild>
              <span>Browse Files</span>
            </Button>
          </label>
          {uploadMedia.isPending && <p className="text-xs text-teal-600 mt-2">Uploading...</p>}
        </div>

        {/* Content */}
        {isLoading ? (
          <LoadingSpinner />
        ) : items.length === 0 ? (
          <p className="text-center text-sm text-slate-400 py-8">No media items found.</p>
        ) : viewMode === 'grid' ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3" data-testid="media-grid">
            {items.map((item: MediaItem) => (
              <div
                key={item.id}
                className="group relative rounded-lg border border-slate-200 overflow-hidden hover:shadow-md transition-shadow"
                data-testid={`media-item-${item.id}`}
              >
                <div className="aspect-square bg-slate-100 flex items-center justify-center">
                  {item.content_type.startsWith('image/') && item.download_url ? (
                    <img src={item.download_url} alt={item.caption || item.file_name} className="object-cover w-full h-full" />
                  ) : (
                    <div className="text-slate-400">{mediaTypeIcon(item.media_type)}</div>
                  )}
                </div>
                <div className="p-2">
                  <p className="text-xs font-medium truncate">{item.file_name}</p>
                  <p className="text-[10px] text-slate-400">{item.category}</p>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  className="absolute top-1 right-1 opacity-0 group-hover:opacity-100 transition-opacity h-7 w-7"
                  data-testid={`attach-media-${item.id}`}
                >
                  <Paperclip className="h-3 w-3" />
                </Button>
              </div>
            ))}
          </div>
        ) : (
          <div className="space-y-1" data-testid="media-list">
            {items.map((item: MediaItem) => (
              <div
                key={item.id}
                className="flex items-center gap-3 p-2 rounded-lg hover:bg-slate-50 transition-colors"
                data-testid={`media-item-${item.id}`}
              >
                <div className="w-10 h-10 rounded bg-slate-100 flex items-center justify-center shrink-0">
                  {mediaTypeIcon(item.media_type)}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{item.file_name}</p>
                  <p className="text-xs text-slate-400">{item.category} • {(item.file_size / 1024).toFixed(0)} KB</p>
                </div>
                <Button variant="ghost" size="sm" data-testid={`attach-media-${item.id}`}>
                  <Paperclip className="h-3 w-3 mr-1" /> Attach
                </Button>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
