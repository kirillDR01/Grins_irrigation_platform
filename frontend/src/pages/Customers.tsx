import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { PageHeader } from '@/shared/components';
import { CustomerList, CustomerDetail, CustomerForm } from '@/features/customers';

export function CustomersPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);

  const handleCreateSuccess = () => {
    setIsCreateDialogOpen(false);
  };

  // If we have an ID in the URL, show the detail view
  if (id) {
    return <CustomerDetail />;
  }

  // Otherwise show the list view with header
  return (
    <div data-testid="customers-page">
      <PageHeader
        title="Customers"
        description="Manage your customer database"
        action={
          <Button onClick={() => setIsCreateDialogOpen(true)} data-testid="add-customer-btn">
            <Plus className="mr-2 h-4 w-4" />
            Add Customer
          </Button>
        }
      />
      <CustomerList
        onEdit={(customer) => navigate(`/customers/${customer.id}`)}
      />

      {/* Create Customer Dialog */}
      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Add New Customer</DialogTitle>
            <DialogDescription>
              Fill in the customer details below. Required fields are marked with an asterisk.
            </DialogDescription>
          </DialogHeader>
          <CustomerForm onSuccess={handleCreateSuccess} />
        </DialogContent>
      </Dialog>
    </div>
  );
}
