/**
 * PhotosPanel — Inline expansion panel for customer photos with upload CTAs.
 * Renders below SecondaryActionsStrip when "See attached photos" is toggled open.
 * Requirements: 4.1–4.12, 9.1–9.6, 11.4, 11.5, 11.7, 11.8, 12.5
 */

import { useRef, useState } from 'react';
import { Image, Upload, Camera, Plus } from 'lucide-react';
import { toast } from 'sonner';
import {
  useCustomerPhotos,
  useUploadCustomerPhotos,
} from '@/features/customers';
import { PhotoCard } from './PhotoCard';

const MONO_FONT =
  "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace";

interface PhotosPanelProps {
  customerId: string;
  appointmentId: string;
  jobId?: string;
}

interface OptimisticPhoto {
  id: string;
  file: File;
  previewUrl: string;
  uploading: boolean;
}

export function PhotosPanel({ customerId, appointmentId }: PhotosPanelProps) {
  const { data: photos, isLoading, error } = useCustomerPhotos(customerId);
  const uploadMutation = useUploadCustomerPhotos(customerId);

  const uploadInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);
  const addMoreInputRef = useRef<HTMLInputElement>(null);

  const [optimisticPhotos, setOptimisticPhotos] = useState<OptimisticPhoto[]>([]);

  const photoCount = (photos?.length ?? 0) + optimisticPhotos.length;

  const handleUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;

    const fileArray = Array.from(files);

    // Create optimistic placeholders
    const placeholders: OptimisticPhoto[] = fileArray.map((file) => ({
      id: `optimistic-${Date.now()}-${Math.random()}`,
      file,
      previewUrl: URL.createObjectURL(file),
      uploading: true,
    }));

    setOptimisticPhotos((prev) => [...placeholders, ...prev]);

    try {
      await uploadMutation.mutateAsync({ files: fileArray });
      // On success, remove placeholders (real data will come from query refetch)
      setOptimisticPhotos((prev) =>
        prev.filter((p) => !placeholders.some((pl) => pl.id === p.id))
      );
      // Revoke object URLs
      placeholders.forEach((p) => URL.revokeObjectURL(p.previewUrl));
    } catch {
      // On error, remove placeholders and show toast
      setOptimisticPhotos((prev) =>
        prev.filter((p) => !placeholders.some((pl) => pl.id === p.id))
      );
      placeholders.forEach((p) => URL.revokeObjectURL(p.previewUrl));
      toast.error('Photo upload failed');
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    handleUpload(e.target.files);
    e.target.value = '';
  };

  return (
    <div
      data-testid="photos-panel"
      style={{
        marginTop: 10,
        borderRadius: 14,
        border: '1.5px solid #1D4ED8',
        backgroundColor: '#FFFFFF',
        overflow: 'hidden',
      }}
    >
      {/* Header bar */}
      <div
        style={{
          backgroundColor: '#DBEAFE',
          padding: '10px 14px',
          display: 'flex',
          alignItems: 'center',
          gap: 8,
        }}
      >
        <span
          style={{
            width: 16,
            height: 16,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#1D4ED8',
            flexShrink: 0,
          }}
        >
          <Image size={16} strokeWidth={2.2} />
        </span>
        <span
          style={{
            fontSize: 13,
            fontWeight: 800,
            color: '#1D4ED8',
          }}
        >
          Attached photos
        </span>
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            borderRadius: 999,
            backgroundColor: '#1D4ED8',
            color: '#FFFFFF',
            fontSize: 11.5,
            fontWeight: 800,
            fontFamily: MONO_FONT,
            minWidth: 20,
            height: 20,
            padding: '0 6px',
            lineHeight: 1,
          }}
        >
          {photoCount}
        </span>
        <span
          style={{
            marginLeft: 'auto',
            fontSize: 11.5,
            fontWeight: 700,
            color: '#1D4ED8',
            opacity: 0.85,
          }}
        >
          From customer file
        </span>
      </div>

      {/* Upload CTAs row */}
      <div
        style={{
          backgroundColor: '#FFFFFF',
          padding: 12,
          borderBottom: '1px solid #E5E7EB',
          display: 'flex',
          gap: 8,
        }}
      >
        {/* Primary: Upload photo · camera roll */}
        <button
          type="button"
          onClick={() => uploadInputRef.current?.click()}
          aria-label="Upload photo from camera roll"
          style={{
            flex: 1,
            minHeight: 48,
            backgroundColor: '#1D4ED8',
            color: '#FFFFFF',
            borderRadius: 12,
            border: 'none',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 6,
            cursor: 'pointer',
            fontSize: 14,
            fontWeight: 700,
            padding: '0 14px',
          }}
        >
          <Upload size={16} strokeWidth={2.2} />
          <span>Upload photo</span>
          <span
            style={{
              fontFamily: MONO_FONT,
              fontSize: 11.5,
              opacity: 0.9,
            }}
          >
            · camera roll
          </span>
        </button>
        <input
          ref={uploadInputRef}
          type="file"
          accept="image/*"
          multiple
          onChange={handleFileChange}
          style={{ display: 'none' }}
          data-testid="upload-photo-input"
        />

        {/* Secondary: Take photo */}
        <button
          type="button"
          onClick={() => cameraInputRef.current?.click()}
          aria-label="Take photo with camera"
          style={{
            minHeight: 48,
            backgroundColor: '#FFFFFF',
            color: '#1D4ED8',
            borderRadius: 12,
            border: '1.5px solid #1D4ED8',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 6,
            cursor: 'pointer',
            fontSize: 14,
            fontWeight: 700,
            padding: '0 14px',
          }}
        >
          <Camera size={16} strokeWidth={2.2} />
          <span>Take photo</span>
        </button>
        <input
          ref={cameraInputRef}
          type="file"
          accept="image/*"
          capture="environment"
          onChange={handleFileChange}
          style={{ display: 'none' }}
          data-testid="take-photo-input"
        />
      </div>

      {/* Photo strip — horizontal scroll */}
      <div
        data-testid="photo-strip"
        style={{
          display: 'flex',
          overflowX: 'auto',
          padding: 12,
          gap: 10,
          WebkitOverflowScrolling: 'touch',
        }}
      >
        {/* Optimistic placeholder cards */}
        {optimisticPhotos.map((op) => (
          <div
            key={op.id}
            style={{
              width: 180,
              flexShrink: 0,
              borderRadius: 12,
              border: '1.5px solid #E5E7EB',
              overflow: 'hidden',
              backgroundColor: '#F9FAFB',
              position: 'relative',
            }}
          >
            <img
              src={op.previewUrl}
              alt="Uploading..."
              style={{
                width: '100%',
                height: 134,
                objectFit: 'cover',
                display: 'block',
                opacity: 0.6,
              }}
            />
            <div
              style={{
                position: 'absolute',
                inset: 0,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <div
                style={{
                  width: 24,
                  height: 24,
                  border: '2.5px solid #1D4ED8',
                  borderTopColor: 'transparent',
                  borderRadius: '50%',
                  animation: 'spin 0.8s linear infinite',
                }}
              />
            </div>
            <div style={{ padding: '8px 10px' }}>
              <span
                style={{
                  fontSize: 12,
                  fontWeight: 700,
                  color: '#9CA3AF',
                }}
              >
                Uploading…
              </span>
            </div>
          </div>
        ))}

        {/* Loading state */}
        {isLoading && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '20px 40px',
              color: '#6B7280',
              fontSize: 13,
              fontWeight: 600,
            }}
          >
            Loading photos…
          </div>
        )}

        {/* Error state */}
        {error && !isLoading && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '20px 40px',
              color: '#EF4444',
              fontSize: 13,
              fontWeight: 600,
            }}
          >
            Unable to load photos
          </div>
        )}

        {/* Real photo cards */}
        {photos?.map((photo) => (
          <PhotoCard
            key={photo.id}
            src={photo.download_url}
            alt={photo.caption || photo.file_name}
            caption={photo.caption}
            date={photo.created_at}
          />
        ))}

        {/* Trailing "Add more · From library" tile */}
        <div
          role="button"
          tabIndex={0}
          onClick={() => addMoreInputRef.current?.click()}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              addMoreInputRef.current?.click();
            }
          }}
          aria-label="Add more photos from library"
          style={{
            width: 110,
            flexShrink: 0,
            borderRadius: 12,
            border: '1.5px dashed #D1D5DB',
            backgroundColor: '#F9FAFB',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 6,
            cursor: 'pointer',
            padding: '16px 8px',
            minHeight: 134,
          }}
        >
          <Plus size={20} strokeWidth={2} color="#9CA3AF" />
          <span
            style={{
              fontSize: 12,
              fontWeight: 800,
              color: '#6B7280',
              textAlign: 'center',
              lineHeight: 1.3,
            }}
          >
            Add more
          </span>
          <span
            style={{
              fontSize: 10.5,
              fontWeight: 600,
              fontFamily: MONO_FONT,
              color: '#9CA3AF',
              textAlign: 'center',
            }}
          >
            From library
          </span>
        </div>
        <input
          ref={addMoreInputRef}
          type="file"
          accept="image/*"
          multiple
          onChange={handleFileChange}
          style={{ display: 'none' }}
          data-testid="add-more-photo-input"
        />
      </div>

      {/* Footer */}
      <div
        style={{
          backgroundColor: '#F9FAFB',
          padding: '8px 14px 10px',
          borderTop: '1px solid #E5E7EB',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <span
          style={{
            fontSize: 11.5,
            fontWeight: 700,
            color: '#6B7280',
          }}
        >
          Tap a photo to expand · pinch to zoom
        </span>
        <button
          type="button"
          style={{
            padding: '6px 10px',
            borderRadius: 8,
            border: '1.5px solid #E5E7EB',
            backgroundColor: '#FFFFFF',
            fontSize: 12,
            fontWeight: 800,
            color: '#1F2937',
            cursor: 'pointer',
          }}
        >
          View all ({photos?.length ?? 0})
        </button>
      </div>
    </div>
  );
}
