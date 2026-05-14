import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { PageHeader } from '@/shared/components';
import { StaffList, StaffDetail, StaffForm } from '@/features/staff';
import type { Staff } from '@/features/staff';

export function StaffPage() {
  const { id } = useParams<{ id: string }>();
  const [formOpen, setFormOpen] = useState(false);
  const [editingStaff, setEditingStaff] = useState<Staff | null>(null);

  const handleEdit = (staff: Staff) => {
    setEditingStaff(staff);
    setFormOpen(true);
  };

  // If we have an ID in the URL, show the detail view.
  if (id) {
    return <StaffDetail onEdit={() => {}} />;
  }

  return (
    <div data-testid="staff-page">
      <PageHeader
        title="Staff"
        description="Manage staff members and their availability"
        action={
          <Button
            data-testid="add-staff-btn"
            onClick={() => {
              setEditingStaff(null);
              setFormOpen(true);
            }}
          >
            <Plus className="mr-2 h-4 w-4" />
            Add Staff
          </Button>
        }
      />
      <StaffList onEdit={handleEdit} />
      <StaffForm
        open={formOpen}
        onOpenChange={(open) => {
          setFormOpen(open);
          if (!open) setEditingStaff(null);
        }}
        mode={editingStaff ? 'edit' : 'create'}
        staff={editingStaff ?? undefined}
      />
    </div>
  );
}
