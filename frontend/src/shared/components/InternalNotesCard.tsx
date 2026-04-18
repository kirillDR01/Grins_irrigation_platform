/**
 * InternalNotesCard — shared component for the single-blob internal notes pattern.
 *
 * Renders a Card with collapsed (read) and expanded (edit) states.
 * Collapsed: plain text display with an Edit button.
 * Expanded: Textarea with Cancel and Save Notes buttons.
 *
 * Validates: internal-notes-simplification Requirement 7
 */

import { useState } from 'react';
import { Edit } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { getErrorMessage } from '@/core/api';

export interface InternalNotesCardProps {
  value: string | null;
  onSave: (next: string | null) => Promise<void>;
  isSaving: boolean;
  readOnly?: boolean;
  placeholder?: string;
  'data-testid-prefix'?: string;
}

export function InternalNotesCard({
  value,
  onSave,
  isSaving,
  readOnly = false,
  placeholder = 'No internal notes',
  'data-testid-prefix': testIdPrefix = '',
}: InternalNotesCardProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [draft, setDraft] = useState<string>('');

  const handleEdit = () => {
    setDraft(value ?? '');
    setIsEditing(true);
  };

  const handleCancel = () => {
    setIsEditing(false);
  };

  const handleSave = async () => {
    try {
      await onSave(draft.trim() === '' ? null : draft);
      setIsEditing(false);
      toast.success('Notes saved');
    } catch (err) {
      toast.error('Failed to save notes', { description: getErrorMessage(err) });
    }
  };

  return (
    <Card data-testid={`${testIdPrefix}notes-editor`}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-semibold text-slate-500 uppercase tracking-wider">
          Internal Notes
        </CardTitle>
        {!isEditing && !readOnly && (
          <Button
            variant="ghost"
            size="sm"
            onClick={handleEdit}
            data-testid={`${testIdPrefix}edit-notes-btn`}
          >
            <Edit className="h-3.5 w-3.5 mr-1" />
            Edit
          </Button>
        )}
      </CardHeader>
      <CardContent>
        {isEditing ? (
          <div className="space-y-3">
            <Textarea
              rows={5}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              data-testid={`${testIdPrefix}internal-notes-textarea`}
            />
            <div className="flex justify-end gap-2">
              <Button
                variant="outline"
                onClick={handleCancel}
              >
                Cancel
              </Button>
              <Button
                onClick={handleSave}
                disabled={isSaving}
                data-testid={`${testIdPrefix}save-notes-btn`}
              >
                {isSaving ? 'Saving...' : 'Save Notes'}
              </Button>
            </div>
          </div>
        ) : (
          <p
            className={`whitespace-pre-wrap text-sm ${
              value ? 'text-slate-700' : 'text-slate-400 italic'
            }`}
            data-testid={`${testIdPrefix}internal-notes-display`}
          >
            {value || placeholder}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
