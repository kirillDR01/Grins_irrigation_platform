/**
 * SecondaryActionsStrip — 4 LinkButtons: Add photo, Notes, Review, Edit tags.
 * Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
 */

import { Camera, FileText, Star, Tag } from 'lucide-react';
import { LinkButton } from './LinkButton';

interface SecondaryActionsStripProps {
  tagsOpen: boolean;
  onAddPhoto?: () => void;
  onNotes?: () => void;
  onReview?: () => void;
  onEditTags: () => void;
}

export function SecondaryActionsStrip({
  tagsOpen,
  onAddPhoto,
  onNotes,
  onReview,
  onEditTags,
}: SecondaryActionsStripProps) {
  return (
    <div className="px-5 pb-4 flex gap-2 flex-wrap flex-shrink-0">
      <LinkButton icon={<Camera />} onClick={onAddPhoto} aria-label="Add photo">
        Add photo
      </LinkButton>
      <LinkButton icon={<FileText />} onClick={onNotes} aria-label="Notes">
        Notes
      </LinkButton>
      <LinkButton icon={<Star />} onClick={onReview} aria-label="Review">
        Review
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
