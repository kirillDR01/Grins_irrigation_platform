/**
 * Appointment notes and photo upload (Req 33).
 * Notes textarea + photo upload with mobile camera capture.
 */

import { useState, useRef } from 'react';
import { FileText, Camera, Loader2, Save, X } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { useUpdateAppointment } from '../hooks/useAppointmentMutations';
import { useUploadAppointmentPhotos } from '../hooks/useAppointmentMutations';

interface AppointmentNotesProps {
  appointmentId: string;
  initialNotes?: string | null;
  onSuccess?: () => void;
}

export function AppointmentNotes({
  appointmentId,
  initialNotes,
  onSuccess,
}: AppointmentNotesProps) {
  const [notes, setNotes] = useState(initialNotes ?? '');
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const updateAppointment = useUpdateAppointment();
  const uploadPhotos = useUploadAppointmentPhotos();

  const handleSaveNotes = async () => {
    try {
      await updateAppointment.mutateAsync({
        id: appointmentId,
        data: { notes },
      });
      toast.success('Notes Saved');
      onSuccess?.();
    } catch {
      toast.error('Error', { description: 'Failed to save notes.' });
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    setSelectedFiles((prev) => [...prev, ...files]);
  };

  const removeFile = (index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleUploadPhotos = async () => {
    if (selectedFiles.length === 0) return;
    try {
      await uploadPhotos.mutateAsync({ id: appointmentId, files: selectedFiles });
      toast.success('Photos Uploaded', {
        description: `${selectedFiles.length} photo(s) uploaded.`,
      });
      setSelectedFiles([]);
      if (fileInputRef.current) fileInputRef.current.value = '';
      onSuccess?.();
    } catch {
      toast.error('Error', { description: 'Failed to upload photos.' });
    }
  };

  return (
    <div data-testid="appointment-notes" className="space-y-3 p-3 bg-slate-50 rounded-xl">
      <div className="flex items-center gap-2 mb-1">
        <FileText className="h-3.5 w-3.5 text-slate-400" />
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          Notes &amp; Photos
        </p>
      </div>

      {/* Notes */}
      <div>
        <Textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Add appointment notes..."
          rows={3}
          className="text-xs"
          data-testid="appointment-notes-textarea"
        />
        <Button
          onClick={handleSaveNotes}
          disabled={updateAppointment.isPending}
          size="sm"
          variant="outline"
          className="mt-1.5 h-7 text-xs"
          data-testid="save-notes-btn"
        >
          {updateAppointment.isPending ? (
            <Loader2 className="mr-1 h-3 w-3 animate-spin" />
          ) : (
            <Save className="mr-1 h-3 w-3" />
          )}
          Save Notes
        </Button>
      </div>

      {/* Photo Upload */}
      <div>
        <label className="text-xs font-medium text-slate-600 mb-1 block">Photos</label>
        <button
          type="button"
          className="w-full border-2 border-dashed border-slate-300 rounded-lg p-4 flex flex-col items-center justify-center gap-1 text-slate-500 hover:border-teal-400 hover:text-teal-600 transition-colors min-h-[48px] md:min-h-0"
          onClick={() => fileInputRef.current?.click()}
          data-testid="photo-upload-area"
        >
          <Camera className="h-5 w-5" />
          <span className="text-xs font-medium">Tap to add photos</span>
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*;capture=camera"
          multiple
          onChange={handleFileChange}
          className="hidden"
          data-testid="photo-file-input"
        />

        {selectedFiles.length > 0 && (
          <div className="mt-2 space-y-1">
            {selectedFiles.map((file, index) => (
              <div
                key={index}
                className="flex items-center justify-between bg-white rounded px-2 py-1 text-xs"
                data-testid={`photo-preview-${index}`}
              >
                <span className="truncate text-slate-600">{file.name}</span>
                <button
                  type="button"
                  onClick={() => removeFile(index)}
                  className="text-slate-400 hover:text-red-500 ml-2"
                >
                  <X className="h-3 w-3" />
                </button>
              </div>
            ))}
            <Button
              onClick={handleUploadPhotos}
              disabled={uploadPhotos.isPending}
              size="sm"
              className="bg-teal-500 hover:bg-teal-600 text-white h-7 text-xs mt-1"
              data-testid="upload-photos-btn"
            >
              {uploadPhotos.isPending ? (
                <Loader2 className="mr-1 h-3 w-3 animate-spin" />
              ) : (
                <Camera className="mr-1 h-3 w-3" />
              )}
              Upload {selectedFiles.length} Photo{selectedFiles.length !== 1 ? 's' : ''}
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
