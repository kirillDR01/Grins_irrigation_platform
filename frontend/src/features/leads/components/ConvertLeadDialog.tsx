/**
 * ConvertLeadDialog component.
 *
 * Dialog for converting a lead into a customer (and optionally a job).
 * Pre-fills first_name/last_name from auto-split of lead name.
 * Offers toggle for creating a job during conversion with auto-suggested description.
 *
 * Validates: Requirement 10.5-10.8
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { UserPlus, Briefcase, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';

import { useConvertLead } from '../hooks';
import type { Lead, LeadSituation } from '../types';

interface ConvertLeadDialogProps {
  /** The lead to convert */
  lead: Lead;
  /** Whether the dialog is open */
  open: boolean;
  /** Callback when dialog open state changes */
  onOpenChange: (open: boolean) => void;
}

/** Map situation to auto-suggested job description */
const SITUATION_JOB_DESCRIPTIONS: Record<LeadSituation, string> = {
  new_system: 'New irrigation system installation',
  upgrade: 'Irrigation system upgrade',
  repair: 'Irrigation system repair',
  exploring: 'Irrigation consultation',
};

/**
 * Split a full name into first and last name.
 * - "John Doe" → ["John", "Doe"]
 * - "John Michael Doe" → ["John", "Michael Doe"]
 * - "Viktor" → ["Viktor", ""]
 */
function splitName(fullName: string): [string, string] {
  const trimmed = fullName.trim();
  const spaceIndex = trimmed.indexOf(' ');
  if (spaceIndex === -1) {
    return [trimmed, ''];
  }
  return [trimmed.substring(0, spaceIndex), trimmed.substring(spaceIndex + 1)];
}

/**
 * ConvertLeadDialog allows converting a lead to a customer with optional job creation.
 * Uses a key-based remount strategy to reset form state when the dialog opens.
 */
export function ConvertLeadDialog({
  lead,
  open,
  onOpenChange,
}: ConvertLeadDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="max-w-md bg-white rounded-2xl shadow-xl"
        data-testid="convert-lead-dialog"
      >
        {/* Key forces remount when dialog opens, resetting all form state */}
        {open && (
          <ConvertLeadForm
            lead={lead}
            onOpenChange={onOpenChange}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}

interface ConvertLeadFormProps {
  lead: Lead;
  onOpenChange: (open: boolean) => void;
}

/**
 * Inner form component that initializes state from lead props on mount.
 * Remounted each time the dialog opens to reset form state cleanly.
 */
function ConvertLeadForm({ lead, onOpenChange }: ConvertLeadFormProps) {
  const navigate = useNavigate();
  const convertMutation = useConvertLead();

  // Auto-split lead name into first/last on mount
  const [defaultFirst, defaultLast] = splitName(lead.name);

  const [firstName, setFirstName] = useState(defaultFirst);
  const [lastName, setLastName] = useState(defaultLast);
  const [createJob, setCreateJob] = useState(true);
  const [jobDescription, setJobDescription] = useState(
    SITUATION_JOB_DESCRIPTIONS[lead.situation] ?? ''
  );

  const handleSubmit = async () => {
    try {
      const result = await convertMutation.mutateAsync({
        id: lead.id,
        data: {
          first_name: firstName.trim(),
          last_name: lastName.trim(),
          create_job: createJob,
          job_description: createJob ? jobDescription.trim() : undefined,
        },
      });

      toast.success('Lead Converted', {
        description: result.message || 'Lead successfully converted to customer.',
      });

      onOpenChange(false);

      // Navigate to the new customer detail page
      if (result.customer_id) {
        navigate(`/customers/${result.customer_id}`);
      }
    } catch (error: unknown) {
      const message =
        error instanceof Error ? error.message : 'Failed to convert lead';
      toast.error('Conversion Failed', {
        description: message,
      });
    }
  };

  return (
    <>
      <DialogHeader className="pb-2">
        <DialogTitle className="flex items-center gap-2 text-lg font-bold text-slate-800">
          <UserPlus className="h-5 w-5 text-teal-600" />
          Convert Lead to Customer
        </DialogTitle>
        <DialogDescription className="text-slate-500 text-sm">
          Create a new customer from <span className="font-medium">{lead.name}</span>.
          Review and edit the name fields below.
        </DialogDescription>
      </DialogHeader>

      <div className="space-y-5 py-4">
        {/* Name Fields */}
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="convert-first-name" className="text-sm font-medium text-slate-700">
              First Name
            </Label>
            <Input
              id="convert-first-name"
              data-testid="convert-first-name"
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
              placeholder="First name"
              className="bg-slate-50 border-slate-200 rounded-lg focus:ring-2 focus:ring-teal-100 focus:border-teal-500"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="convert-last-name" className="text-sm font-medium text-slate-700">
              Last Name
            </Label>
            <Input
              id="convert-last-name"
              data-testid="convert-last-name"
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
              placeholder="Last name"
              className="bg-slate-50 border-slate-200 rounded-lg focus:ring-2 focus:ring-teal-100 focus:border-teal-500"
            />
          </div>
        </div>

        {/* Create Job Toggle */}
        <div className="p-4 bg-slate-50 rounded-xl space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Briefcase className="h-4 w-4 text-slate-500" />
              <Label
                htmlFor="convert-create-job"
                className="text-sm font-medium text-slate-700 cursor-pointer"
              >
                Create job during conversion
              </Label>
            </div>
            <Switch
              id="convert-create-job"
              data-testid="convert-create-job"
              checked={createJob}
              onCheckedChange={setCreateJob}
            />
          </div>

          {/* Job Description (shown when toggle is on) */}
          {createJob && (
            <div className="space-y-2">
              <Label
                htmlFor="convert-job-description"
                className="text-sm font-medium text-slate-600"
              >
                Job Description
              </Label>
              <Input
                id="convert-job-description"
                data-testid="convert-job-description"
                value={jobDescription}
                onChange={(e) => setJobDescription(e.target.value)}
                placeholder="Describe the job..."
                className="bg-white border-slate-200 rounded-lg focus:ring-2 focus:ring-teal-100 focus:border-teal-500"
              />
            </div>
          )}
        </div>
      </div>

      <DialogFooter className="pt-2">
        <Button
          variant="outline"
          onClick={() => onOpenChange(false)}
          disabled={convertMutation.isPending}
          className="bg-white hover:bg-slate-50 border-slate-200 text-slate-700"
        >
          Cancel
        </Button>
        <Button
          data-testid="convert-submit-btn"
          onClick={handleSubmit}
          disabled={convertMutation.isPending || !firstName.trim()}
          className="bg-teal-500 hover:bg-teal-600 text-white shadow-sm shadow-teal-200"
        >
          {convertMutation.isPending ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Converting...
            </>
          ) : (
            <>
              <UserPlus className="mr-2 h-4 w-4" />
              Convert to Customer
            </>
          )}
        </Button>
      </DialogFooter>
    </>
  );
}

export default ConvertLeadDialog;
