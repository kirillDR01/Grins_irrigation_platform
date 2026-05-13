/**
 * CustomerDetail page component.
 *
 * Phase 6 inline edits:
 * - Task 6.5: Basic info (first_name, last_name, phone, email)
 * - Task 6.6: Primary address (PATCHes Property row)
 * - Task 6.7: Communication prefs, lead source, flags, status
 * - Task 6.8: Properties section with full CRUD
 */

import { useState, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  ArrowLeft, Phone, Mail, Edit, Trash2, Plus, MapPin, Dog,
  Image, FileText, CreditCard, MessageSquare, Users, Loader2,
  Star, AlertTriangle,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { AddressAutocomplete } from '@/shared/components/AddressAutocomplete';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { StatusBadge, LoadingPage, ErrorMessage, PageHeader, InternalNotesCard, OptOutBadge } from '@/shared/components';
import { TagPicker } from '@/features/customers/components/TagPicker';
import { ConsentHistoryPanel } from '@/features/customers/components/ConsentHistoryPanel';
import {
  useCustomer,
  useDeleteCustomer,
  useUpdateCustomer,
  useAddProperty,
  useUpdateProperty,
  useDeleteProperty,
  useSetPropertyPrimary,
} from '../hooks';
import {
  getCustomerFlags,
  getCustomerFullName,
  CUSTOMER_STATUS_LABELS,
} from '../types';
import type { CustomerStatus, Property } from '../types';
import { LEAD_SOURCE_LABELS } from '@/features/leads/types';
import { toast } from 'sonner';
import { getErrorMessage } from '@/core/api';
import { AICommunicationDrafts } from '@/features/ai/components';
import { useAICommunication } from '@/features/ai/hooks/useAICommunication';
import { PhotoGallery } from './PhotoGallery';
import { InvoiceHistory } from './InvoiceHistory';
import { PaymentMethods } from './PaymentMethods';
import { CustomerMessages } from './CustomerMessages';
import { DuplicateReview } from './DuplicateReview';
import { ServicePreferencesSection } from './ServicePreferencesSection';

interface CustomerDetailProps {
  onEdit?: () => void;
}

export function CustomerDetail({ onEdit }: CustomerDetailProps) {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: customer, isLoading, error, refetch } = useCustomer(id!);
  const deleteMutation = useDeleteCustomer();
  const updateMutation = useUpdateCustomer();
  const addPropertyMutation = useAddProperty(id!);
  const updatePropertyMutation = useUpdateProperty(id!);
  const deletePropertyMutation = useDeleteProperty(id!);
  const setPrimaryMutation = useSetPropertyPrimary(id!);
  const { draft, isLoading: isDraftLoading, error: draftError, sendNow, scheduleLater } = useAICommunication();

  // Internal notes save handler — wired to InternalNotesCard
  const handleSaveCustomerNotes = useCallback(
    async (next: string | null) => {
      if (!customer) return;
      await updateMutation.mutateAsync({
        id: customer.id,
        data: { internal_notes: next },
      });
    },
    [customer, updateMutation],
  );

  // ── Task 6.5: Basic info inline edit ──
  const [editingBasicInfo, setEditingBasicInfo] = useState(false);
  const [basicInfoForm, setBasicInfoForm] = useState({
    first_name: '', last_name: '', phone: '', email: '',
  });

  // ── Task 6.6: Primary address inline edit ──
  const [editingAddress, setEditingAddress] = useState(false);
  const [addressForm, setAddressForm] = useState({
    address: '', city: '', state: 'MN', zip_code: '',
  });

  // ── Task 6.7: Comm prefs, lead source, flags, status ──
  const [editingPrefs, setEditingPrefs] = useState(false);
  const [prefsForm, setPrefsForm] = useState({
    sms_opt_in: false, email_opt_in: false,
    lead_source: '' as string, lead_source_details: '' as string,
    is_priority: false, is_red_flag: false, is_slow_payer: false,
    status: 'active' as string,
  });

  // ── Task 6.8: Property management ──
  const [showAddPropertyDialog, setShowAddPropertyDialog] = useState(false);
  const [newPropertyForm, setNewPropertyForm] = useState({
    address: '', city: '', state: 'MN', zip_code: '',
    gate_code: '', access_instructions: '', has_dogs: false,
    property_type: 'residential', zone_count: '' as string,
    special_notes: '',
  });
  const [editingPropertyId, setEditingPropertyId] = useState<string | null>(null);
  const [editPropertyForm, setEditPropertyForm] = useState<Record<string, string | boolean>>({});
  const [showDeletePropertyDialog, setShowDeletePropertyDialog] = useState<string | null>(null);

  const handleDelete = async () => {
    if (!customer) return;
    if (window.confirm(`Are you sure you want to delete ${getCustomerFullName(customer)}?`)) {
      try {
        await deleteMutation.mutateAsync(customer.id);
        toast.success('Customer deleted successfully');
        navigate('/customers');
      } catch (err) {
        toast.error('Failed to delete customer', { description: getErrorMessage(err) });
      }
    }
  };

  // ── Task 6.5: Basic info handlers ──
  const startEditBasicInfo = () => {
    if (!customer) return;
    setBasicInfoForm({
      first_name: customer.first_name,
      last_name: customer.last_name,
      phone: customer.phone,
      email: customer.email ?? '',
    });
    setEditingBasicInfo(true);
  };

  const saveBasicInfo = async () => {
    if (!customer) return;
    if (!basicInfoForm.first_name.trim()) { toast.error('First name is required'); return; }
    if (!basicInfoForm.last_name.trim()) { toast.error('Last name is required'); return; }
    if (!basicInfoForm.phone.trim()) { toast.error('Phone is required'); return; }
    const phone = basicInfoForm.phone.replace(/[\s()-]/g, '');
    if (!/^\+?\d{10,15}$/.test(phone)) {
      toast.error('Invalid phone', { description: 'Enter a 10-digit phone number' });
      return;
    }
    try {
      await updateMutation.mutateAsync({
        id: customer.id,
        data: {
          first_name: basicInfoForm.first_name.trim(),
          last_name: basicInfoForm.last_name.trim(),
          phone: phone,
          email: basicInfoForm.email.trim() || null,
        },
      });
      toast.success('Basic Info Updated');
      setEditingBasicInfo(false);
    } catch (err) {
      toast.error('Update Failed', { description: getErrorMessage(err) });
    }
  };

  // ── Task 6.6: Primary address handlers ──
  const primaryProperty = customer?.properties?.find((p) => p.is_primary) ?? customer?.properties?.[0];

  const startEditAddress = () => {
    if (!primaryProperty) return;
    setAddressForm({
      address: primaryProperty.address ?? '',
      city: primaryProperty.city ?? '',
      state: primaryProperty.state ?? 'MN',
      zip_code: primaryProperty.zip_code ?? '',
    });
    setEditingAddress(true);
  };

  const saveAddress = async () => {
    if (!primaryProperty) return;
    try {
      await updatePropertyMutation.mutateAsync({
        propertyId: primaryProperty.id,
        data: {
          address: addressForm.address || undefined,
          city: addressForm.city || undefined,
          state: addressForm.state || undefined,
          zip_code: addressForm.zip_code || undefined,
        },
      });
      toast.success('Address Updated');
      setEditingAddress(false);
    } catch (err) {
      toast.error('Update Failed', { description: getErrorMessage(err) });
    }
  };

  const handleAddPrimaryProperty = async () => {
    try {
      await addPropertyMutation.mutateAsync({
        address: '(New property)',
        city: '',
        state: 'MN',
        is_primary: true,
      } as Partial<Property>);
      toast.success('Primary property created — edit the address now');
    } catch (err) {
      toast.error('Failed to add property', { description: getErrorMessage(err) });
    }
  };

  // ── Task 6.7: Prefs/flags/status handlers ──
  const startEditPrefs = () => {
    if (!customer) return;
    setPrefsForm({
      sms_opt_in: customer.sms_opt_in,
      email_opt_in: customer.email_opt_in,
      lead_source: customer.lead_source ?? '',
      lead_source_details: customer.lead_source_details ?? '',
      is_priority: customer.is_priority,
      is_red_flag: customer.is_red_flag,
      is_slow_payer: customer.is_slow_payer,
      status: customer.status ?? 'active',
    });
    setEditingPrefs(true);
  };

  const savePrefs = async () => {
    if (!customer) return;
    try {
      await updateMutation.mutateAsync({
        id: customer.id,
        data: {
          sms_opt_in: prefsForm.sms_opt_in,
          email_opt_in: prefsForm.email_opt_in,
          lead_source: prefsForm.lead_source || null,
          lead_source_details: prefsForm.lead_source_details || null,
          is_priority: prefsForm.is_priority,
          is_red_flag: prefsForm.is_red_flag,
          is_slow_payer: prefsForm.is_slow_payer,
          status: prefsForm.status as CustomerStatus,
        },
      });
      toast.success('Customer Settings Updated');
      setEditingPrefs(false);
    } catch (err) {
      toast.error('Update Failed', { description: getErrorMessage(err) });
    }
  };

  // ── Task 6.8: Property CRUD handlers ──
  const handleAddProperty = async () => {
    if (!newPropertyForm.address.trim()) {
      toast.error('Please enter a street address');
      return;
    }
    try {
      await addPropertyMutation.mutateAsync({
        address: newPropertyForm.address.trim(),
        city: newPropertyForm.city.trim(),
        state: newPropertyForm.state.trim() || 'MN',
        zip_code: newPropertyForm.zip_code.trim() || undefined,
        gate_code: newPropertyForm.gate_code.trim() || undefined,
        access_instructions: newPropertyForm.access_instructions.trim() || undefined,
        has_dogs: newPropertyForm.has_dogs,
        property_type: newPropertyForm.property_type,
        zone_count: newPropertyForm.zone_count ? parseInt(newPropertyForm.zone_count) : undefined,
        special_notes: newPropertyForm.special_notes.trim() || undefined,
      } as Partial<Property>);
      toast.success('Property added');
      setNewPropertyForm({
        address: '', city: '', state: 'MN', zip_code: '',
        gate_code: '', access_instructions: '', has_dogs: false,
        property_type: 'residential', zone_count: '', special_notes: '',
      });
      setShowAddPropertyDialog(false);
    } catch (err) {
      toast.error('Failed to add property', { description: getErrorMessage(err) });
    }
  };

  const startEditProperty = (property: Property) => {
    setEditingPropertyId(property.id);
    setEditPropertyForm({
      address: property.address,
      city: property.city,
      state: property.state,
      zip_code: property.zip_code ?? '',
      gate_code: property.gate_code ?? '',
      access_instructions: property.access_instructions ?? '',
      has_dogs: property.has_dogs,
      property_type: property.property_type,
      zone_count: property.zone_count?.toString() ?? '',
      special_notes: property.special_notes ?? '',
    });
  };

  const saveEditProperty = async () => {
    if (!editingPropertyId) return;
    try {
      await updatePropertyMutation.mutateAsync({
        propertyId: editingPropertyId,
        data: {
          address: editPropertyForm.address as string || undefined,
          city: editPropertyForm.city as string || undefined,
          state: editPropertyForm.state as string || undefined,
          zip_code: (editPropertyForm.zip_code as string) || undefined,
          gate_code: (editPropertyForm.gate_code as string) || undefined,
          access_instructions: (editPropertyForm.access_instructions as string) || undefined,
          has_dogs: editPropertyForm.has_dogs as boolean,
          property_type: editPropertyForm.property_type as string,
          zone_count: editPropertyForm.zone_count ? parseInt(editPropertyForm.zone_count as string) : undefined,
          special_notes: (editPropertyForm.special_notes as string) || undefined,
        } as Partial<Property>,
      });
      toast.success('Property updated');
      setEditingPropertyId(null);
    } catch (err) {
      toast.error('Failed to update property', { description: getErrorMessage(err) });
    }
  };

  const handleDeleteProperty = async (propertyId: string) => {
    try {
      await deletePropertyMutation.mutateAsync(propertyId);
      toast.success('Property deleted');
      setShowDeletePropertyDialog(null);
    } catch (err) {
      toast.error('Cannot delete property', { description: getErrorMessage(err) });
    }
  };

  const handleSetPrimary = async (propertyId: string) => {
    try {
      await setPrimaryMutation.mutateAsync(propertyId);
      toast.success('Primary property updated');
    } catch (err) {
      toast.error('Failed to set primary', { description: getErrorMessage(err) });
    }
  };

  if (isLoading) return <LoadingPage message="Loading customer..." />;
  if (error) return <ErrorMessage error={error} onRetry={() => refetch()} />;
  if (!customer) return <ErrorMessage error={new Error('Customer not found')} />;

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
        description={
          <span className="inline-flex flex-wrap items-center gap-2">
            <span>{`Customer since ${new Date(customer.created_at).toLocaleDateString()}`}</span>
            <OptOutBadge customerId={customer.id} />
          </span>
        }
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
        {/* Main Info Card — Task 6.5 + 6.6 */}
        <Card className="lg:col-span-2 bg-white rounded-2xl shadow-sm border border-slate-100">
          <CardHeader className="border-b border-slate-100">
            <CardTitle className="text-2xl font-bold text-slate-800">{getCustomerFullName(customer)}</CardTitle>
          </CardHeader>
          <CardContent className="p-6 space-y-6">
            {/* Task 6.5: Basic Info inline edit */}
            <div>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider">Contact Information</h3>
                {!editingBasicInfo ? (
                  <Button variant="ghost" size="sm" onClick={startEditBasicInfo} data-testid="edit-basic-info-btn">
                    <Edit className="h-3.5 w-3.5 mr-1" />Edit
                  </Button>
                ) : (
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={() => setEditingBasicInfo(false)} data-testid="cancel-basic-info-btn">Cancel</Button>
                    <Button size="sm" onClick={saveBasicInfo} disabled={updateMutation.isPending} data-testid="save-basic-info-btn">
                      {updateMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Save'}
                    </Button>
                  </div>
                )}
              </div>
              {editingBasicInfo ? (
                <div className="space-y-3" data-testid="basic-info-form">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-xs text-slate-400 mb-1 block">First Name *</label>
                      <Input value={basicInfoForm.first_name} onChange={(e) => setBasicInfoForm((p) => ({ ...p, first_name: e.target.value }))} data-testid="basic-first-name-input" />
                    </div>
                    <div>
                      <label className="text-xs text-slate-400 mb-1 block">Last Name *</label>
                      <Input value={basicInfoForm.last_name} onChange={(e) => setBasicInfoForm((p) => ({ ...p, last_name: e.target.value }))} data-testid="basic-last-name-input" />
                    </div>
                  </div>
                  <div>
                    <label className="text-xs text-slate-400 mb-1 block">Phone *</label>
                    <Input value={basicInfoForm.phone} onChange={(e) => setBasicInfoForm((p) => ({ ...p, phone: e.target.value }))} data-testid="basic-phone-input" />
                  </div>
                  <div>
                    <label className="text-xs text-slate-400 mb-1 block">Email</label>
                    <Input type="email" value={basicInfoForm.email} onChange={(e) => setBasicInfoForm((p) => ({ ...p, email: e.target.value }))} data-testid="basic-email-input" />
                  </div>
                </div>
              ) : (
                <div className="space-y-4" data-testid="basic-info-display">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-slate-100 rounded-lg"><Phone className="h-5 w-5 text-slate-600" /></div>
                    <div>
                      <p className="text-xs text-slate-400">Phone</p>
                      <a href={`tel:${customer.phone}`} className="font-medium text-slate-700 hover:text-teal-600 transition-colors">{customer.phone}</a>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-slate-100 rounded-lg"><Mail className="h-5 w-5 text-slate-600" /></div>
                    <div>
                      <p className="text-xs text-slate-400">Email</p>
                      {customer.email ? (
                        <a href={`mailto:${customer.email}`} className="font-medium text-slate-700 hover:text-teal-600 transition-colors">{customer.email}</a>
                      ) : (
                        <span className="text-slate-400 italic">Not provided</span>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>

            <Separator className="bg-slate-100" />

            {/* Task 6.6: Primary Address inline edit */}
            <div>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider">Address</h3>
                {primaryProperty && !editingAddress ? (
                  <Button variant="ghost" size="sm" onClick={startEditAddress} data-testid="edit-address-btn">
                    <Edit className="h-3.5 w-3.5 mr-1" />Edit
                  </Button>
                ) : editingAddress ? (
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={() => setEditingAddress(false)} data-testid="cancel-address-btn">Cancel</Button>
                    <Button size="sm" onClick={saveAddress} disabled={updatePropertyMutation.isPending} data-testid="save-address-btn">
                      {updatePropertyMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Save'}
                    </Button>
                  </div>
                ) : null}
              </div>
              {editingAddress ? (
                <div className="space-y-3" data-testid="address-form">
                  <AddressAutocomplete placeholder="Street Address" value={addressForm.address} onChange={(v) => setAddressForm((p) => ({ ...p, address: v }))} data-testid="address-input" />
                  <div className="grid grid-cols-3 gap-3">
                    <Input placeholder="City" value={addressForm.city} onChange={(e) => setAddressForm((p) => ({ ...p, city: e.target.value }))} data-testid="city-input" />
                    <Input placeholder="State" value={addressForm.state} onChange={(e) => setAddressForm((p) => ({ ...p, state: e.target.value }))} data-testid="state-input" />
                    <Input placeholder="Zip Code" value={addressForm.zip_code} onChange={(e) => setAddressForm((p) => ({ ...p, zip_code: e.target.value }))} data-testid="zip-code-input" />
                  </div>
                </div>
              ) : (
                <div className="flex items-start gap-3">
                  <div className="p-2 bg-slate-100 rounded-lg"><MapPin className="h-5 w-5 text-slate-600" /></div>
                  <div data-testid="address-display">
                    {primaryProperty ? (
                      <p className="font-medium text-slate-700">
                        {primaryProperty.address}, {primaryProperty.city}, {primaryProperty.state} {primaryProperty.zip_code}
                      </p>
                    ) : (
                      <div>
                        <p className="text-slate-400 italic">No primary property</p>
                        <Button variant="link" size="sm" className="text-teal-600 p-0 h-auto mt-1" onClick={handleAddPrimaryProperty} data-testid="add-primary-property-btn">
                          <Plus className="h-3 w-3 mr-1" />Add primary property
                        </Button>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Right Column — Task 6.7: Comm prefs, lead source, flags, status */}
        <Card>
          <CardHeader className="border-b border-slate-100">
            <div className="flex items-center justify-between">
              <CardTitle className="font-bold text-slate-800">Customer Settings</CardTitle>
              {!editingPrefs ? (
                <Button variant="ghost" size="sm" onClick={startEditPrefs} data-testid="edit-prefs-btn">
                  <Edit className="h-3.5 w-3.5 mr-1" />Edit
                </Button>
              ) : (
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => setEditingPrefs(false)} data-testid="cancel-prefs-btn">Cancel</Button>
                  <Button size="sm" onClick={savePrefs} disabled={updateMutation.isPending} data-testid="save-prefs-btn">
                    {updateMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Save'}
                  </Button>
                </div>
              )}
            </div>
          </CardHeader>
          <CardContent className="p-6 space-y-4">
            {editingPrefs ? (
              <div className="space-y-4" data-testid="prefs-form">
                {/* Status */}
                <div>
                  <label className="text-xs text-slate-400 uppercase tracking-wider mb-1 block">Status</label>
                  <Select value={prefsForm.status} onValueChange={(v) => setPrefsForm((p) => ({ ...p, status: v }))}>
                    <SelectTrigger data-testid="prefs-status-select"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {(Object.entries(CUSTOMER_STATUS_LABELS) as [string, string][]).map(([val, label]) => (
                        <SelectItem key={val} value={val}>{label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                {/* Communication Preferences */}
                <div>
                  <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">Communication Preferences</p>
                  <label className="flex items-center gap-3 cursor-pointer mb-2">
                    <input type="checkbox" checked={prefsForm.sms_opt_in} onChange={(e) => setPrefsForm((p) => ({ ...p, sms_opt_in: e.target.checked }))} className="h-4 w-4 rounded border-slate-300 text-teal-600" data-testid="prefs-sms-input" />
                    <span className="text-sm text-slate-700">SMS Opt-in</span>
                  </label>
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input type="checkbox" checked={prefsForm.email_opt_in} onChange={(e) => setPrefsForm((p) => ({ ...p, email_opt_in: e.target.checked }))} className="h-4 w-4 rounded border-slate-300 text-teal-600" data-testid="prefs-email-input" />
                    <span className="text-sm text-slate-700">Email Opt-in</span>
                  </label>
                </div>
                {/* Lead Source */}
                <div>
                  <label className="text-xs text-slate-400 uppercase tracking-wider mb-1 block">Lead Source</label>
                  <Select value={prefsForm.lead_source || '_none'} onValueChange={(v) => setPrefsForm((p) => ({ ...p, lead_source: v === '_none' ? '' : v }))}>
                    <SelectTrigger data-testid="prefs-lead-source-select"><SelectValue placeholder="None" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="_none">None</SelectItem>
                      {(Object.entries(LEAD_SOURCE_LABELS) as [string, string][]).map(([val, label]) => (
                        <SelectItem key={val} value={val}>{label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <label className="text-xs text-slate-400 uppercase tracking-wider mb-1 block">Lead Source Details</label>
                  <Input value={prefsForm.lead_source_details} onChange={(e) => setPrefsForm((p) => ({ ...p, lead_source_details: e.target.value }))} placeholder="Details..." data-testid="prefs-lead-source-details-input" />
                </div>
                {/* Flags */}
                <div>
                  <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">Flags</p>
                  <label className="flex items-center gap-3 cursor-pointer mb-2">
                    <input type="checkbox" checked={prefsForm.is_priority} onChange={(e) => setPrefsForm((p) => ({ ...p, is_priority: e.target.checked }))} className="h-4 w-4 rounded border-slate-300 text-teal-600" data-testid="prefs-priority-input" />
                    <span className="text-sm text-slate-700">⭐ Priority</span>
                  </label>
                  <label className="flex items-center gap-3 cursor-pointer mb-2">
                    <input type="checkbox" checked={prefsForm.is_red_flag} onChange={(e) => setPrefsForm((p) => ({ ...p, is_red_flag: e.target.checked }))} className="h-4 w-4 rounded border-slate-300 text-teal-600" data-testid="prefs-red-flag-input" />
                    <span className="text-sm text-slate-700">🚩 Red Flag</span>
                  </label>
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input type="checkbox" checked={prefsForm.is_slow_payer} onChange={(e) => setPrefsForm((p) => ({ ...p, is_slow_payer: e.target.checked }))} className="h-4 w-4 rounded border-slate-300 text-teal-600" data-testid="prefs-slow-payer-input" />
                    <span className="text-sm text-slate-700">🐢 Slow Payer</span>
                  </label>
                </div>
              </div>
            ) : (
              <div data-testid="prefs-display">
                {/* Status */}
                <div className="mb-3">
                  <p className="text-xs text-slate-400 uppercase tracking-wider mb-1">Status</p>
                  <StatusBadge status={customer.status ?? 'active'} type="customer" />
                </div>
                {/* Flags */}
                <div className="flex gap-2 flex-wrap mb-3" data-testid="customer-flags">
                  {flags.length > 0 ? flags.map((flag) => (
                    <StatusBadge key={flag} status={flag} type="customer" />
                  )) : (
                    <span className="text-slate-400 italic text-sm">No flags</span>
                  )}
                </div>
                <Separator className="bg-slate-100 my-3" />
                {/* Communication Preferences */}
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
                    <Separator className="bg-slate-100 my-3" />
                    <div>
                      <p className="text-xs text-slate-400 uppercase tracking-wider mb-1">Lead Source</p>
                      <p className="font-medium text-slate-700">{customer.lead_source}</p>
                      {customer.lead_source_details && (
                        <p className="text-xs text-slate-500 mt-0.5">{customer.lead_source_details}</p>
                      )}
                    </div>
                  </>
                )}
                <Separator className="bg-slate-100 my-3" />
                <div>
                  <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">Property Notes</p>
                  <div className="space-y-2">
                    {customer.properties?.some((p) => p.has_dogs) ? (
                      <div className="flex items-center gap-2">
                        <Dog className="h-4 w-4 text-amber-500" />
                        <span className="text-sm text-amber-700 font-medium">Dogs on Property</span>
                      </div>
                    ) : (
                      <span className="text-sm text-slate-400 italic">No special notes</span>
                    )}
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Gap 06: SMS consent history timeline */}
      <div className="mt-6">
        <ConsentHistoryPanel customerId={customer.id} />
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
              {/* Tags */}
              <Card data-testid="customer-tags-card">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-semibold text-slate-500 uppercase tracking-wider">
                    Tags
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <TagPicker customerId={customer.id} />
                </CardContent>
              </Card>

              {/* Internal Notes Card */}
              <InternalNotesCard
                value={customer.internal_notes}
                onSave={handleSaveCustomerNotes}
                isSaving={updateMutation.isPending}
                data-testid-prefix="customer-"
              />

              {/* Service Preferences */}
              <ServicePreferencesSection customerId={customer.id} />

              {/* Task 6.8: Properties Section with full CRUD */}
              <Card className="lg:col-span-2" data-testid="properties-section">
                <CardHeader className="border-b border-slate-100">
                  <div className="flex items-center justify-between">
                    <CardTitle className="flex items-center gap-2 font-bold text-slate-800">
                      <MapPin className="h-5 w-5 text-teal-500" />
                      Properties
                    </CardTitle>
                    <Button variant="outline" size="sm" onClick={() => setShowAddPropertyDialog(true)} data-testid="add-property-btn" className="text-teal-600 border-teal-200 hover:bg-teal-50">
                      <Plus className="mr-2 h-4 w-4" />Add Property
                    </Button>
                  </div>
                </CardHeader>
                <CardContent className="p-6">
                  {customer.properties && customer.properties.length > 0 ? (
                    <div className="space-y-4">
                      {customer.properties.map((property) => (
                        <div key={property.id} className="rounded-lg border border-slate-100 p-4 space-y-2" data-testid={`property-${property.id}`}>
                          {editingPropertyId === property.id ? (
                            /* Inline property edit form */
                            <div className="space-y-3" data-testid={`property-edit-form-${property.id}`}>
                              <div className="grid grid-cols-2 gap-3">
                                <div>
                                  <label className="text-xs text-slate-400 mb-1 block">Address</label>
                                  <Input value={editPropertyForm.address as string} onChange={(e) => setEditPropertyForm((p) => ({ ...p, address: e.target.value }))} data-testid="prop-edit-address" />
                                </div>
                                <div>
                                  <label className="text-xs text-slate-400 mb-1 block">City</label>
                                  <Input value={editPropertyForm.city as string} onChange={(e) => setEditPropertyForm((p) => ({ ...p, city: e.target.value }))} data-testid="prop-edit-city" />
                                </div>
                              </div>
                              <div className="grid grid-cols-3 gap-3">
                                <div>
                                  <label className="text-xs text-slate-400 mb-1 block">State</label>
                                  <Input value={editPropertyForm.state as string} onChange={(e) => setEditPropertyForm((p) => ({ ...p, state: e.target.value }))} data-testid="prop-edit-state" />
                                </div>
                                <div>
                                  <label className="text-xs text-slate-400 mb-1 block">Zip</label>
                                  <Input value={editPropertyForm.zip_code as string} onChange={(e) => setEditPropertyForm((p) => ({ ...p, zip_code: e.target.value }))} data-testid="prop-edit-zip" />
                                </div>
                                <div>
                                  <label className="text-xs text-slate-400 mb-1 block">Zone Count</label>
                                  <Input type="number" value={editPropertyForm.zone_count as string} onChange={(e) => setEditPropertyForm((p) => ({ ...p, zone_count: e.target.value }))} data-testid="prop-edit-zones" />
                                </div>
                              </div>
                              <div className="grid grid-cols-2 gap-3">
                                <div>
                                  <label className="text-xs text-slate-400 mb-1 block">Gate Code</label>
                                  <Input value={editPropertyForm.gate_code as string} onChange={(e) => setEditPropertyForm((p) => ({ ...p, gate_code: e.target.value }))} data-testid="prop-edit-gate-code" />
                                </div>
                                <div>
                                  <label className="text-xs text-slate-400 mb-1 block">Property Type</label>
                                  <Select value={editPropertyForm.property_type as string} onValueChange={(v) => setEditPropertyForm((p) => ({ ...p, property_type: v }))}>
                                    <SelectTrigger data-testid="prop-edit-type"><SelectValue /></SelectTrigger>
                                    <SelectContent>
                                      <SelectItem value="residential">Residential</SelectItem>
                                      <SelectItem value="commercial">Commercial</SelectItem>
                                    </SelectContent>
                                  </Select>
                                </div>
                              </div>
                              <div>
                                <label className="text-xs text-slate-400 mb-1 block">Access Instructions</label>
                                <Input value={editPropertyForm.access_instructions as string} onChange={(e) => setEditPropertyForm((p) => ({ ...p, access_instructions: e.target.value }))} data-testid="prop-edit-access" />
                              </div>
                              <div>
                                <label className="text-xs text-slate-400 mb-1 block">Special Notes</label>
                                <Input value={editPropertyForm.special_notes as string} onChange={(e) => setEditPropertyForm((p) => ({ ...p, special_notes: e.target.value }))} data-testid="prop-edit-notes" />
                              </div>
                              <label className="flex items-center gap-2 cursor-pointer">
                                <input type="checkbox" checked={editPropertyForm.has_dogs as boolean} onChange={(e) => setEditPropertyForm((p) => ({ ...p, has_dogs: e.target.checked }))} className="h-4 w-4 rounded" data-testid="prop-edit-dogs" />
                                <span className="text-sm text-slate-700">Dogs on property</span>
                              </label>
                              <div className="flex gap-2 pt-2">
                                <Button variant="outline" size="sm" onClick={() => setEditingPropertyId(null)} data-testid={`cancel-edit-property-${property.id}`}>Cancel</Button>
                                <Button size="sm" onClick={saveEditProperty} disabled={updatePropertyMutation.isPending} data-testid={`save-edit-property-${property.id}`}>
                                  {updatePropertyMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Save'}
                                </Button>
                              </div>
                            </div>
                          ) : (
                            /* Property display */
                            <>
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
                                <div className="flex items-center gap-1">
                                  {property.has_dogs && (
                                    <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-1 text-xs font-medium text-amber-700">
                                      <Dog className="h-3 w-3" />Dogs
                                    </span>
                                  )}
                                  {!property.is_primary && (
                                    <Button variant="ghost" size="sm" onClick={() => handleSetPrimary(property.id)} data-testid={`set-primary-${property.id}`} className="text-xs h-7 px-2 text-teal-600">
                                      <Star className="h-3 w-3 mr-1" />Set Primary
                                    </Button>
                                  )}
                                  <Button variant="ghost" size="sm" onClick={() => startEditProperty(property)} data-testid={`edit-property-${property.id}`} className="text-xs h-7 px-2">
                                    <Edit className="h-3 w-3" />
                                  </Button>
                                  <Button variant="ghost" size="sm" onClick={() => setShowDeletePropertyDialog(property.id)} data-testid={`delete-property-${property.id}`} className="text-xs h-7 px-2 text-red-500 hover:text-red-700">
                                    <Trash2 className="h-3 w-3" />
                                  </Button>
                                </div>
                              </div>
                              {(property.access_instructions || property.gate_code || property.special_notes) && (
                                <div className="text-xs text-slate-500 space-y-1 pt-1 border-t border-slate-50">
                                  {property.gate_code && <p>Gate Code: <span className="font-medium text-slate-600">{property.gate_code}</span></p>}
                                  {property.access_instructions && <p>Access: {property.access_instructions}</p>}
                                  {property.special_notes && <p>Notes: {property.special_notes}</p>}
                                </div>
                              )}
                            </>
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

          <TabsContent value="photos" data-testid="tab-content-photos">
            <PhotoGallery customerId={customer.id} />
          </TabsContent>
          <TabsContent value="invoices" data-testid="tab-content-invoices">
            <InvoiceHistory customerId={customer.id} />
          </TabsContent>
          <TabsContent value="payment-methods" data-testid="tab-content-payment-methods">
            <PaymentMethods customerId={customer.id} />
          </TabsContent>
          <TabsContent value="messages" data-testid="tab-content-messages">
            <CustomerMessages customerId={customer.id} />
          </TabsContent>
          <TabsContent value="duplicates" data-testid="tab-content-duplicates">
            <DuplicateReview customerId={customer.id} />
          </TabsContent>
        </Tabs>
      </div>

      {/* Add Property Dialog — Task 6.8 */}
      <Dialog open={showAddPropertyDialog} onOpenChange={setShowAddPropertyDialog}>
        <DialogContent className="max-w-lg" data-testid="add-property-dialog">
          <DialogHeader>
            <DialogTitle>Add Property</DialogTitle>
            <DialogDescription>
              Add a service property for {getCustomerFullName(customer)}.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="property-address">Street Address *</Label>
              <AddressAutocomplete id="property-address" value={newPropertyForm.address} onChange={(v) => setNewPropertyForm((p) => ({ ...p, address: v }))} placeholder="123 Main St" data-testid="new-property-address-input" />
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label htmlFor="property-city">City</Label>
                <Input id="property-city" value={newPropertyForm.city} onChange={(e) => setNewPropertyForm((p) => ({ ...p, city: e.target.value }))} placeholder="Eden Prairie" data-testid="new-property-city-input" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="property-state">State</Label>
                <Input id="property-state" value={newPropertyForm.state} onChange={(e) => setNewPropertyForm((p) => ({ ...p, state: e.target.value }))} placeholder="MN" data-testid="new-property-state-input" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="property-zip">ZIP</Label>
                <Input id="property-zip" value={newPropertyForm.zip_code} onChange={(e) => setNewPropertyForm((p) => ({ ...p, zip_code: e.target.value }))} placeholder="55344" data-testid="new-property-zip-input" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="property-gate-code">Gate Code</Label>
                <Input id="property-gate-code" value={newPropertyForm.gate_code} onChange={(e) => setNewPropertyForm((p) => ({ ...p, gate_code: e.target.value }))} placeholder="1234" data-testid="new-property-gate-code-input" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="property-type">Property Type</Label>
                <Select value={newPropertyForm.property_type} onValueChange={(v) => setNewPropertyForm((p) => ({ ...p, property_type: v }))}>
                  <SelectTrigger data-testid="new-property-type-select"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="residential">Residential</SelectItem>
                    <SelectItem value="commercial">Commercial</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="property-zones">Zone Count</Label>
                <Input id="property-zones" type="number" value={newPropertyForm.zone_count} onChange={(e) => setNewPropertyForm((p) => ({ ...p, zone_count: e.target.value }))} placeholder="6" data-testid="new-property-zones-input" />
              </div>
              <div className="flex items-end pb-2">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" checked={newPropertyForm.has_dogs} onChange={(e) => setNewPropertyForm((p) => ({ ...p, has_dogs: e.target.checked }))} className="h-4 w-4 rounded" data-testid="new-property-dogs-input" />
                  <span className="text-sm text-slate-700">Dogs on property</span>
                </label>
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="property-access">Access Instructions</Label>
              <Input id="property-access" value={newPropertyForm.access_instructions} onChange={(e) => setNewPropertyForm((p) => ({ ...p, access_instructions: e.target.value }))} placeholder="Enter through side gate..." data-testid="new-property-access-input" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="property-notes">Special Notes</Label>
              <Input id="property-notes" value={newPropertyForm.special_notes} onChange={(e) => setNewPropertyForm((p) => ({ ...p, special_notes: e.target.value }))} placeholder="Any special notes..." data-testid="new-property-notes-input" />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setShowAddPropertyDialog(false)} data-testid="cancel-add-property-btn">Cancel</Button>
            <Button onClick={handleAddProperty} disabled={addPropertyMutation.isPending} data-testid="save-add-property-btn">
              {addPropertyMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
              Add Property
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Delete Property Confirmation Dialog — Task 6.8 */}
      <Dialog open={!!showDeletePropertyDialog} onOpenChange={(open) => !open && setShowDeletePropertyDialog(null)}>
        <DialogContent data-testid="delete-property-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-red-500" />
              Delete Property
            </DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this property? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDeletePropertyDialog(null)} data-testid="cancel-delete-property-btn">Cancel</Button>
            <Button variant="destructive" onClick={() => showDeletePropertyDialog && handleDeleteProperty(showDeletePropertyDialog)} disabled={deletePropertyMutation.isPending} data-testid="confirm-delete-property-btn">
              {deletePropertyMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Trash2 className="h-4 w-4 mr-2" />}
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
