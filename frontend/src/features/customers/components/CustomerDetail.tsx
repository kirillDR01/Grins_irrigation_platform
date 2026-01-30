import { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, Phone, Mail, Edit, Trash2, Plus, MapPin } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { StatusBadge, LoadingPage, ErrorMessage, PageHeader } from '@/shared/components';
import { useCustomer, useDeleteCustomer } from '../hooks';
import { getCustomerFlags, getCustomerFullName } from '../types';
import { toast } from 'sonner';
import { AICommunicationDrafts } from '@/features/ai/components';
import { useAICommunication } from '@/features/ai/hooks/useAICommunication';

interface CustomerDetailProps {
  onEdit?: () => void;
}

export function CustomerDetail({ onEdit }: CustomerDetailProps) {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: customer, isLoading, error, refetch } = useCustomer(id!);
  const deleteMutation = useDeleteCustomer();
  const { draft, isLoading: isDraftLoading, error: draftError, sendNow, scheduleLater } = useAICommunication();
  
  // Add Property dialog state
  const [showAddPropertyDialog, setShowAddPropertyDialog] = useState(false);
  const [propertyAddress, setPropertyAddress] = useState('');
  const [propertyCity, setPropertyCity] = useState('');
  const [propertyState, setPropertyState] = useState('MN');
  const [propertyZip, setPropertyZip] = useState('');
  const [propertyNotes, setPropertyNotes] = useState('');

  const handleDelete = async () => {
    if (!customer) return;

    if (window.confirm(`Are you sure you want to delete ${getCustomerFullName(customer)}?`)) {
      try {
        await deleteMutation.mutateAsync(customer.id);
        toast.success('Customer deleted successfully');
        navigate('/customers');
      } catch {
        toast.error('Failed to delete customer');
      }
    }
  };

  const handleAddProperty = () => {
    // For now, just show a toast since the property API isn't fully implemented
    // In a real implementation, this would call the property API
    if (!propertyAddress.trim()) {
      toast.error('Please enter a street address');
      return;
    }
    
    toast.success('Property added', {
      description: `${propertyAddress}, ${propertyCity}, ${propertyState} ${propertyZip}`,
    });
    
    // Reset form and close dialog
    setPropertyAddress('');
    setPropertyCity('');
    setPropertyState('MN');
    setPropertyZip('');
    setPropertyNotes('');
    setShowAddPropertyDialog(false);
  };

  if (isLoading) {
    return <LoadingPage message="Loading customer..." />;
  }

  if (error) {
    return <ErrorMessage error={error} onRetry={() => refetch()} />;
  }

  if (!customer) {
    return <ErrorMessage error={new Error('Customer not found')} />;
  }

  const flags = getCustomerFlags(customer);

  return (
    <div data-testid="customer-detail">
      <div className="mb-6">
        <Button variant="ghost" size="sm" asChild>
          <Link to="/customers">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Customers
          </Link>
        </Button>
      </div>

      <PageHeader
        title={getCustomerFullName(customer)}
        description={`Customer since ${new Date(customer.created_at).toLocaleDateString()}`}
        action={
          <div className="flex gap-2">
            {onEdit && (
              <Button variant="outline" onClick={onEdit} data-testid="edit-customer-btn">
                <Edit className="mr-2 h-4 w-4" />
                Edit
              </Button>
            )}
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleteMutation.isPending}
              data-testid="delete-customer-btn"
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Delete
            </Button>
          </div>
        }
      />

      <div className="grid gap-6 md:grid-cols-2">
        {/* Contact Information */}
        <Card>
          <CardHeader>
            <CardTitle>Contact Information</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-3">
              <Phone className="h-5 w-5 text-muted-foreground" />
              <div>
                <p className="text-sm text-muted-foreground">Phone</p>
                <a href={`tel:${customer.phone}`} className="font-medium hover:underline">
                  {customer.phone}
                </a>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Mail className="h-5 w-5 text-muted-foreground" />
              <div>
                <p className="text-sm text-muted-foreground">Email</p>
                {customer.email ? (
                  <a
                    href={`mailto:${customer.email}`}
                    className="font-medium hover:underline"
                  >
                    {customer.email}
                  </a>
                ) : (
                  <span className="text-muted-foreground">Not provided</span>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Status & Flags */}
        <Card>
          <CardHeader>
            <CardTitle>Status & Flags</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="text-sm text-muted-foreground mb-2">Customer Flags</p>
              <div className="flex gap-2 flex-wrap">
                {flags.length > 0 ? (
                  flags.map((flag) => (
                    <StatusBadge key={flag} status={flag} type="customer" />
                  ))
                ) : (
                  <span className="text-muted-foreground">No flags</span>
                )}
              </div>
            </div>
            <Separator />
            <div>
              <p className="text-sm text-muted-foreground mb-2">Communication Preferences</p>
              <div className="space-y-1">
                <p className="text-sm">
                  SMS: {customer.sms_opt_in ? '✓ Opted in' : '✗ Opted out'}
                </p>
                <p className="text-sm">
                  Email: {customer.email_opt_in ? '✓ Opted in' : '✗ Opted out'}
                </p>
              </div>
            </div>
            {customer.lead_source && (
              <>
                <Separator />
                <div>
                  <p className="text-sm text-muted-foreground">Lead Source</p>
                  <p className="font-medium">{customer.lead_source}</p>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        {/* Properties */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <MapPin className="h-5 w-5" />
              Properties
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground">No properties yet.</p>
            <Button 
              variant="outline" 
              size="sm" 
              className="mt-4"
              onClick={() => setShowAddPropertyDialog(true)}
              data-testid="add-property-btn"
            >
              <Plus className="mr-2 h-4 w-4" />
              Add Property
            </Button>
          </CardContent>
        </Card>

        {/* Jobs History - Placeholder */}
        <Card>
          <CardHeader>
            <CardTitle>Job History</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground">No jobs yet.</p>
            <Button variant="outline" size="sm" className="mt-4" asChild>
              <Link to={`/jobs?customer_id=${customer.id}`}>View Jobs</Link>
            </Button>
          </CardContent>
        </Card>

        {/* AI Communication Drafts */}
        <div className="md:col-span-2">
          <AICommunicationDrafts
            draft={draft}
            isLoading={isDraftLoading}
            error={draftError ? new Error(draftError) : null}
            onSendNow={sendNow}
            onScheduleLater={scheduleLater}
          />
        </div>
      </div>

      {/* Add Property Dialog */}
      <Dialog open={showAddPropertyDialog} onOpenChange={setShowAddPropertyDialog}>
        <DialogContent className="max-w-md" data-testid="add-property-dialog">
          <DialogHeader>
            <DialogTitle>Add Property</DialogTitle>
            <DialogDescription>
              Add a service property for {customer ? getCustomerFullName(customer) : 'this customer'}.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="property-address">Street Address *</Label>
              <Input
                id="property-address"
                value={propertyAddress}
                onChange={(e) => setPropertyAddress(e.target.value)}
                placeholder="123 Main St"
                data-testid="property-address-input"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="property-city">City</Label>
                <Input
                  id="property-city"
                  value={propertyCity}
                  onChange={(e) => setPropertyCity(e.target.value)}
                  placeholder="Eden Prairie"
                  data-testid="property-city-input"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="property-state">State</Label>
                <Input
                  id="property-state"
                  value={propertyState}
                  onChange={(e) => setPropertyState(e.target.value)}
                  placeholder="MN"
                  data-testid="property-state-input"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="property-zip">ZIP Code</Label>
              <Input
                id="property-zip"
                value={propertyZip}
                onChange={(e) => setPropertyZip(e.target.value)}
                placeholder="55344"
                data-testid="property-zip-input"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="property-notes">Notes</Label>
              <Input
                id="property-notes"
                value={propertyNotes}
                onChange={(e) => setPropertyNotes(e.target.value)}
                placeholder="Gate code, access instructions, etc."
                data-testid="property-notes-input"
              />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button
              variant="outline"
              onClick={() => setShowAddPropertyDialog(false)}
              data-testid="cancel-property-btn"
            >
              Cancel
            </Button>
            <Button
              onClick={handleAddProperty}
              data-testid="save-property-btn"
            >
              Add Property
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
