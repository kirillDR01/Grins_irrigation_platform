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
      style={{
        marginTop: 10,
        borderRadius: 14,
        border: '1.5px solid #E5E7EB',
        backgroundColor: '#FFFFFF',
        boxShadow: '0 1px 2px rgba(10,15,30,0.04)',
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '18px 20px 14px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <span
          style={{
            fontSize: 12.5,
            fontWeight: 800,
            letterSpacing: 1.4,
            textTransform: 'uppercase' as const,
            color: '#64748B',
          }}
        >
          INTERNAL NOTES
        </span>

        {/* Edit affordance — visible only in view mode */}
        {!editing && (
          <button
            type="button"
            onClick={() => onSetEditing(true)}
            aria-label="Edit notes"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 4,
              fontSize: 14,
              fontWeight: 700,
              color: '#64748B',
              backgroundColor: 'transparent',
              border: 'none',
              cursor: 'pointer',
              padding: 0,
            }}
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
          style={{
            padding: '0 20px 22px',
            fontSize: 14.5,
            fontWeight: 500,
            lineHeight: 1.6,
            color: '#0B1220',
            minHeight: 80,
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
          }}
        >
          {notes?.body || (
            <span style={{ color: '#9CA3AF', fontStyle: 'italic' }}>
              No notes yet. Tap Edit to add internal notes.
            </span>
          )}
        </div>
      )}

      {/* Edit mode */}
      {editing && (
        <div style={{ padding: '0 20px 22px' }}>
          <textarea
            ref={textareaRef}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={handleKeyDown}
            data-testid="notes-textarea"
            aria-label="Internal notes"
            style={{
              width: '100%',
              minHeight: 150,
              padding: '12px 14px',
              borderRadius: 12,
              border: '1.5px solid #E5E7EB',
              fontSize: 14.5,
              fontWeight: 500,
              lineHeight: 1.5,
              resize: 'vertical' as const,
              outline: 'none',
              fontFamily: 'inherit',
              boxSizing: 'border-box',
            }}
          />

          {/* Button row */}
          <div
            style={{
              marginTop: 14,
              display: 'flex',
              gap: 12,
              justifyContent: 'flex-end',
            }}
          >
            <button
              type="button"
              onClick={handleCancel}
              data-testid="notes-cancel-btn"
              style={{
                backgroundColor: '#FFFFFF',
                border: '1.5px solid #E5E7EB',
                color: '#1F2937',
                padding: '12px 28px',
                borderRadius: 999,
                fontSize: 15,
                fontWeight: 700,
                minWidth: 120,
                cursor: 'pointer',
              }}
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSave}
              data-testid="notes-save-btn"
              style={{
                backgroundColor: '#14B8A6',
                border: '1.5px solid #14B8A6',
                color: '#FFFFFF',
                padding: '12px 28px',
                borderRadius: 999,
                fontSize: 15,
                fontWeight: 700,
                minWidth: 140,
                cursor: 'pointer',
              }}
            >
              Save Notes
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
