import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog,
  DialogContent,
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
import type { ServicePreference, ServicePreferenceCreate } from '../types';

const SERVICE_TYPES = [
  { value: 'spring_startup', label: 'Spring Startup' },
  { value: 'mid_season_inspection', label: 'Mid-Season Inspection' },
  { value: 'fall_winterization', label: 'Fall Winterization' },
  { value: 'monthly_visit', label: 'Monthly Visit' },
  { value: 'custom', label: 'Custom' },
] as const;

const TIME_WINDOWS = [
  { value: 'morning', label: 'Morning' },
  { value: 'afternoon', label: 'Afternoon' },
  { value: 'evening', label: 'Evening' },
  { value: 'any', label: 'Any' },
] as const;

interface ServicePreferenceModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSave: (data: ServicePreferenceCreate) => void;
  preference?: ServicePreference | null;
  isPending?: boolean;
}

function ModalForm({
  onSave,
  onCancel,
  preference,
  isPending,
}: {
  onSave: (data: ServicePreferenceCreate) => void;
  onCancel: () => void;
  preference?: ServicePreference | null;
  isPending?: boolean;
}) {
  const [serviceType, setServiceType] = useState(preference?.service_type ?? 'spring_startup');
  const [preferredWeek, setPreferredWeek] = useState(preference?.preferred_week ?? '');
  const [preferredDate, setPreferredDate] = useState(preference?.preferred_date ?? '');
  const [timeWindow, setTimeWindow] = useState(preference?.time_window ?? 'any');
  const [notes, setNotes] = useState(preference?.notes ?? '');

  const handleSubmit = () => {
    onSave({
      service_type: serviceType,
      preferred_week: preferredWeek || null,
      preferred_date: preferredDate || null,
      time_window: timeWindow,
      notes: notes || null,
    });
  };

  return (
    <>
      <div className="space-y-4 py-2">
        <div className="space-y-2">
          <Label>Service Type</Label>
          <Select value={serviceType} onValueChange={setServiceType}>
            <SelectTrigger data-testid="service-type-select">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {SERVICE_TYPES.map((t) => (
                <SelectItem key={t.value} value={t.value}>
                  {t.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>Preferred Week (Monday date)</Label>
          <Input
            type="date"
            value={preferredWeek}
            onChange={(e) => setPreferredWeek(e.target.value)}
            data-testid="preferred-week-input"
          />
        </div>
        <div className="space-y-2">
          <Label>Preferred Specific Date (overrides week)</Label>
          <Input
            type="date"
            value={preferredDate}
            onChange={(e) => setPreferredDate(e.target.value)}
            data-testid="preferred-date-input"
          />
        </div>
        <div className="space-y-2">
          <Label>Time Window</Label>
          <Select value={timeWindow} onValueChange={setTimeWindow}>
            <SelectTrigger data-testid="time-window-select">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {TIME_WINDOWS.map((t) => (
                <SelectItem key={t.value} value={t.value}>
                  {t.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>Notes</Label>
          <Textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Additional notes..."
            rows={3}
            data-testid="preference-notes-input"
          />
        </div>
      </div>
      <div className="flex justify-end gap-2">
        <Button variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button onClick={handleSubmit} disabled={isPending} data-testid="save-preference-btn">
          {isPending ? 'Saving...' : preference ? 'Update' : 'Add'}
        </Button>
      </div>
    </>
  );
}

export function ServicePreferenceModal({
  open,
  onOpenChange,
  onSave,
  preference,
  isPending,
}: ServicePreferenceModalProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md" data-testid="service-preference-modal">
        <DialogHeader>
          <DialogTitle>{preference ? 'Edit' : 'Add'} Service Preference</DialogTitle>
        </DialogHeader>
        {open && (
          <ModalForm
            onSave={onSave}
            onCancel={() => onOpenChange(false)}
            preference={preference}
            isPending={isPending}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}
