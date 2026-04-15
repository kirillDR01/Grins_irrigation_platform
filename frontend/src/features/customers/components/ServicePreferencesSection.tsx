import { useState } from 'react';
import { Plus, Edit, Trash2, Clock } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { toast } from 'sonner';
import {
  useServicePreferences,
  useAddServicePreference,
  useUpdateServicePreference,
  useDeleteServicePreference,
} from '../hooks';
import { ServicePreferenceModal } from './ServicePreferenceModal';
import type { ServicePreference, ServicePreferenceCreate } from '../types';

const SERVICE_TYPE_LABELS: Record<string, string> = {
  spring_startup: 'Spring Startup',
  mid_season_inspection: 'Mid-Season Inspection',
  fall_winterization: 'Fall Winterization',
  monthly_visit: 'Monthly Visit',
  custom: 'Custom',
};

const TIME_WINDOW_LABELS: Record<string, string> = {
  morning: 'Morning',
  afternoon: 'Afternoon',
  evening: 'Evening',
  any: 'Any',
};

interface ServicePreferencesSectionProps {
  customerId: string;
}

export function ServicePreferencesSection({ customerId }: ServicePreferencesSectionProps) {
  const { data: preferences = [], isLoading } = useServicePreferences(customerId);
  const addMutation = useAddServicePreference(customerId);
  const updateMutation = useUpdateServicePreference(customerId);
  const deleteMutation = useDeleteServicePreference(customerId);

  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<ServicePreference | null>(null);

  const handleAdd = () => {
    setEditing(null);
    setModalOpen(true);
  };

  const handleEdit = (pref: ServicePreference) => {
    setEditing(pref);
    setModalOpen(true);
  };

  const handleDelete = async (prefId: string) => {
    try {
      await deleteMutation.mutateAsync(prefId);
      toast.success('Preference deleted');
    } catch {
      toast.error('Failed to delete preference');
    }
  };

  const handleSave = async (data: ServicePreferenceCreate) => {
    try {
      if (editing) {
        await updateMutation.mutateAsync({ preferenceId: editing.id, data });
        toast.success('Preference updated');
      } else {
        await addMutation.mutateAsync(data);
        toast.success('Preference added');
      }
      setModalOpen(false);
    } catch {
      toast.error('Failed to save preference');
    }
  };

  return (
    <>
      <Card data-testid="service-preferences-section">
        <CardHeader className="border-b border-slate-100">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-lg font-bold text-slate-800">
              <Clock className="h-5 w-5 text-teal-500" />
              Service Preferences
            </CardTitle>
            <Button
              variant="outline"
              size="sm"
              onClick={handleAdd}
              data-testid="add-preference-btn"
              className="text-teal-600 border-teal-200 hover:bg-teal-50"
            >
              <Plus className="mr-1 h-4 w-4" />
              Add
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-4">
          {isLoading ? (
            <p className="text-sm text-slate-400">Loading...</p>
          ) : preferences.length === 0 ? (
            <p className="text-sm text-slate-400 italic" data-testid="no-preferences">
              No service preferences configured
            </p>
          ) : (
            <div className="space-y-3">
              {preferences.map((pref) => (
                <div
                  key={pref.id}
                  className="flex items-start justify-between rounded-lg border border-slate-100 p-3"
                  data-testid={`preference-${pref.id}`}
                >
                  <div className="space-y-1">
                    <p className="text-sm font-medium text-slate-700">
                      {SERVICE_TYPE_LABELS[pref.service_type] || pref.service_type}
                    </p>
                    <div className="flex flex-wrap gap-2 text-xs text-slate-500">
                      {pref.preferred_week && <span>Week of {pref.preferred_week}</span>}
                      {pref.preferred_date && <span>Date: {pref.preferred_date}</span>}
                      <span>{TIME_WINDOW_LABELS[pref.time_window] || pref.time_window}</span>
                    </div>
                    {pref.notes && (
                      <p className="text-xs text-slate-400 mt-1">{pref.notes}</p>
                    )}
                  </div>
                  <div className="flex gap-1 shrink-0">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleEdit(pref)}
                      data-testid={`edit-preference-${pref.id}`}
                    >
                      <Edit className="h-3.5 w-3.5" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDelete(pref.id)}
                      disabled={deleteMutation.isPending}
                      data-testid={`delete-preference-${pref.id}`}
                    >
                      <Trash2 className="h-3.5 w-3.5 text-red-500" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <ServicePreferenceModal
        open={modalOpen}
        onOpenChange={setModalOpen}
        onSave={handleSave}
        preference={editing}
        isPending={addMutation.isPending || updateMutation.isPending}
      />
    </>
  );
}
