/**
 * Main schedule page component.
 * Displays calendar view with appointments.
 */

import { useState } from 'react';
import { format } from 'date-fns';
import { PageHeader } from '@/shared/components/PageHeader';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Plus, Calendar, List } from 'lucide-react';
import { CalendarView } from './CalendarView';
import { AppointmentForm } from './AppointmentForm';
import { AppointmentDetail } from './AppointmentDetail';
import { AppointmentList } from './AppointmentList';

type ViewMode = 'calendar' | 'list';

export function SchedulePage() {
  const [viewMode, setViewMode] = useState<ViewMode>('calendar');
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [selectedAppointmentId, setSelectedAppointmentId] = useState<
    string | null
  >(null);
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);

  const handleDateClick = (date: Date) => {
    setSelectedDate(date);
    setShowCreateDialog(true);
  };

  const handleEventClick = (appointmentId: string) => {
    setSelectedAppointmentId(appointmentId);
  };

  const handleCreateSuccess = () => {
    setShowCreateDialog(false);
    setSelectedDate(null);
  };

  const handleCloseDetail = () => {
    setSelectedAppointmentId(null);
  };

  return (
    <div data-testid="schedule-page" className="space-y-6">
      <PageHeader
        title="Schedule"
        description="Manage appointments and view daily/weekly schedules"
        action={
          <div className="flex items-center gap-4">
            <Tabs
              value={viewMode}
              onValueChange={(v) => setViewMode(v as ViewMode)}
            >
              <TabsList>
                <TabsTrigger value="calendar" data-testid="calendar-view-tab">
                  <Calendar className="mr-2 h-4 w-4" />
                  Calendar
                </TabsTrigger>
                <TabsTrigger value="list" data-testid="list-view-tab">
                  <List className="mr-2 h-4 w-4" />
                  List
                </TabsTrigger>
              </TabsList>
            </Tabs>
            <Button
              onClick={() => setShowCreateDialog(true)}
              data-testid="add-appointment-btn"
            >
              <Plus className="mr-2 h-4 w-4" />
              New Appointment
            </Button>
          </div>
        }
      />

      {/* Main Content */}
      <div className="bg-white rounded-lg border shadow-sm">
        {viewMode === 'calendar' ? (
          <CalendarView
            onDateClick={handleDateClick}
            onEventClick={handleEventClick}
          />
        ) : (
          <AppointmentList
            onAppointmentClick={(id) => setSelectedAppointmentId(id)}
          />
        )}
      </div>

      {/* Create Appointment Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="max-w-lg" aria-describedby="create-appointment-description">
          <DialogHeader>
            <DialogTitle>
              {selectedDate
                ? `Schedule Appointment for ${format(selectedDate, 'MMMM d, yyyy')}`
                : 'Schedule New Appointment'}
            </DialogTitle>
            <p id="create-appointment-description" className="text-sm text-muted-foreground">
              Fill in the details below to schedule a new appointment.
            </p>
          </DialogHeader>
          <AppointmentForm
            initialDate={selectedDate ?? undefined}
            onSuccess={handleCreateSuccess}
            onCancel={() => {
              setShowCreateDialog(false);
              setSelectedDate(null);
            }}
          />
        </DialogContent>
      </Dialog>

      {/* Appointment Detail Dialog */}
      <Dialog
        open={!!selectedAppointmentId}
        onOpenChange={() => handleCloseDetail()}
      >
        <DialogContent className="max-w-2xl" aria-describedby="appointment-detail-description">
          <DialogHeader>
            <DialogTitle>Appointment Details</DialogTitle>
            <p id="appointment-detail-description" className="text-sm text-muted-foreground">
              View and manage appointment information.
            </p>
          </DialogHeader>
          {selectedAppointmentId && (
            <AppointmentDetail
              appointmentId={selectedAppointmentId}
              onClose={handleCloseDetail}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
