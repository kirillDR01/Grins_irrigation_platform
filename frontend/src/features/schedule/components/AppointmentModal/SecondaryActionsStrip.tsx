/**
 * SecondaryActionsStrip — V2 upgrade.
 * Photos & Notes use V2LinkBtn with count badges and chevrons.
 * "Review" renamed to "Send Review Request". "Edit tags" unchanged.
 * Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7
 */

import { Image, FileText, Star, Tag } from 'lucide-react';
import { LinkButton } from './LinkButton';
import { V2LinkBtn } from './V2LinkBtn';

interface SecondaryActionsStripProps {
  tagsOpen: boolean;
  onEditTags: () => void;
  onReview?: () => void;
  reviewEnabled?: boolean;
  reviewDisabledReason?: string;
  /** V2 panel state */
  photosOpen: boolean;
  notesOpen: boolean;
  photoCount: number;
  noteCount: number;
  onTogglePhotos: () => void;
  onToggleNotes: () => void;
}

export function SecondaryActionsStrip({
  tagsOpen,
  onEditTags,
  onReview,
  reviewEnabled = true,
  reviewDisabledReason,
  photosOpen,
  notesOpen,
  photoCount,
  noteCount,
  onTogglePhotos,
  onToggleNotes,
}: SecondaryActionsStripProps) {
  return (
    <div className="px-5 pb-4 flex gap-2 flex-wrap flex-shrink-0">
      <V2LinkBtn
        icon={<Image />}
        accent="blue"
        open={photosOpen}
        count={photoCount}
        onClick={onTogglePhotos}
        aria-label="See attached photos"
      >
        See attached photos
      </V2LinkBtn>
      <V2LinkBtn
        icon={<FileText />}
        accent="amber"
        open={notesOpen}
        count={noteCount}
        onClick={onToggleNotes}
        aria-label="See attached notes"
      >
        See attached notes
      </V2LinkBtn>
      <LinkButton
        icon={<Star />}
        onClick={onReview}
        disabled={!reviewEnabled}
        aria-label={
          reviewEnabled
            ? 'Send Review Request'
            : reviewDisabledReason
              ? `Send Review Request — ${reviewDisabledReason}`
              : 'Send Review Request'
        }
        title={!reviewEnabled ? reviewDisabledReason : undefined}
      >
        Send Review Request
      </LinkButton>
      <LinkButton
        icon={<Tag />}
        onClick={onEditTags}
        variant={tagsOpen ? 'active' : 'default'}
        aria-label="Edit tags"
      >
        Edit tags
      </LinkButton>
    </div>
  );
}
