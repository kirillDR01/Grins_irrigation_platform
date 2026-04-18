/**
 * LeadDetail page component.
 *
 * Displays full lead details with action buttons for managing the lead
 * through the pipeline: mark as contacted, convert to customer, mark as lost/spam.
 * Enhanced with full address fields (Req 12), action tag badges (Req 13),
 * attachment panel (Req 15), and estimate/contract creation (Req 17).
 *
 * H-1 (bughunt 2026-04-16): LeadDetail now mirrors the LeadsList routing
 * actions — Mark Contacted / Move to Jobs / Move to Sales / Delete — via the
 * shared ``useLeadRoutingActions`` hook. The CR-6 duplicate-conflict modal
 * is reused here so duplicate collisions surface regardless of entry point.
 * Also folds in L-4: Mark Contacted now flows through ``useMarkContacted``
 * so NEEDS_CONTACT tag cleanup and contacted_at stamping behave consistently.
 */

import { useState, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  ArrowLeft,
  Phone,
  Mail,
  MapPin,
  Globe,
  Clock,
  FileText,
  Trash2,
  UserPlus,
  PhoneCall,
  ExternalLink,
  Loader2,
  User,
  Briefcase,
  MessageSquare,
  FileCheck,
  AlertTriangle,
  ShoppingCart,
  Edit,
  CalendarClock,
} from 'lucide-react';
import { format } from 'date-fns';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Input } from '@/components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { LoadingPage, ErrorMessage, PageHeader } from '@/shared/components';
import { getErrorMessage } from '@/core/api';

import { useLead, useUpdateLead } from '../hooks';
import { useLeadRoutingActions } from '../hooks/useLeadRoutingActions';
import { LeadStatusBadge } from './LeadStatusBadge';
import { LeadSituationBadge } from './LeadSituationBadge';
import { LeadSourceBadge } from './LeadSourceBadge';
import { LeadTagBadges } from './LeadTagBadges';
import { LeadConversionConflictModal } from './LeadConversionConflictModal';
import { AttachmentPanel } from './AttachmentPanel';
import { NotesTimeline } from '@/shared/components/NotesTimeline';
import type { LeadStatus, LeadSituation, LeadSource, IntakeTag } from '../types';
import {
  LEAD_STATUS_LABELS,
  LEAD_SITUATION_LABELS,
  LEAD_SOURCE_LABELS,
} from '../types';
import { useStaff } from '@/features/staff/hooks/useStaff';

/** Valid status transitions for the dropdown */
const VALID_TRANSITIONS: Record<LeadStatus, LeadStatus[]> = {
  new: ['contacted'],
  contacted: ['new'],
  qualified: [],    // legacy — no transitions
  converted: [],    // legacy — no transitions
  lost: [],         // legacy — no transitions
  spam: [],         // legacy — no transitions
};

