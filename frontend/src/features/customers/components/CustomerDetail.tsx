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
    <div data-testid="customer-detail" className="animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="mb-6">
        <Button variant="ghost" size="sm" asChild className="text-slate-600 hover:text-slate-800">
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

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Main Info Card - spans 2 columns on large screens */}
        <Card className="lg:col-span-2 bg-white rounded-2xl shadow-sm border border-slate-100">
          <CardHeader className="border-b border-slate-100">
            <CardTitle className="text-2xl font-bold text-slate-800">{getCustomerFullName(customer)}</CardTitle>
          </CardHeader>
          <CardContent className="p-6 space-y-6">
            {/* Contact Information Section */}
            <div>
              <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-4">Contact Information</h3>
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-slate-100 rounded-lg">
                    <Phone className="h-5 w-5 text-slate-600" />
                  </div>
                  <div>
                    <p className="text-xs text-slate-400">Phone</p>
                    <a href={`tel:${customer.phone}`} className="font-medium text-slate-700 hover:text-teal-600 transition-colors">
                      {customer.phone}
                    </a>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-slate-100 rounded-lg">
                    <Mail className="h-5 w-5 text-slate-600" />
                  </div>
                  <div>
                    <p className="text-xs text-slate-400">Email</p>
                    {customer.email ? (
                      <a
                        href={`mailto:${customer.email}`}
                        className="font-medium text-slate-700 hover:text-teal-600 transition-colors"
                      >
                        {customer.email}
                      </a>
                    ) : (
                      <span className="text-slate-400 italic">Not provided</span>
                    )}
                  </div>
                </div>
              </div>
            </div>

            <Separator className="bg-slate-100" />

            {/* Address Section */}
            <div>
              <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-4">Address</h3>
              <div className="flex items-start gap-3">
                <div className="p-2 bg-slate-100 rounded-lg">
                  <MapPin className="h-5 w-5 text-slate-600" />
                </div>
                <div>
                  <p className="text-slate-400 italic">No address on file</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Right Column - Customer Flags */}
        <Card>
          <CardHeader className="border-b border-slate-100">
            <CardTitle className="font-bold text-slate-800">Customer Flags</CardTitle>
          </CardHeader>
          <CardContent className="p-6 space-y-4">
            <div className="flex gap-2 flex-wrap" data-testid="customer-flags">
              {flags.length > 0 ? (
                flags.map((flag) => (
                  <StatusBadge key={flag} status={flag} type="customer" />
                ))
              ) : (
                <span className="text-slate-400 italic">No flags</span>
              )}
            </div>
            <Separator className="bg-slate-100" />
            <div>
              <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">Communication Preferences</p>
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${customer.sms_opt_in ? 'bg-emerald-500' : 'bg-slate-300'}`} />
                  <span className="text-sm text-slate-600">
                    SMS: {customer.sms_opt_in ? 'Opted in' : 'Opted out'}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${customer.email_opt_in ? 'bg-emerald-500' : 'bg-slate-300'}`} />
                  <span className="text-sm text-slate-600">
                    Email: {customer.email_opt_in ? 'Opted in' : 'Opted out'}
                  </span>
                </div>
              </div>
            </div>
            {customer.lead_source && (
              <>
                <Separator className="bg-slate-100" />
                <div>
                  <p className="text-xs text-slate-400 uppercase tracking-wider mb-1">Lead Source</p>
                  <p className="font-medium text-slate-700">{customer.lead_source}</p>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        {/* Properties Section */}
        <Card className="lg:col-span-2 bg-white rounded-2xl shadow-sm border border-slate-100" data-testid="properties-section">
          <CardHeader className="border-b border-slate-100">
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2 font-bold text-slate-800">
                <MapPin className="h-5 w-5 text-teal-500" />
                Properties
              </CardTitle>
              <Button 
                variant="outline" 
                size="sm"
                onClick={() => setShowAddPropertyDialog(true)}
                data-testid="add-property-btn"
                className="text-teal-600 border-teal-200 hover:bg-teal-50"
              >
                <Plus className="mr-2 h-4 w-4" />
                Add Property
              </Button>
            </div>
          </CardHeader>
          <CardContent className="p-6">
            <div className="text-center py-8">
              <div className="w-12 h-12 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-3">
                <MapPin className="h-6 w-6 text-slate-400" />
              </div>
              <p className="text-slate-500">No properties yet</p>
              <p className="text-sm text-slate-400 mt-1">Add a property to track service locations</p>
            </div>
          </CardContent>
        </Card>

        {/* Job History Section */}
        <Card data-testid="job-history-section">
          <CardHeader className="border-b border-slate-100">
            <CardTitle className="font-bold text-slate-800">Job History</CardTitle>
          </CardHeader>
          <CardContent className="p-6">
            <div className="text-center py-6">
              <p className="text-slate-500">No jobs yet</p>
              <Button variant="outline" size="sm" className="mt-4 text-teal-600 border-teal-200 hover:bg-teal-50" asChild>
                <Link to={`/jobs?customer_id=${customer.id}`}>View All Jobs</Link>
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* AI Communication Drafts - Full width */}
        <div className="lg:col-span-3">
          <AICommunicationDrafts
            draft={draft}
            isLoading={isDraftLoading}
            error={draftError ? new Error(draftError) : null}
            onSendNow={sendNow}
            onScheduleLater={(draftId) => scheduleLater(draftId, '')}
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
