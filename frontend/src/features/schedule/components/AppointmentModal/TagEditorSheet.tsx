/**
 * Tag editor sheet — Sheet wrapper around the shared <TagPicker>.
 *
 * The picker is self-saving (via useSaveCustomerTags); the Sheet acts as a
 * focused modal surface for managing the customer's tag set on mobile.
 */

import { SheetContainer } from '@/shared/components/SheetContainer';
import { TagPicker } from '@/features/customers/components/TagPicker';

interface TagEditorSheetProps {
  customerId: string;
  customerName: string;
  onClose: () => void;
}

export function TagEditorSheet({
  customerId,
  customerName,
  onClose,
}: TagEditorSheetProps) {
  const footer = (
    <div className="flex gap-3">
      <button
        type="button"
        onClick={onClose}
        className="flex-1 h-11 rounded-[12px] bg-[#0B1220] text-white text-[15px] font-semibold"
      >
        Done
      </button>
    </div>
  );

  return (
    <SheetContainer
      title="Edit tags"
      subtitle={`Tags apply to ${customerName} across every job — past and future`}
      onClose={onClose}
      footer={footer}
    >
      <div className="mb-4 rounded-[10px] bg-[#DBEAFE] px-4 py-3 text-[13px] font-medium text-[#1E40AF]">
        Tags are saved to the customer profile and appear on all their
        appointments.
      </div>

      <section>
        <p className="text-[11px] font-extrabold tracking-[0.06em] text-[#6B7280] uppercase mb-2">
          Tags
        </p>
        <TagPicker customerId={customerId} />
      </section>
    </SheetContainer>
  );
}
