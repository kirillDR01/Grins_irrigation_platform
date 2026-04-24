/**
 * Local UI state for the AppointmentModal.
 * Requirements: 6.4, 16.1
 */

import { useState } from 'react';
import type { AppointmentStatus } from '../types';

export type ModalSheet = 'payment' | 'estimate' | 'tags';

/**
 * Maps appointment status to a 0-based timeline step index.
 * Returns null for statuses that have no timeline representation.
 */
export function deriveStep(status: AppointmentStatus): number | null {
  switch (status) {
    case 'scheduled':
    case 'confirmed':
      return 0;
    case 'en_route':
      return 1;
    case 'in_progress':
      return 2;
    case 'completed':
      return 3;
    default:
      return null;
  }
}

export function useModalState() {
  const [openSheet, setOpenSheet] = useState<ModalSheet | null>(null);
  const [mapsPopoverOpen, setMapsPopoverOpen] = useState(false);

  const openSheetExclusive = (sheet: ModalSheet) => {
    setOpenSheet((prev) => (prev === sheet ? null : sheet));
    setMapsPopoverOpen(false);
  };

  const closeSheet = () => setOpenSheet(null);

  return {
    openSheet,
    mapsPopoverOpen,
    setMapsPopoverOpen,
    openSheetExclusive,
    closeSheet,
  };
}
