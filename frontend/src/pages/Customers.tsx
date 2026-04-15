import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Plus, Users } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { PageHeader } from '@/shared/components';
import { CustomerList, CustomerDetail, CustomerForm, DuplicateReviewQueue } from '@/features/customers';
import { useCustomer, useDuplicateReviewQueue } from '@/features/customers/hooks';

export function CustomersPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [showDuplicateQueue, setShowDuplicateQueue] = useState(false);
  
  // Fetch customer data when on detail page for edit form
  const { data: customer } = useCustomer(id ?? '');

  // Fetch duplicate count for badge
  const { data: dupData } = useDuplicateReviewQueue(0, 1);
  const dupCount = dupData?.total ?? 0;

  const handleCreateSuccess = () => {
    setIsCreateDialogOpen(false);
  };

  const handleEditSuccess = () => {
    setIsEditDialogOpen(false);
  };

  // If we have an ID in the URL, show the detail view
  if (id) {
    return (
      <>
        <CustomerDetail onEdit={() => setIsEditDialogOpen(true)} />
        
        {/* Edit Customer Dialog */}
        <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Edit Customer</DialogTitle>
              <DialogDescription>
                Update the customer details below.
              </DialogDescription>
            </DialogHeader>
            {customer && (
              <CustomerForm 
                customer={customer} 
                onSuccess={handleEditSuccess} 
              />
            )}
          </DialogContent>
        </Dialog>
      </>
    );
  }

  // Otherwise show the list view with header
  if (showDuplicateQueue) {
    return (
      <div data-testid="customers-page">
        <PageHeader
          title="Customers"
          description="Manage your customer database"
        />
        <DuplicateReviewQueue onClose={() => setShowDuplicateQueue(false)} />
      </div>
    );
  }

  return (
    <div data-testid="customers-page">
      <PageHeader
        title="Customers"
        description="Manage your customer database"
        action={
          <div className="flex gap-2">
            {dupCount > 0 && (
              <Button
                variant="outline"
                onClick={() => setShowDuplicateQueue(true)}
                data-testid="review-duplicates-btn"
              >
                <Users className="mr-2 h-4 w-4" />
                Review Duplicates
                <Badge variant="secondary" className="ml-2" data-testid="dup-count-badge">
                  {dupCount}
                </Badge>
              </Button>
            )}
            <Button onClick={() => setIsCreateDialogOpen(true)} data-testid="add-customer-btn">
              <Plus className="mr-2 h-4 w-4" />
              Add Customer
            </Button>
          </div>
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