export function LeadDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: lead, isLoading, error, refetch } = useLead(id!);
  const updateMutation = useUpdateLead();
  const { data: staffData } = useStaff({ page_size: 100, is_active: true });

  // Shared routing hook (H-1) — drives Mark Contacted / Move to Jobs /
  // Move to Sales / Delete plus the CR-6 conflict + estimate-override flows.
  const {
    markContacted,
    moveToJobs,
    moveToSales,
    deleteLead,
    markContactedMutation,
    moveToJobsMutation,
    moveToSalesMutation,
    deleteLeadMutation,
    requiresEstimateState,
    resolveRequiresEstimate,
    closeRequiresEstimate,
    conflictState,
    onConvertAnyway,
    onUseExisting,
    closeConflict,
  } = useLeadRoutingActions({ navigate, navigateOnSuccess: true });

  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

  // ── Task 6.1: Contact info inline edit ──
  const [editingContact, setEditingContact] = useState(false);
  const [contactForm, setContactForm] = useState({ phone: '', email: '' });

  // ── Task 6.2: Service details inline edit ──
  const [editingService, setEditingService] = useState(false);
  const [serviceForm, setServiceForm] = useState({
    situation: '' as string,
    source_site: '',
    lead_source: '' as string,
    source_detail: '',
    intake_tag: '' as string,
  });

  // ── Task 6.3: Consent inline edit ──
  const [editingConsent, setEditingConsent] = useState(false);
  const [consentForm, setConsentForm] = useState({
    sms_consent: false,
    email_marketing_consent: false,
    terms_accepted: false,
  });

  // ── Task 6.4: Last Contacted inline edit ──
  const [editingLastContacted, setEditingLastContacted] = useState(false);
  const [lastContactedValue, setLastContactedValue] = useState('');

  // Editable address fields
  const [editingAddress, setEditingAddress] = useState(false);
  const [addressForm, setAddressForm] = useState({
    address: '',
    city: '',
    state: '',
    zip_code: '',
  });

  const startEditAddress = () => {
    if (!lead) return;
    setAddressForm({
      address: lead.address ?? '',
      city: lead.city ?? '',
      state: lead.state ?? '',
      zip_code: lead.zip_code ?? '',
    });
    setEditingAddress(true);
  };

  const saveAddress = async () => {
    if (!lead) return;
    try {
      await updateMutation.mutateAsync({
        id: lead.id,
        data: {
          address: addressForm.address || null,
          city: addressForm.city || null,
          state: addressForm.state || null,
          zip_code: addressForm.zip_code || null,
        },
      });
      toast.success('Address Updated');
      setEditingAddress(false);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to update address';
      toast.error('Update Failed', { description: message });
    }
  };

  // ── Task 6.1: Contact info save ──
  const startEditContact = () => {
    if (!lead) return;
    setContactForm({ phone: lead.phone ?? '', email: lead.email ?? '' });
    setEditingContact(true);
  };

  const saveContact = async () => {
    if (!lead) return;
    if (!contactForm.phone.trim()) {
      toast.error('Phone is required');
      return;
    }
    // Basic E.164 check: must start with + and have digits
    const phone = contactForm.phone.trim();
    if (!/^\+?\d{10,15}$/.test(phone.replace(/[\s()-]/g, ''))) {
      toast.error('Invalid phone format', { description: 'Use E.164 format (e.g. +16125551234)' });
      return;
    }
    try {
      await updateMutation.mutateAsync({
        id: lead.id,
        data: {
          phone: phone,
          email: contactForm.email.trim() || null,
        },
      });
      toast.success('Contact Info Updated');
      setEditingContact(false);
    } catch (err: unknown) {
      toast.error('Update Failed', { description: getErrorMessage(err) });
    }
  };

  // ── Task 6.2: Service details save ──
  const startEditService = () => {
    if (!lead) return;
    setServiceForm({
      situation: lead.situation ?? '',
      source_site: lead.source_site ?? '',
      lead_source: lead.lead_source ?? '',
      source_detail: lead.source_detail ?? '',
      intake_tag: lead.intake_tag ?? '',
    });
    setEditingService(true);
  };

  const saveService = async () => {
    if (!lead) return;
    try {
      await updateMutation.mutateAsync({
        id: lead.id,
        data: {
          situation: serviceForm.situation as LeadSituation,
          source_site: serviceForm.source_site || undefined,
          lead_source: serviceForm.lead_source as LeadSource,
          source_detail: serviceForm.source_detail || null,
          intake_tag: (serviceForm.intake_tag || null) as IntakeTag | null,
        },
      });
      toast.success('Service Details Updated');
      setEditingService(false);
    } catch (err: unknown) {
      toast.error('Update Failed', { description: getErrorMessage(err) });
    }
  };

  // ── Task 6.3: Consent save ──
  const startEditConsent = () => {
    if (!lead) return;
    setConsentForm({
      sms_consent: lead.sms_consent ?? false,
      email_marketing_consent: lead.email_marketing_consent ?? false,
      terms_accepted: lead.terms_accepted ?? false,
    });
    setEditingConsent(true);
  };

  const saveConsent = async () => {
    if (!lead) return;
    try {
      await updateMutation.mutateAsync({
        id: lead.id,
        data: {
          sms_consent: consentForm.sms_consent,
          email_marketing_consent: consentForm.email_marketing_consent,
          terms_accepted: consentForm.terms_accepted,
        },
      });
      toast.success('Consent Settings Updated');
      setEditingConsent(false);
    } catch (err: unknown) {
      toast.error('Update Failed', { description: getErrorMessage(err) });
    }
  };

  // ── Task 6.4: Last Contacted save ──
  const startEditLastContacted = () => {
    if (!lead) return;
    // Format for datetime-local input
    const val = lead.last_contacted_at
      ? format(new Date(lead.last_contacted_at), "yyyy-MM-dd'T'HH:mm")
      : '';
    setLastContactedValue(val);
    setEditingLastContacted(true);
  };

  const saveLastContacted = async () => {
    if (!lead) return;
    if (!lastContactedValue) {
      toast.error('Please select a date and time');
      return;
    }
    const dt = new Date(lastContactedValue);
    if (dt > new Date()) {
      toast.error('Validation Error', { description: 'Last contacted date cannot be in the future' });
      return;
    }
    if (dt < new Date(lead.created_at)) {
      toast.error('Validation Error', { description: 'Last contacted date cannot be before lead creation date' });
      return;
    }
    try {
      await updateMutation.mutateAsync({
        id: lead.id,
        data: { last_contacted_at: new Date(lastContactedValue).toISOString() },
      });
      toast.success('Last Contacted Updated');
      setEditingLastContacted(false);
    } catch (err: unknown) {
      toast.error('Update Failed', { description: getErrorMessage(err) });
    }
  };

  // Handle status change via dropdown
  const handleStatusChange = async (newStatus: string) => {
    if (!lead) return;
    try {
      await updateMutation.mutateAsync({
        id: lead.id,
        data: { status: newStatus as LeadStatus },
      });
      toast.success('Status Updated', {
        description: `Lead status changed to ${LEAD_STATUS_LABELS[newStatus as LeadStatus]}.`,
      });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to update status';
      toast.error('Update Failed', { description: message });
    }
  };

  // Handle staff assignment change
  const handleStaffChange = async (staffId: string) => {
    if (!lead) return;
    const assignedTo = staffId === 'unassigned' ? null : staffId;
    try {
      await updateMutation.mutateAsync({
        id: lead.id,
        data: { assigned_to: assignedTo },
      });
      toast.success('Staff Assigned', {
        description: assignedTo
          ? 'Lead assigned to staff member.'
          : 'Staff assignment removed.',
      });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to assign staff';
      toast.error('Assignment Failed', { description: message });
    }
  };

  const handleMarkContacted = useCallback(() => {
    if (!lead) return;
    void markContacted(lead);
  }, [lead, markContacted]);

  const handleMoveToJobs = useCallback(() => {
    if (!lead) return;
    void moveToJobs(lead);
  }, [lead, moveToJobs]);

  const handleMoveToSales = useCallback(() => {
    if (!lead) return;
    void moveToSales(lead);
  }, [lead, moveToSales]);

  const executeDelete = useCallback(async () => {
    if (!lead) return;
    try {
      const ok = await deleteLead(lead);
      if (ok) {
        navigate('/leads');
      }
    } finally {
      setShowDeleteDialog(false);
    }
  }, [lead, deleteLead, navigate]);

  const handleDelete = () => {
    if (!lead) return;
    setShowDeleteDialog(true);
  };

  if (isLoading) return <LoadingPage message="Loading lead..." />;
  if (error) return <ErrorMessage error={error} onRetry={() => refetch()} />;
  if (!lead) return <ErrorMessage error={new Error('Lead not found')} />;

  const isTerminal = lead.status === 'converted' || lead.status === 'spam';
  // H-1 / L-3: keep Mark Contacted visible on new, contacted so
  // admins can re-stamp on follow-up contact attempts.
  const canMarkContacted =
    lead.status === 'new' ||
    lead.status === 'contacted';
  const canRoute = !isTerminal && lead.status !== 'lost';
  const availableTransitions = VALID_TRANSITIONS[lead.status] ?? [];
  const assignedStaff = staffData?.items?.find((s) => s.id === lead.assigned_to);

  return (
    <div data-testid="lead-detail" className="animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* Back Button */}
      <div className="mb-6">
        <Button variant="ghost" size="sm" asChild className="text-slate-600 hover:text-slate-800">
          <Link to="/leads">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Leads
          </Link>
        </Button>
      </div>

      {/* Page Header */}
      <PageHeader
        title={lead.name}
        description={`Lead submitted ${format(new Date(lead.created_at), 'MMM d, yyyy \'at\' h:mm a')}`}
        action={
          <div className="flex gap-2 flex-wrap">
            {canMarkContacted && (
              <Button
                variant="outline"
                onClick={handleMarkContacted}
                disabled={markContactedMutation.isPending}
                data-testid="lead-detail-mark-contacted-btn"
                className="text-yellow-700 border-yellow-200 hover:bg-yellow-50"
              >
                {markContactedMutation.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <PhoneCall className="mr-2 h-4 w-4" />
                )}
                Mark as Contacted
              </Button>
            )}
            {canRoute && (
              <>
                <Button
                  variant="outline"
                  onClick={handleMoveToJobs}
                  disabled={moveToJobsMutation.isPending}
                  data-testid="lead-detail-move-to-jobs-btn"
                  className="text-blue-700 border-blue-200 hover:bg-blue-50"
                >
                  {moveToJobsMutation.isPending ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Briefcase className="mr-2 h-4 w-4" />
                  )}
                  Move to Jobs
                </Button>
                <Button
                  variant="outline"
                  onClick={handleMoveToSales}
                  disabled={moveToSalesMutation.isPending}
                  data-testid="lead-detail-move-to-sales-btn"
                  className="text-purple-700 border-purple-200 hover:bg-purple-50"
                >
                  {moveToSalesMutation.isPending ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <ShoppingCart className="mr-2 h-4 w-4" />
                  )}
                  Move to Sales
                </Button>
              </>
            )}
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleteLeadMutation.isPending}
              data-testid="lead-detail-delete-btn"
            >
              {deleteLeadMutation.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Trash2 className="mr-2 h-4 w-4" />
              )}
              Delete
            </Button>
          </div>
        }
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Main Info Card - spans 2 columns */}
        <Card className="lg:col-span-2 bg-white rounded-2xl shadow-sm border border-slate-100">
          <CardHeader className="border-b border-slate-100">
            <div className="flex items-center justify-between">
              <CardTitle className="text-2xl font-bold text-slate-800">{lead.name}</CardTitle>
              <LeadTagBadges tags={lead.action_tags ?? []} />
            </div>
          </CardHeader>
          <CardContent className="p-6 space-y-6">
            {/* Contact Information — Task 6.1 inline edit */}
            <div>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider">
                  Contact Information
                </h3>
                {!editingContact ? (
                  <Button variant="ghost" size="sm" onClick={startEditContact} data-testid="edit-contact-btn">
                    <Edit className="h-3.5 w-3.5 mr-1" />
                    Edit
                  </Button>
                ) : (
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={() => setEditingContact(false)} data-testid="cancel-contact-btn">Cancel</Button>
                    <Button size="sm" onClick={saveContact} disabled={updateMutation.isPending} data-testid="save-contact-btn">
                      {updateMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Save'}
                    </Button>
                  </div>
                )}
              </div>
              {editingContact ? (
                <div className="space-y-3" data-testid="contact-form">
                  <div>
                    <label className="text-xs text-slate-400 mb-1 block">Phone *</label>
                    <Input
                      placeholder="Phone (E.164, e.g. +16125551234)"
                      value={contactForm.phone}
                      onChange={(e) => setContactForm((p) => ({ ...p, phone: e.target.value }))}
                      data-testid="contact-phone-input"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-slate-400 mb-1 block">Email</label>
                    <Input
                      placeholder="Email (optional)"
                      type="email"
                      value={contactForm.email}
                      onChange={(e) => setContactForm((p) => ({ ...p, email: e.target.value }))}
                      data-testid="contact-email-input"
                    />
                  </div>
                </div>
              ) : (
                <div className="space-y-4" data-testid="contact-display">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-slate-100 rounded-lg">
                      <Phone className="h-5 w-5 text-slate-600" />
                    </div>
                    <div>
                      <p className="text-xs text-slate-400">Phone</p>
                      <a href={`tel:${lead.phone}`} className="font-medium text-slate-700 hover:text-teal-600 transition-colors">
                        {lead.phone}
                      </a>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-slate-100 rounded-lg">
                      <Mail className="h-5 w-5 text-slate-600" />
                    </div>
                    <div>
                      <p className="text-xs text-slate-400">Email</p>
                      {lead.email ? (
                        <a href={`mailto:${lead.email}`} className="font-medium text-slate-700 hover:text-teal-600 transition-colors">
                          {lead.email}
                        </a>
                      ) : (
                        <span className="text-slate-400 italic">Not provided</span>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>

            <Separator className="bg-slate-100" />

            {/* Full Address (Req 12) */}
            <div>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider">
                  Address
                </h3>
                {!editingAddress ? (
                  <Button variant="ghost" size="sm" onClick={startEditAddress} data-testid="edit-address-btn">
                    Edit
                  </Button>
                ) : (
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={() => setEditingAddress(false)}>Cancel</Button>
                    <Button size="sm" onClick={saveAddress} disabled={updateMutation.isPending} data-testid="save-address-btn">
                      {updateMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Save'}
                    </Button>
                  </div>
                )}
              </div>
              {editingAddress ? (
                <div className="space-y-3" data-testid="address-form">
                  <Input
                    placeholder="Street Address"
                    value={addressForm.address}
                    onChange={(e) => setAddressForm((p) => ({ ...p, address: e.target.value }))}
                    data-testid="address-input"
                  />
                  <div className="grid grid-cols-3 gap-3">
                    <Input
                      placeholder="City"
                      value={addressForm.city}
                      onChange={(e) => setAddressForm((p) => ({ ...p, city: e.target.value }))}
                      data-testid="city-input"
                    />
                    <Input
                      placeholder="State"
                      value={addressForm.state}
                      onChange={(e) => setAddressForm((p) => ({ ...p, state: e.target.value }))}
                      data-testid="state-input"
                    />
                    <Input
                      placeholder="Zip Code"
                      value={addressForm.zip_code}
                      onChange={(e) => setAddressForm((p) => ({ ...p, zip_code: e.target.value }))}
                      data-testid="zip-code-input"
                    />
                  </div>
                </div>
              ) : (
                <div className="flex items-start gap-3">
                  <div className="p-2 bg-slate-100 rounded-lg">
                    <MapPin className="h-5 w-5 text-slate-600" />
                  </div>
                  <div data-testid="address-display">
                    {lead.address || lead.city || lead.state || lead.zip_code ? (
                      <>
                        {lead.address && <p className="font-medium text-slate-700">{lead.address}</p>}
                        <p className="text-slate-600">
                          {[lead.city, lead.state].filter(Boolean).join(', ')}
                          {lead.zip_code ? ` ${lead.zip_code}` : ''}
                        </p>
                      </>
                    ) : (
                      <p className="text-slate-400 italic">No address provided</p>
                    )}
                  </div>
                </div>
              )}
            </div>

            <Separator className="bg-slate-100" />

            {/* Service Details — Task 6.2 inline edit */}
            <div>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider">
                  Service Details
                </h3>
                {!editingService ? (
                  <Button variant="ghost" size="sm" onClick={startEditService} data-testid="edit-service-btn">
                    <Edit className="h-3.5 w-3.5 mr-1" />
                    Edit
                  </Button>
                ) : (
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={() => setEditingService(false)} data-testid="cancel-service-btn">Cancel</Button>
                    <Button size="sm" onClick={saveService} disabled={updateMutation.isPending} data-testid="save-service-btn">
                      {updateMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Save'}
                    </Button>
                  </div>
                )}
              </div>
              {editingService ? (
                <div className="space-y-3" data-testid="service-form">
                  <div>
                    <label className="text-xs text-slate-400 mb-1 block">Situation</label>
                    <Select value={serviceForm.situation} onValueChange={(v) => setServiceForm((p) => ({ ...p, situation: v }))}>
                      <SelectTrigger data-testid="service-situation-select">
                        <SelectValue placeholder="Select situation..." />
                      </SelectTrigger>
                      <SelectContent>
                        {(Object.entries(LEAD_SITUATION_LABELS) as [string, string][]).map(([val, label]) => (
                          <SelectItem key={val} value={val}>{label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <label className="text-xs text-slate-400 mb-1 block">Source Site</label>
                    <Input
                      placeholder="Source site"
                      value={serviceForm.source_site}
                      onChange={(e) => setServiceForm((p) => ({ ...p, source_site: e.target.value }))}
                      data-testid="service-source-site-input"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-slate-400 mb-1 block">Lead Source</label>
                    <Select value={serviceForm.lead_source} onValueChange={(v) => setServiceForm((p) => ({ ...p, lead_source: v }))}>
                      <SelectTrigger data-testid="service-lead-source-select">
                        <SelectValue placeholder="Select lead source..." />
                      </SelectTrigger>
                      <SelectContent>
                        {(Object.entries(LEAD_SOURCE_LABELS) as [string, string][]).map(([val, label]) => (
                          <SelectItem key={val} value={val}>{label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <label className="text-xs text-slate-400 mb-1 block">Source Detail</label>
                    <Input
                      placeholder="Source detail (optional)"
                      value={serviceForm.source_detail}
                      onChange={(e) => setServiceForm((p) => ({ ...p, source_detail: e.target.value }))}
                      data-testid="service-source-detail-input"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-slate-400 mb-1 block">Intake Tag</label>
                    <Select value={serviceForm.intake_tag || '_none'} onValueChange={(v) => setServiceForm((p) => ({ ...p, intake_tag: v === '_none' ? '' : v }))}>
                      <SelectTrigger data-testid="service-intake-tag-select">
                        <SelectValue placeholder="None" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="_none">None</SelectItem>
                        <SelectItem value="schedule">Schedule</SelectItem>
                        <SelectItem value="follow_up">Follow Up</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              ) : (
                <div className="space-y-4" data-testid="service-display">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-slate-100 rounded-lg"><Briefcase className="h-5 w-5 text-slate-600" /></div>
                    <div>
                      <p className="text-xs text-slate-400">Situation</p>
                      <LeadSituationBadge situation={lead.situation} />
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-slate-100 rounded-lg"><Globe className="h-5 w-5 text-slate-600" /></div>
                    <div>
                      <p className="text-xs text-slate-400">Source Site</p>
                      <p className="font-medium text-slate-700">{lead.source_site}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-slate-100 rounded-lg"><Globe className="h-5 w-5 text-slate-600" /></div>
                    <div>
                      <p className="text-xs text-slate-400">Lead Source</p>
                      <LeadSourceBadge source={lead.lead_source} />
                    </div>
                  </div>
                  {lead.source_detail && (
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-slate-100 rounded-lg"><Globe className="h-5 w-5 text-slate-600" /></div>
                      <div>
                        <p className="text-xs text-slate-400">Source Detail</p>
                        <p className="font-medium text-slate-700">{lead.source_detail}</p>
                      </div>
                    </div>
                  )}
                  {lead.intake_tag && (
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-slate-100 rounded-lg"><Globe className="h-5 w-5 text-slate-600" /></div>
                      <div>
                        <p className="text-xs text-slate-400">Intake Tag</p>
                        <p className="font-medium text-slate-700 capitalize">{lead.intake_tag.replace('_', ' ')}</p>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Notes Timeline */}
            <Separator className="bg-slate-100" />
            <NotesTimeline subjectType="lead" subjectId={lead.id} />

            {/* Consent Status — Task 6.3 inline edit */}
            <Separator className="bg-slate-100" />
            <div>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider">Consent Status</h3>
                {!editingConsent ? (
                  <Button variant="ghost" size="sm" onClick={startEditConsent} data-testid="edit-consent-btn">
                    <Edit className="h-3.5 w-3.5 mr-1" />
                    Edit
                  </Button>
                ) : (
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={() => setEditingConsent(false)} data-testid="cancel-consent-btn">Cancel</Button>
                    <Button size="sm" onClick={saveConsent} disabled={updateMutation.isPending} data-testid="save-consent-btn">
                      {updateMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Save'}
                    </Button>
                  </div>
                )}
              </div>
              {editingConsent ? (
                <div className="space-y-4" data-testid="consent-form">
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={consentForm.sms_consent}
                      onChange={(e) => setConsentForm((p) => ({ ...p, sms_consent: e.target.checked }))}
                      className="h-4 w-4 rounded border-slate-300 text-teal-600 focus:ring-teal-500"
                      data-testid="consent-sms-input"
                    />
                    <span className="text-sm text-slate-700">SMS Consent</span>
                  </label>
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={consentForm.email_marketing_consent}
                      onChange={(e) => setConsentForm((p) => ({ ...p, email_marketing_consent: e.target.checked }))}
                      className="h-4 w-4 rounded border-slate-300 text-teal-600 focus:ring-teal-500"
                      data-testid="consent-email-marketing-input"
                    />
                    <span className="text-sm text-slate-700">Email Marketing Consent</span>
                  </label>
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={consentForm.terms_accepted}
                      onChange={(e) => setConsentForm((p) => ({ ...p, terms_accepted: e.target.checked }))}
                      className="h-4 w-4 rounded border-slate-300 text-teal-600 focus:ring-teal-500"
                      data-testid="consent-terms-input"
                    />
                    <span className="text-sm text-slate-700">Terms &amp; Conditions Accepted</span>
                  </label>
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4" data-testid="consent-display">
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg ${lead.sms_consent ? 'bg-green-100' : 'bg-gray-100'}`}>
                      <MessageSquare className={`h-5 w-5 ${lead.sms_consent ? 'text-green-600' : 'text-gray-400'}`} />
                    </div>
                    <div>
                      <p className="text-xs text-slate-400">SMS Consent</p>
                      <p className={`text-sm font-medium ${lead.sms_consent ? 'text-green-700' : 'text-gray-500'}`}
                         data-testid={`sms-consent-${lead.id}`}>
                        {lead.sms_consent ? 'Given' : 'Not given'}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg ${lead.email_marketing_consent ? 'bg-green-100' : 'bg-gray-100'}`}>
                      <FileCheck className={`h-5 w-5 ${lead.email_marketing_consent ? 'text-green-600' : 'text-gray-400'}`} />
                    </div>
                    <div>
                      <p className="text-xs text-slate-400">Email Marketing Consent</p>
                      <p className={`text-sm font-medium ${lead.email_marketing_consent ? 'text-green-700' : 'text-gray-500'}`}
                         data-testid={`email-marketing-consent-${lead.id}`}>
                        {lead.email_marketing_consent ? 'Opted in' : 'Not opted in'}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg ${lead.terms_accepted ? 'bg-green-100' : 'bg-gray-100'}`}>
                      <FileCheck className={`h-5 w-5 ${lead.terms_accepted ? 'text-green-600' : 'text-gray-400'}`} />
                    </div>
                    <div>
                      <p className="text-xs text-slate-400">Terms &amp; Conditions</p>
                      <p className={`text-sm font-medium ${lead.terms_accepted ? 'text-green-700' : 'text-gray-500'}`}
                         data-testid={`terms-accepted-${lead.id}`}>
                        {lead.terms_accepted ? 'Accepted' : 'Not accepted'}
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Converted Links */}
            {lead.status === 'converted' && (
              <>
                <Separator className="bg-slate-100" />
                <div>
                  <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-4">Conversion Details</h3>
                  <div className="space-y-3">
                    {lead.customer_id && (
                      <Link
                        to={`/customers/${lead.customer_id}`}
                        data-testid="customer-link"
                        className="flex items-center gap-3 p-3 bg-green-50 rounded-xl hover:bg-green-100 transition-colors group"
                      >
                        <div className="p-2 bg-green-100 rounded-lg group-hover:bg-green-200 transition-colors">
                          <User className="h-5 w-5 text-green-700" />
                        </div>
                        <div className="flex-1">
                          <p className="text-sm font-medium text-green-800">View Customer</p>
                          <p className="text-xs text-green-600">Navigate to the converted customer record</p>
                        </div>
                        <ExternalLink className="h-4 w-4 text-green-600" />
                      </Link>
                    )}
                    <Link
                      to={`/jobs?customer_id=${lead.customer_id}`}
                      data-testid="job-link"
                      className="flex items-center gap-3 p-3 bg-blue-50 rounded-xl hover:bg-blue-100 transition-colors group"
                    >
                      <div className="p-2 bg-blue-100 rounded-lg group-hover:bg-blue-200 transition-colors">
                        <Briefcase className="h-5 w-5 text-blue-700" />
                      </div>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-blue-800">View Jobs</p>
                        <p className="text-xs text-blue-600">View jobs for this customer</p>
                      </div>
                      <ExternalLink className="h-4 w-4 text-blue-600" />
                    </Link>
                  </div>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        {/* Right Column - Status, Actions, Attachments */}
        <div className="space-y-6">
          {/* Status Card */}
          <Card className="bg-white rounded-2xl shadow-sm border border-slate-100">
            <CardHeader className="border-b border-slate-100">
              <CardTitle className="font-bold text-slate-800">Status & Assignment</CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-5">
              <div>
                <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">Current Status</p>
                <LeadStatusBadge status={lead.status} className="text-sm" />
              </div>

              {availableTransitions.length > 0 && (
                <div>
                  <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">Change Status</p>
                  <Select value="" onValueChange={handleStatusChange} disabled={updateMutation.isPending}>
                    <SelectTrigger className="w-full bg-slate-50 border-slate-200 rounded-lg" data-testid="lead-status-dropdown">
                      <SelectValue placeholder="Select new status..." />
                    </SelectTrigger>
                    <SelectContent>
                      {availableTransitions.map((status) => (
                        <SelectItem key={status} value={status}>{LEAD_STATUS_LABELS[status]}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}

              <Separator className="bg-slate-100" />

              <div>
                <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">Assigned To</p>
                <Select value={lead.assigned_to ?? 'unassigned'} onValueChange={handleStaffChange} disabled={updateMutation.isPending}>
                  <SelectTrigger className="w-full bg-slate-50 border-slate-200 rounded-lg" data-testid="lead-staff-select">
                    <SelectValue placeholder="Unassigned">
                      {assignedStaff ? assignedStaff.name : 'Unassigned'}
                    </SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="unassigned">Unassigned</SelectItem>
                    {staffData?.items?.map((staff) => (
                      <SelectItem key={staff.id} value={staff.id}>{staff.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <Separator className="bg-slate-100" />

              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <Clock className="h-4 w-4 text-slate-400" />
                  <div>
                    <p className="text-xs text-slate-400">Submitted</p>
                    <p className="text-sm font-medium text-slate-700">
                      {format(new Date(lead.created_at), 'MMM d, yyyy \'at\' h:mm a')}
                    </p>
                  </div>
                </div>
                {lead.contacted_at && (
                  <div className="flex items-center gap-2">
                    <PhoneCall className="h-4 w-4 text-yellow-500" />
                    <div>
                      <p className="text-xs text-slate-400">Contacted</p>
                      <p className="text-sm font-medium text-slate-700">
                        {format(new Date(lead.contacted_at), 'MMM d, yyyy \'at\' h:mm a')}
                      </p>
                    </div>
                  </div>
                )}
                {/* Task 6.4: Last Contacted inline edit */}
                <div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <CalendarClock className="h-4 w-4 text-teal-500" />
                      <div>
                        <p className="text-xs text-slate-400">Last Contacted</p>
                        {!editingLastContacted ? (
                          <p className="text-sm font-medium text-slate-700" data-testid="last-contacted-display">
                            {lead.last_contacted_at
                              ? format(new Date(lead.last_contacted_at), 'MMM d, yyyy \'at\' h:mm a')
                              : <span className="text-slate-400 italic">Not set</span>}
                          </p>
                        ) : null}
                      </div>
                    </div>
                    {!editingLastContacted ? (
                      <Button variant="ghost" size="sm" onClick={startEditLastContacted} data-testid="edit-last-contacted-btn" className="h-6 px-2 text-xs">
                        <Edit className="h-3 w-3 mr-1" />
                        Edit
                      </Button>
                    ) : null}
                  </div>
                  {editingLastContacted && (
                    <div className="mt-2 space-y-2" data-testid="last-contacted-form">
                      <Input
                        type="datetime-local"
                        value={lastContactedValue}
                        onChange={(e) => setLastContactedValue(e.target.value)}
                        max={format(new Date(), "yyyy-MM-dd'T'HH:mm")}
                        data-testid="last-contacted-input"
                      />
                      {lead.last_contacted_at && (
                        <p className="text-xs text-slate-400">
                          {lead.contacted_at && lead.last_contacted_at === lead.contacted_at
                            ? '⚙️ System-set (auto-stamped)'
                            : '✏️ Manually overridden'}
                        </p>
                      )}
                      <div className="flex gap-2">
                        <Button variant="outline" size="sm" onClick={() => setEditingLastContacted(false)} data-testid="cancel-last-contacted-btn" className="text-xs h-7">Cancel</Button>
                        <Button size="sm" onClick={saveLastContacted} disabled={updateMutation.isPending} data-testid="save-last-contacted-btn" className="text-xs h-7">
                          {updateMutation.isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : 'Save'}
                        </Button>
                      </div>
                    </div>
                  )}
                  {!editingLastContacted && lead.last_contacted_at && (
                    <p className="text-xs text-slate-400 mt-0.5 ml-6" data-testid="last-contacted-indicator">
                      {lead.contacted_at && lead.last_contacted_at === lead.contacted_at
                        ? '⚙️ System-set'
                        : '✏️ Manual override'}
                    </p>
                  )}
                </div>
                {lead.converted_at && (
                  <div className="flex items-center gap-2">
                    <UserPlus className="h-4 w-4 text-green-500" />
                    <div>
                      <p className="text-xs text-slate-400">Converted</p>
                      <p className="text-sm font-medium text-slate-700">
                        {format(new Date(lead.converted_at), 'MMM d, yyyy \'at\' h:mm a')}
                      </p>
                    </div>
                  </div>
                )}
                <div className="flex items-center gap-2">
                  <Clock className="h-4 w-4 text-slate-400" />
                  <div>
                    <p className="text-xs text-slate-400">Last Updated</p>
                    <p className="text-sm font-medium text-slate-700">
                      {format(new Date(lead.updated_at), 'MMM d, yyyy \'at\' h:mm a')}
                    </p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Quick Actions Card */}
          {!isTerminal && (
            <Card className="bg-white rounded-2xl shadow-sm border border-slate-100">
              <CardHeader className="border-b border-slate-100">
                <CardTitle className="font-bold text-slate-800">Quick Actions</CardTitle>
              </CardHeader>
              <CardContent className="p-6 space-y-3">
                {canMarkContacted && (
                  <Button
                    variant="outline"
                    className="w-full justify-start text-yellow-700 border-yellow-200 hover:bg-yellow-50"
                    onClick={handleMarkContacted}
                    disabled={markContactedMutation.isPending}
                  >
                    <PhoneCall className="mr-2 h-4 w-4" />Mark as Contacted
                  </Button>
                )}
              </CardContent>
            </Card>
          )}

          {/* Attachments Panel (Req 15) */}
          <AttachmentPanel leadId={lead.id} />
        </div>
      </div>

      {/* Delete Confirmation Dialog */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent data-testid="delete-confirmation-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-red-500" />
              Delete Lead
            </DialogTitle>
            <DialogDescription>
              Are you sure you want to delete <span className="font-semibold text-slate-700">{lead.name}</span>? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowDeleteDialog(false)}
              disabled={deleteLeadMutation.isPending}
              data-testid="cancel-delete-btn"
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={executeDelete}
              disabled={deleteLeadMutation.isPending}
              data-testid="confirm-delete-btn"
            >
              {deleteLeadMutation.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Trash2 className="mr-2 h-4 w-4" />
              )}
              Delete Lead
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Requires-estimate override modal (H-1) */}
      <Dialog
        open={!!requiresEstimateState}
        onOpenChange={(open) => !open && closeRequiresEstimate()}
      >
        <DialogContent data-testid="lead-detail-requires-estimate-modal">
          <DialogHeader>
            <DialogTitle>Estimate Required</DialogTitle>
            <DialogDescription>
              This job type typically requires an estimate. Move to Jobs anyway, or move to Sales for the estimate workflow?
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="flex flex-col sm:flex-row gap-2">
            <Button
              variant="outline"
              onClick={() => resolveRequiresEstimate('cancel')}
              data-testid="lead-detail-requires-estimate-cancel-btn"
            >
              Cancel
            </Button>
            <Button
              variant="default"
              className="bg-purple-600 hover:bg-purple-700 text-white"
              onClick={() => resolveRequiresEstimate('sales')}
              disabled={moveToSalesMutation.isPending}
              data-testid="lead-detail-requires-estimate-move-to-sales-btn"
            >
              Move to Sales
            </Button>
            <Button
              variant="default"
              className="bg-blue-600 hover:bg-blue-700 text-white"
              onClick={() => resolveRequiresEstimate('jobs-force')}
              disabled={moveToJobsMutation.isPending}
              data-testid="lead-detail-requires-estimate-move-to-jobs-btn"
            >
              Move to Jobs
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Duplicate Conflict Modal (CR-6) */}
      {conflictState && (
        <LeadConversionConflictModal
          open={conflictState !== null}
          onClose={closeConflict}
          duplicates={conflictState.duplicates}
          onUseExisting={onUseExisting}
          onConvertAnyway={onConvertAnyway}
          isConverting={
            moveToJobsMutation.isPending || moveToSalesMutation.isPending
          }
          phone={conflictState.phone}
          email={conflictState.email}
        />
      )}
    </div>
  );
}

export default LeadDetail;
