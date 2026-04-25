/**
 * Local UI state for the AppointmentModal.
 * V2: adds openPanel, editingNotes, togglePanel, setEditingNotes.
 * Requirements: 6.4, 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 16.1
 */

import { useState, useCallback, useEffect } from 'react';
import type { AppointmentStatus } from '../types';

export type ModalSheet = 'payment' | 'estimate' | 'tags';
export type OpenPanel = 'photos' | 'notes' | null;

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

  // V2 panel state
  const [openPanel, setOpenPanel] = useState<OpenPanel>(null);
  const [editingNotes, setEditingNotesRaw] = useState(false);

  // Auto-reset editingNotes when openPanel changes away from 'notes'
  useEffect(() => {
    if (openPanel !== 'notes') {
      setEditingNotesRaw(false);
    }
  }, [openPanel]);

  /**
   * Toggle a panel open/closed. Closes the other panel and any open sheet.
   * Req 7.2, 7.5: opening a panel closes any open sheet.
   */
  const togglePanel = useCallback((panel: 'photos' | 'notes') => {
    setOpenPanel((prev) => (prev === panel ? null : panel));
    setOpenSheet(null);
    setMapsPopoverOpen(false);
  }, []);

  /**
   * Wrapper for setEditingNotes so consumers get a stable reference.
   */
  const setEditingNotes = useCallback((editing: boolean) => {
    setEditingNotesRaw(editing);
  }, []);

  /**
   * Open a sheet exclusively — closes any open panel.
   * Req 7.4: opening a sheet closes any open panel.
   */
  const openSheetExclusive = useCallback((sheet: ModalSheet) => {
    setOpenSheet((prev) => (prev === sheet ? null : sheet));
    setOpenPanel(null);
    setMapsPopoverOpen(false);
  }, []);

  const closeSheet = useCallback(() => setOpenSheet(null), []);

  return {
    // Existing
    openSheet,
    mapsPopoverOpen,
    setMapsPopoverOpen,
    openSheetExclusive,
    closeSheet,
    // V2
    openPanel,
    editingNotes,
    togglePanel,
    setEditingNotes,
  };
}
