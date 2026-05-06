// @ts-nocheck — pre-existing TS errors documented in bughunt/2026-04-29-pre-existing-tsc-errors.md
/**
 * PhotosPanel — Inline expansion panel for customer photos with upload CTAs.
 * Renders below SecondaryActionsStrip when "See attached photos" is toggled open.
 * Requirements: 4.1–4.12, 9.1–9.6, 11.4, 11.5, 11.7, 11.8, 12.5
 */

import { useRef, useState } from 'react';
import { Image, Upload, Camera, Plus } from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';
import {
  useCustomerPhotos,
  useUploadCustomerPhotos,
} from '@/features/customers';
import { PhotoCard } from './PhotoCard';

const MONO_FONT =
  "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace";

const ACCEPTED_TYPES = ['image/jpeg', 'image/png', 'image/heic', 'image/heif'] as const;
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB — must match photo_service.py:_RULES[CUSTOMER_PHOTO]

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

function toastUploadError(error: unknown): void {
  if (axios.isAxiosError(error)) {
    const status = error.response?.status;
    if (status === 413) {
      toast.error('File too large', { description: 'Photos must be 10 MB or smaller.' });
      return;
    }
    if (status === 415) {
      toast.error('Unsupported file type', { description: 'Use JPEG, PNG, or HEIC.' });
      return;
    }
    if (status === 422) {
      toast.error('Photo upload failed', { description: 'The server rejected the request. Please try a different file.' });
      return;
    }
  }
  toast.error('Photo upload failed', { description: 'Network or server error. Please try again.' });
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

    // Pre-validate (mirror PhotoGallery.tsx:34-48)
    const accepted: File[] = [];
    for (const file of fileArray) {
      if (!ACCEPTED_TYPES.includes(file.type as (typeof ACCEPTED_TYPES)[number])) {
        toast.error(`${file.name}: unsupported file type. Use JPEG, PNG, or HEIC.`);
        continue;
      }
      if (file.size > MAX_FILE_SIZE) {
        toast.error(`${file.name}: exceeds 10MB limit.`);
        continue;
      }
      accepted.push(file);
    }
    if (accepted.length === 0) return;

    // Optimistic placeholders for accepted files only
    const placeholders: OptimisticPhoto[] = accepted.map((file) => ({
      id: `optimistic-${Date.now()}-${Math.random()}`,
      file,
      previewUrl: URL.createObjectURL(file),
      uploading: true,
    }));

    setOptimisticPhotos((prev) => [...placeholders, ...prev]);

    try {
      await uploadMutation.mutateAsync({ files: accepted });
      setOptimisticPhotos((prev) =>
        prev.filter((p) => !placeholders.some((pl) => pl.id === p.id))
      );
      placeholders.forEach((p) => URL.revokeObjectURL(p.previewUrl));
    } catch (error: unknown) {
      setOptimisticPhotos((prev) =>
        prev.filter((p) => !placeholders.some((pl) => pl.id === p.id))
      );
      placeholders.forEach((p) => URL.revokeObjectURL(p.previewUrl));
      toastUploadError(error);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    handleUpload(e.target.files);
    e.target.value = '';
  };

  return (
    <div
      data-testid="photos-panel"
      className="mt-2.5 rounded-[14px] border-[1.5px] border-blue-700 bg-white overflow-hidden"
    >
      {/* Header bar */}
      <div className="bg-blue-100 py-2.5 px-3.5 flex items-center gap-2">
        <span className="w-4 h-4 flex items-center justify-center text-blue-700 flex-shrink-0">
          <Image size={16} strokeWidth={2.2} />
        </span>
        <span className="text-[13px] font-extrabold text-blue-700">
          Attached photos
        </span>
        <span
          className="inline-flex items-center justify-center rounded-full bg-blue-700 text-white text-[11.5px] font-extrabold min-w-[20px] h-5 px-1.5 leading-none"
          style={{ fontFamily: MONO_FONT }}
        >
          {photoCount}
        </span>
        <span className="ml-auto text-[11.5px] font-bold text-blue-700 opacity-[0.85]">
          From customer file
        </span>
      </div>

      {/* Upload CTAs row */}
      <div className="bg-white p-3 border-b border-[#E5E7EB] flex gap-2">
        {/* Primary: Upload photo · camera roll */}
        <button
          type="button"
          onClick={() => uploadInputRef.current?.click()}
          aria-label="Upload photo from camera roll"
          className="flex-1 min-h-[48px] bg-blue-700 text-white rounded-xl border-0 flex items-center justify-center gap-1.5 cursor-pointer text-sm font-bold px-3.5"
        >
          <Upload size={16} strokeWidth={2.2} />
          <span>Upload photo</span>
          <span
            className="text-[11.5px] opacity-90"
            style={{ fontFamily: MONO_FONT }}
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
          className="hidden"
          data-testid="upload-photo-input"
        />

        {/* Secondary: Take photo */}
        <button
          type="button"
          onClick={() => cameraInputRef.current?.click()}
          aria-label="Take photo with camera"
          className="min-h-[48px] bg-white text-blue-700 rounded-xl border-[1.5px] border-blue-700 flex items-center justify-center gap-1.5 cursor-pointer text-sm font-bold px-3.5"
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
          className="hidden"
          data-testid="take-photo-input"
        />
      </div>

      {/* Photo strip — horizontal scroll */}
      <div
        data-testid="photo-strip"
        className="flex overflow-x-auto p-3 gap-2.5"
      >
        {/* Optimistic placeholder cards */}
        {optimisticPhotos.map((op) => (
          <div
            key={op.id}
            className="w-[180px] max-sm:w-[140px] flex-shrink-0 rounded-xl border-[1.5px] border-[#E5E7EB] overflow-hidden bg-[#F9FAFB] relative"
          >
            <img
              src={op.previewUrl}
              alt="Uploading..."
              className="w-full h-[134px] object-cover block opacity-60"
            />
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-6 h-6 border-[2.5px] border-blue-700 border-t-transparent rounded-full animate-spin" />
            </div>
            <div className="py-2 px-2.5">
              <span className="text-xs font-bold text-gray-400">
                Uploading…
              </span>
            </div>
          </div>
        ))}

        {/* Loading state */}
        {isLoading && (
          <div className="flex items-center justify-center py-5 px-10 text-gray-500 text-[13px] font-semibold">
            Loading photos…
          </div>
        )}

        {/* Error state */}
        {error && !isLoading && (
          <div className="flex items-center justify-center py-5 px-10 text-red-500 text-[13px] font-semibold">
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
          className="w-[110px] max-sm:w-[90px] flex-shrink-0 rounded-xl border-[1.5px] border-dashed border-gray-300 bg-[#F9FAFB] flex flex-col items-center justify-center gap-1.5 cursor-pointer py-4 px-2 min-h-[134px] max-sm:min-h-[110px]"
        >
          <Plus size={20} strokeWidth={2} color="#9CA3AF" />
          <span className="text-xs font-extrabold text-gray-500 text-center leading-[1.3]">
            Add more
          </span>
          <span
            className="text-[10.5px] font-semibold text-gray-400 text-center"
            style={{ fontFamily: MONO_FONT }}
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
          className="hidden"
          data-testid="add-more-photo-input"
        />
      </div>

      {/* Footer */}
      <div className="bg-[#F9FAFB] pt-2 px-3.5 pb-2.5 border-t border-[#E5E7EB] flex items-center justify-between">
        <span className="text-[11.5px] font-bold text-gray-500">
          Tap a photo to expand · pinch to zoom
        </span>
        <button
          type="button"
          className="py-1.5 px-2.5 rounded-lg border-[1.5px] border-[#E5E7EB] bg-white text-xs font-extrabold text-gray-800 cursor-pointer"
        >
          View all ({photos?.length ?? 0})
        </button>
      </div>
    </div>
  );
}
