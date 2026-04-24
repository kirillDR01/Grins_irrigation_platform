/**
 * ModalFooter — Edit, No show, Cancel actions. Hidden for terminal statuses.
 * Requirements: 11.1, 11.2, 11.3, 11.4, 11.5
 */

import { Pencil, UserX, XCircle } from 'lucide-react';
import { LinkButton } from './LinkButton';
import type { AppointmentStatus } from '../../types';

const TERMINAL_STATUSES: AppointmentStatus[] = ['completed', 'cancelled', 'no_show'];

interface ModalFooterProps {
  status: AppointmentStatus;
  onEdit?: () => void;
  onNoShow?: () => void;
  onCancel?: () => void;
}

export function ModalFooter({ status, onEdit, onNoShow, onCancel }: ModalFooterProps) {
  if (TERMINAL_STATUSES.includes(status)) return null;

  return (
    <div className="flex items-center gap-2 bg-[#F9FAFB] border-t border-[#E5E7EB] px-5 py-4">
      <LinkButton onClick={onEdit} icon={<Pencil />} className="flex-1">
        Edit
      </LinkButton>
      <LinkButton onClick={onNoShow} icon={<UserX />} className="flex-1">
        No show
      </LinkButton>
      <LinkButton
        onClick={onCancel}
        icon={<XCircle />}
        variant="destructive"
        className="flex-1"
      >
        Cancel
      </LinkButton>
    </div>
  );
}
