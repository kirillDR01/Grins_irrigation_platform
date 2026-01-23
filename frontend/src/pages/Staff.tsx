import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { PageHeader } from '@/shared/components';
import { StaffList, StaffDetail } from '@/features/staff';
import type { Staff } from '@/features/staff';

export function StaffPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [, setSelectedStaff] = useState<Staff | null>(null);

  const handleEdit = (staff: Staff) => {
    setSelectedStaff(staff);
    navigate(`/staff/${staff.id}`);
  };

  const handleDelete = (staff: Staff) => {
    // Delete is handled in the list component via dropdown
    console.log('Delete staff:', staff.id);
  };

  // If we have an ID in the URL, show the detail view
  if (id) {
    return <StaffDetail />;
  }

  // Otherwise show the list view
  return (
    <div data-testid="staff-page">
      <PageHeader
        title="Staff"
        description="Manage staff members and their availability"
        action={
          <Button data-testid="add-staff-btn">
            <Plus className="mr-2 h-4 w-4" />
            Add Staff
          </Button>
        }
      />
      <StaffList onEdit={handleEdit} onDelete={handleDelete} />
    </div>
  );
}
