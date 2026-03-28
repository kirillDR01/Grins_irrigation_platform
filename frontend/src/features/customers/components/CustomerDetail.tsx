import { useState, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  ArrowLeft, Phone, Mail, Edit, Trash2, Plus, MapPin, Dog, Clock,
  Image, FileText, CreditCard, MessageSquare, Users,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
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
import { useCustomer, useDeleteCustomer, useUpdateCustomer } from '../hooks';
import { getCustomerFlags, getCustomerFullName } from '../types';
import { toast } from 'sonner';
import { AICommunicationDrafts } from '@/features/ai/components';
import { useAICommunication } from '@/features/ai/hooks/useAICommunication';
import { PhotoGallery } from './PhotoGallery';
import { InvoiceHistory } from './InvoiceHistory';
import { PaymentMethods } from './PaymentMethods';
import { CustomerMessages } from './CustomerMessages';
import { DuplicateReview } from './DuplicateReview';

const SERVICE_TIME_OPTIONS = [
  { value: 'MORNING', label: 'Morning' },
  { value: 'AFTERNOON', label: 'Afternoon' },
  { value: 'EVENING', label: 'Evening' },
  { value: 'NO_PREFERENCE', label: 'No Preference' },
] as const;

const SCHEDULE_LABELS: Record<string, string> = {
  ASAP: 'As Soon As Possible',
  ONE_TWO_WEEKS: 'Within 1-2 Weeks',
  THREE_FOUR_WEEKS: 'Within 3-4 Weeks',
  OTHER: 'Other',
};

interface CustomerDetailProps {
  onEdit?: () => void;
}

export function CustomerDetail({ onEdit }: CustomerDetailProps) {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: customer, isLoading, error, refetch } = useCustomer(id!);
  const deleteMutation = useDeleteCustomer();
  const updateMutation = useUpdateCustomer();
  const { draft, isLoading: isDraftLoading, error: draftError, sendNow, scheduleLater } = useAICommunication();

  // Internal notes state
  const [notesValue, setNotesValue] = useState<string | null>(null);
  const [isEditingNotes, setIsEditingNotes] = useState(false);

  // Service time preference state
  const [isEditingServiceTime, setIsEditingServiceTime] = useState(false);

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

  const handleSaveNotes = useCallback(async () => {
    if (!customer || notesValue === null) return;
    try {
      await updateMutation.mutateAsync({
        id: customer.id,
        data: { internal_notes: notesValue || null },
      });
      setIsEditingNotes(false);
      toast.success('Notes saved');
    } catch {
      toast.error('Failed to save notes');
    }
  }, [customer, notesValue, updateMutation]);

  const handleServiceTimeChange = useCallback(
    async (preference: string) => {
      if (!customer) return;
      try {
        await updateMutation.mutateAsync({
          id: customer.id,
          data: { preferred_service_times: { preference } },
        });
        setIsEditingServiceTime(false);
        toast.success('Service preference updated');
      } catch {
        toast.error('Failed to update service preference');
      }
    },
    [customer, updateMutation]
  );

  const handleAddProperty = () => {
    if (!propertyAddress.trim()) {
      toast.error('Please enter a street address');
      return;
    }
    toast.success('Property added', {
      description: `${propertyAddress}, ${propertyCity}, ${propertyState} ${propertyZip}`,
    });
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
  const currentPreference = customer.preferred_service_times?.preference || 'NO_PREFERENCE';

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
        {/* Main Info Card */}
        <Card className="lg:col-span-2 bg-white rounded-2xl shadow-sm border border-slate-100">
          <CardHeader className="border-b border-slate-100">
            <CardTitle className="text-2xl font-bold text-slate-800">{getCustomerFullName(customer)}</CardTitle>
          </CardHeader>
          <CardContent className="p-6 space-y-6">
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
                      <a href={`mailto:${customer.email}`} className="font-medium text-slate-700 hover:text-teal-600 transition-colors">
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
            <div>
              <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-4">Address</h3>
              <div className="flex items-start gap-3">
                <div className="p-2 bg-slate-100 rounded-lg">
                  <MapPin className="h-5 w-5 text-slate-600" />
                </div>
                <div>
                  {customer.properties && customer.properties.length > 0 ? (
                    <p className="font-medium text-slate-700">
                      {customer.properties[0].address}, {customer.properties[0].city}, {customer.properties[0].state} {customer.properties[0].zip_code}
                    </p>
                  ) : (
                    <p className="text-slate-400 italic">No address on file</p>
                  )}
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
                  <span className="text-sm text-slate-600">SMS: {customer.sms_opt_in ? 'Opted in' : 'Opted out'}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${customer.email_opt_in ? 'bg-emerald-500' : 'bg-slate-300'}`} />
                  <span className="text-sm text-slate-600">Email: {customer.email_opt_in ? 'Opted in' : 'Opted out'}</span>
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
            <Separator className="bg-slate-100" />
            <div>
              <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">Service Preferences</p>
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Clock className="h-4 w-4 text-slate-500" />
                  <span className="text-sm text-slate-600">
                    Preferred Time:{' '}
                    {SERVICE_TIME_OPTIONS.find((o) => o.value === currentPreference)?.label || 'No Preference'}
                  </span>
                </div>
                {customer.properties?.some((p) => p.has_dogs) && (
                  <div className="flex items-center gap-2">
                    <Dog className="h-4 w-4 text-amber-500" />
                    <span className="text-sm text-amber-700 font-medium">Dogs on Property</span>
                  </div>
                )}
                {customer.preferred_schedule && (
                  <div className="flex items-start gap-2" data-testid="customer-preferred-schedule">
                    <Clock className="h-4 w-4 text-slate-500 mt-0.5" />
                    <div>
                      <span className="text-sm text-slate-600">
                        Timeline: {SCHEDULE_LABELS[customer.preferred_schedule] || customer.preferred_schedule}
                      </span>
                      {customer.preferred_schedule === 'OTHER' && customer.preferred_schedule_details && (
                        <p className="text-xs text-slate-500 mt-0.5">{customer.preferred_schedule_details}</p>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabbed Content Section */}
      <div className="mt-8">
        <Tabs defaultValue="overview" data-testid="customer-tabs">
          <TabsList data-testid="customer-tabs-list">
            <TabsTrigger value="overview" data-testid="tab-overview">
              <Edit className="h-4 w-4" />
              Overview
            </TabsTrigger>
            <TabsTrigger value="photos" data-testid="tab-photos">
              <Image className="h-4 w-4" />
              Photos
            </TabsTrigger>
            <TabsTrigger value="invoices" data-testid="tab-invoices">
              <FileText className="h-4 w-4" />
              Invoice History
            </TabsTrigger>
            <TabsTrigger value="payment-methods" data-testid="tab-payment-methods">
              <CreditCard className="h-4 w-4" />
              Payment Methods
            </TabsTrigger>
            <TabsTrigger value="messages" data-testid="tab-messages">
              <MessageSquare className="h-4 w-4" />
              Messages
            </TabsTrigger>
            <TabsTrigger value="duplicates" data-testid="tab-duplicates">
              <Users className="h-4 w-4" />
              Potential Duplicates
            </TabsTrigger>
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview" data-testid="tab-content-overview">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Internal Notes (Req 8) */}
              <Card>
                <CardHeader className="border-b border-slate-100">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-lg font-bold text-slate-800">Internal Notes</CardTitle>
                    {!isEditingNotes && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setNotesValue(customer.internal_notes || '');
                          setIsEditingNotes(true);
                        }}
                        data-testid="edit-notes-btn"
                      >
                        <Edit className="h-3.5 w-3.5 mr-1" />
                        Edit
                      </Button>
                    )}
                  </div>
                </CardHeader>
                <CardContent className="p-4">
                  {isEditingNotes ? (
                    <div className="space-y-3" data-testid="notes-editor">
                      <Textarea
                        value={notesValue || ''}
                        onChange={(e) => setNotesValue(e.target.value)}
                        placeholder="Add internal notes about this customer..."
                        rows={5}
                        data-testid="internal-notes-textarea"
                      />
                      <div className="flex justify-end gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setIsEditingNotes(false)}
                        >
                          Cancel
                        </Button>
                        <Button
                          size="sm"
                          onClick={handleSaveNotes}
                          disabled={updateMutation.isPending}
                          data-testid="save-notes-btn"
                        >
                          {updateMutation.isPending ? 'Saving...' : 'Save Notes'}
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <div data-testid="internal-notes-display">
                      {customer.internal_notes ? (
                        <p className="text-sm text-slate-700 whitespace-pre-wrap">{customer.internal_notes}</p>
                      ) : (
                        <p className="text-sm text-slate-400 italic">No internal notes</p>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Preferred Service Times (Req 11) */}
              <Card>
                <CardHeader className="border-b border-slate-100">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-lg font-bold text-slate-800">Service Preferences</CardTitle>
                    {!isEditingServiceTime && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setIsEditingServiceTime(true)}
                        data-testid="edit-service-time-btn"
                      >
                        <Edit className="h-3.5 w-3.5 mr-1" />
                        Edit
                      </Button>
                    )}
                  </div>
                </CardHeader>
                <CardContent className="p-4">
                  {isEditingServiceTime ? (
                    <div className="space-y-3" data-testid="service-time-editor">
                      <p className="text-sm text-slate-600 mb-2">Select preferred service time:</p>
                      <div className="grid grid-cols-2 gap-2">
                        {SERVICE_TIME_OPTIONS.map((option) => (
                          <Button
                            key={option.value}
                            variant={currentPreference === option.value ? 'default' : 'outline'}
                            size="sm"
                            onClick={() => handleServiceTimeChange(option.value)}
                            disabled={updateMutation.isPending}
                            data-testid={`service-time-${option.value.toLowerCase()}`}
                          >
                            {option.label}
                          </Button>
                        ))}
                      </div>
                      <div className="flex justify-end">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setIsEditingServiceTime(false)}
                        >
                          Cancel
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <div data-testid="service-time-display">
                      <div className="flex items-center gap-2">
                        <Clock className="h-4 w-4 text-teal-500" />
                        <span className="text-sm font-medium text-slate-700">
                          {SERVICE_TIME_OPTIONS.find((o) => o.value === currentPreference)?.label || 'No Preference'}
                        </span>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Properties Section */}
              <Card className="lg:col-span-2" data-testid="properties-section">
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
                  {customer.properties && customer.properties.length > 0 ? (
                    <div className="space-y-4">
                      {customer.properties.map((property) => (
                        <div
                          key={property.id}
                          className="rounded-lg border border-slate-100 p-4 space-y-2"
                          data-testid={`property-${property.id}`}
                        >
                          <div className="flex items-start justify-between">
                            <div>
                              <p className="font-medium text-slate-700">
                                {property.address}, {property.city}, {property.state} {property.zip_code}
                              </p>
                              <div className="flex items-center gap-3 mt-1 text-xs text-slate-500">
                                <span>{property.property_type}</span>
                                {property.zone_count != null && <span>{property.zone_count} zones</span>}
                                {property.is_primary && <span className="text-teal-600 font-medium">Primary</span>}
                              </div>
                            </div>
                            {property.has_dogs && (
                              <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-1 text-xs font-medium text-amber-700">
                                <Dog className="h-3 w-3" />
                                Dogs
                              </span>
                            )}
                          </div>
                          {(property.access_instructions || property.gate_code || property.special_notes) && (
                            <div className="text-xs text-slate-500 space-y-1 pt-1 border-t border-slate-50">
                              {property.gate_code && (
                                <p>Gate Code: <span className="font-medium text-slate-600">{property.gate_code}</span></p>
                              )}
                              {property.access_instructions && <p>Access: {property.access_instructions}</p>}
                              {property.special_notes && <p>Notes: {property.special_notes}</p>}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-8">
                      <div className="w-12 h-12 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-3">
                        <MapPin className="h-6 w-6 text-slate-400" />
                      </div>
                      <p className="text-slate-500">No properties yet</p>
                      <p className="text-sm text-slate-400 mt-1">Add a property to track service locations</p>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* AI Communication Drafts */}
              <div className="lg:col-span-2">
                <AICommunicationDrafts
                  draft={draft}
                  isLoading={isDraftLoading}
                  error={draftError ? new Error(draftError) : null}
                  onSendNow={sendNow}
                  onScheduleLater={(draftId) => scheduleLater(draftId, '')}
                />
              </div>
            </div>
          </TabsContent>

          {/* Photos Tab */}
          <TabsContent value="photos" data-testid="tab-content-photos">
            <PhotoGallery customerId={customer.id} />
          </TabsContent>

          {/* Invoice History Tab */}
          <TabsContent value="invoices" data-testid="tab-content-invoices">
            <InvoiceHistory customerId={customer.id} />
          </TabsContent>

          {/* Payment Methods Tab */}
          <TabsContent value="payment-methods" data-testid="tab-content-payment-methods">
            <PaymentMethods customerId={customer.id} />
          </TabsContent>

          {/* Messages Tab */}
          <TabsContent value="messages" data-testid="tab-content-messages">
            <CustomerMessages customerId={customer.id} />
          </TabsContent>

          {/* Potential Duplicates Tab */}
          <TabsContent value="duplicates" data-testid="tab-content-duplicates">
            <DuplicateReview customerId={customer.id} />
          </TabsContent>
        </Tabs>
      </div>

      {/* Add Property Dialog */}
      <Dialog open={showAddPropertyDialog} onOpenChange={setShowAddPropertyDialog}>
        <DialogContent className="max-w-md" data-testid="add-property-dialog">
          <DialogHeader>
            <DialogTitle>Add Property</DialogTitle>
            <DialogDescription>
              Add a service property for {getCustomerFullName(customer)}.
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
            <Button variant="outline" onClick={() => setShowAddPropertyDialog(false)} data-testid="cancel-property-btn">
              Cancel
            </Button>
            <Button onClick={handleAddProperty} data-testid="save-property-btn">
              Add Property
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
