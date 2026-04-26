/**
 * NotesPanel — Inline expansion panel for centralized internal notes.
 * Supports view mode (read-only body) and edit mode (textarea + Save/Cancel).
 * Requirements: 6.1–6.11, 11.2, 11.3, 12.2, 12.3
 */

import { useState, useRef, useEffect, useCallback } from 'react';
import { Pencil } from 'lucide-react';
import { toast } from 'sonner';
import { useQueryClient } from '@tanstack/react-query';
import {
  useAppointmentNotes,
  useSaveAppointmentNotes,
  appointmentNoteKeys,
} from '../../hooks/useAppointmentNotes';
import type { AppointmentNotesResponse } from '../../hooks/useAppointmentNotes';

// ── Component ──

interface NotesPanelProps {
  appointmentId: string;
  editing: boolean;
  onSetEditing: (editing: boolean) => void;
}

export function NotesPanel({
  appointmentId,
  editing,
  onSetEditing,
}: NotesPanelProps) {
  const { data: notes } = useAppointmentNotes(appointmentId);
  const saveMutation = useSaveAppointmentNotes();
  const queryClient = useQueryClient();

  const [draft, setDraft] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // When entering edit mode, pre-fill draft with current body and focus textarea
  useEffect(() => {
    if (editing) {
      setDraft(notes?.body ?? '');
      // Defer focus to next tick so textarea is rendered
      requestAnimationFrame(() => {
        const ta = textareaRef.current;
        if (ta) {
          ta.focus();
          ta.setSelectionRange(ta.value.length, ta.value.length);
        }
      });
    }
  }, [editing, notes?.body]);

  const handleCancel = useCallback(() => {
    setDraft('');
    onSetEditing(false);
  }, [onSetEditing]);

  const handleSave = useCallback(async () => {
    // Optimistic update
    const previousNotes = queryClient.getQueryData<AppointmentNotesResponse>(
      appointmentNoteKeys.detail(appointmentId)
    );

    queryClient.setQueryData<AppointmentNotesResponse>(
      appointmentNoteKeys.detail(appointmentId),
      (old) =>
        old
          ? { ...old, body: draft, updated_at: new Date().toISOString() }
          : {
              appointment_id: appointmentId,
              body: draft,
              updated_at: new Date().toISOString(),
              updated_by: null,
            }
    );

    onSetEditing(false);

    try {
      await saveMutation.mutateAsync({ appointmentId, body: draft });
    } catch {
      // Revert optimistic update
      if (previousNotes) {
        queryClient.setQueryData(
          appointmentNoteKeys.detail(appointmentId),
          previousNotes
        );
      }
      toast.error("Couldn't save notes — try again");
      // Re-enter edit mode with draft preserved
      onSetEditing(true);
    }
  }, [appointmentId, draft, onSetEditing, queryClient, saveMutation]);

  // Keyboard shortcuts
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        handleCancel();
      }
      if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        handleSave();
      }
    },
    [handleCancel, handleSave]
  );

  return (
    <div
      data-testid="notes-panel"
      className="mt-2.5 rounded-[14px] border-[1.5px] border-[#E5E7EB] bg-white shadow-[0_1px_2px_rgba(10,15,30,0.04)] overflow-hidden"
    >
      {/* Header */}
      <div className="pt-[18px] px-5 pb-3.5 flex items-center justify-between">
        <span className="text-[12.5px] font-extrabold tracking-[1.4px] uppercase text-slate-500">
          INTERNAL NOTES
        </span>

        {/* Edit affordance — visible only in view mode */}
        {!editing && (
          <button
            type="button"
            onClick={() => onSetEditing(true)}
            aria-label="Edit notes"
            className="inline-flex items-center gap-1 text-sm font-bold text-slate-500 bg-transparent border-0 cursor-pointer p-0"
          >
            <Pencil size={14} strokeWidth={2.2} />
            <span>Edit</span>
          </button>
        )}
      </div>

      {/* View mode */}
      {!editing && (
        <div
          data-testid="notes-view-body"
          className="px-5 pb-[22px] text-[14.5px] font-medium leading-[1.6] text-[#0B1220] min-h-[80px] whitespace-pre-wrap break-words"
        >
          {notes?.body || (
            <span className="text-gray-400 italic">
              No notes yet. Tap Edit to add internal notes.
            </span>
          )}
        </div>
      )}

      {/* Edit mode */}
      {editing && (
        <div className="px-5 pb-[22px]">
          <textarea
            ref={textareaRef}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={handleKeyDown}
            data-testid="notes-textarea"
            aria-label="Internal notes"
            className="w-full min-h-[120px] sm:min-h-[150px] max-h-[40vh] px-3.5 py-3 rounded-xl border-[1.5px] border-[#E5E7EB] text-[14.5px] font-medium leading-[1.5] resize-y outline-none box-border"
            style={{ fontFamily: 'inherit' }}
          />

          {/* Button row — Save on top on mobile (above keyboard), side-by-side on sm:+ */}
          <div className="mt-3.5 flex flex-col-reverse gap-2 sm:flex-row sm:flex-wrap sm:justify-end sm:gap-3">
            <button
              type="button"
              onClick={handleCancel}
              data-testid="notes-cancel-btn"
              className="w-full sm:w-auto sm:min-w-[120px] min-h-[44px] px-7 py-3 rounded-full text-[15px] font-bold bg-white border-[1.5px] border-[#E5E7EB] text-gray-800 cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSave}
              data-testid="notes-save-btn"
              className="w-full sm:w-auto sm:min-w-[140px] min-h-[44px] px-7 py-3 rounded-full text-[15px] font-bold bg-teal-500 border-[1.5px] border-teal-500 text-white cursor-pointer"
            >
              Save Notes
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
