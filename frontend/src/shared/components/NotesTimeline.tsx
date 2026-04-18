/**
 * NotesTimeline — shared component for the unified notes timeline.
 *
 * Renders notes newest-first with author, timestamp, body, and stage tag.
 * Includes an "Add note" form when not in readOnly mode.
 * Supports `readOnly` and `maxEntries` props for appointment modal slices.
 *
 * Validates: april-16th-fixes-enhancements Requirement 4
 */

import { useState } from 'react';
import { format } from 'date-fns';
import { MessageSquare, Send, Loader2, User } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { getErrorMessage } from '@/core/api';
import { useNotes, useCreateNote } from '@/shared/hooks/useNotes';
import type { NoteEntry } from '@/shared/hooks/useNotes';

/** Stage tag color mapping */
const STAGE_TAG_COLORS: Record<string, string> = {
  Lead: 'bg-amber-100 text-amber-800 border-amber-200',
  Sales: 'bg-purple-100 text-purple-800 border-purple-200',
  Customer: 'bg-green-100 text-green-800 border-green-200',
  Appointment: 'bg-blue-100 text-blue-800 border-blue-200',
};

interface NotesTimelineProps {
  subjectType: 'lead' | 'sales_entry' | 'customer' | 'appointment';
  subjectId: string;
  /** When true, hides the "Add note" form */
  readOnly?: boolean;
  /** Limit the number of displayed entries (for appointment modal slice) */
  maxEntries?: number;
}

function NoteItem({ note }: { note: NoteEntry }) {
  const tagColor =
    STAGE_TAG_COLORS[note.stage_tag] ?? 'bg-slate-100 text-slate-700 border-slate-200';

  return (
    <div
      className="flex gap-3 py-3"
      data-testid={`note-item-${note.id}`}
    >
      {/* Avatar */}
      <div className="flex-shrink-0 mt-0.5">
        <div className="h-8 w-8 rounded-full bg-slate-100 flex items-center justify-center">
          <User className="h-4 w-4 text-slate-500" />
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-medium text-slate-700">
            {note.author_name}
          </span>
          <Badge
            variant="outline"
            className={`text-[10px] px-1.5 py-0 h-4 font-medium ${tagColor}`}
          >
            {note.stage_tag}
          </Badge>
          {note.is_system && (
            <Badge
              variant="outline"
              className="text-[10px] px-1.5 py-0 h-4 font-medium bg-slate-50 text-slate-500 border-slate-200"
            >
              System
            </Badge>
          )}
          <span className="text-xs text-slate-400">
            {format(new Date(note.created_at), 'MMM d, yyyy \'at\' h:mm a')}
          </span>
        </div>
        <p className="text-sm text-slate-600 mt-1 whitespace-pre-wrap break-words">
          {note.body}
        </p>
      </div>
    </div>
  );
}

export function NotesTimeline({
  subjectType,
  subjectId,
  readOnly = false,
  maxEntries,
}: NotesTimelineProps) {
  const { data: notes, isLoading, error } = useNotes(subjectType, subjectId);
  const createNote = useCreateNote(subjectType, subjectId);
  const [newNoteBody, setNewNoteBody] = useState('');

  const handleSubmit = async () => {
    const body = newNoteBody.trim();
    if (!body) return;

    try {
      await createNote.mutateAsync(body);
      setNewNoteBody('');
      toast.success('Note added');
    } catch (err: unknown) {
      toast.error('Failed to add note', { description: getErrorMessage(err) });
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const displayNotes = maxEntries && notes ? notes.slice(0, maxEntries) : notes;
  const hasMore = maxEntries && notes && notes.length > maxEntries;

  return (
    <div data-testid="notes-timeline" className="space-y-3">
      {/* Header */}
      <div className="flex items-center gap-2">
        <MessageSquare className="h-4 w-4 text-slate-500" />
        <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider">
          Notes
        </h3>
        {notes && notes.length > 0 && (
          <span className="text-xs text-slate-400">({notes.length})</span>
        )}
      </div>

      {/* Add note form */}
      {!readOnly && (
        <div className="flex gap-2" data-testid="add-note-form">
          <Textarea
            placeholder="Add a note... (Ctrl+Enter to submit)"
            value={newNoteBody}
            onChange={(e) => setNewNoteBody(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={2}
            className="resize-none text-sm"
            data-testid="note-input"
          />
          <Button
            size="sm"
            onClick={handleSubmit}
            disabled={!newNoteBody.trim() || createNote.isPending}
            className="self-end"
            data-testid="submit-note-btn"
          >
            {createNote.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </div>
      )}

      {/* Loading state */}
      {isLoading && (
        <div className="flex items-center justify-center py-6">
          <Loader2 className="h-5 w-5 animate-spin text-slate-400" />
        </div>
      )}

      {/* Error state */}
      {error && (
        <p className="text-sm text-red-500 py-2">
          Failed to load notes. Please try again.
        </p>
      )}

      {/* Notes list */}
      {displayNotes && displayNotes.length > 0 ? (
        <div className="divide-y divide-slate-100">
          {displayNotes.map((note) => (
            <NoteItem key={note.id} note={note} />
          ))}
        </div>
      ) : (
        !isLoading &&
        !error && (
          <p className="text-sm text-slate-400 italic py-3">
            No notes yet.{!readOnly && ' Add the first note above.'}
          </p>
        )
      )}

      {/* "View more" indicator for truncated lists */}
      {hasMore && (
        <p className="text-xs text-slate-400 text-center">
          Showing {maxEntries} of {notes!.length} notes
        </p>
      )}
    </div>
  );
}
