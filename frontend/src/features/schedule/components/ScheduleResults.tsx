/**
 * Schedule Results component.
 * Displays generated schedule assignments grouped by staff.
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import { CheckCircle, MapPin, AlertTriangle, Calendar, Loader2 } from 'lucide-react';
import { ScheduleExplanationModal } from './ScheduleExplanationModal';
import { UnassignedJobExplanationCard } from './UnassignedJobExplanationCard';
import { useApplySchedule } from '../hooks/useApplySchedule';
import type { ScheduleGenerateResponse } from '../types';

interface ScheduleResultsProps {
  results: ScheduleGenerateResponse;
  scheduleDate: string;
}

export function ScheduleResults({ results, scheduleDate }: ScheduleResultsProps) {
  const [isApplied, setIsApplied] = useState(false);
  const navigate = useNavigate();
  const applyMutation = useApplySchedule();

  // Format the date for display
  const formattedDate = new Date(scheduleDate + 'T00:00:00').toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });

  const handleApplySchedule = async () => {
    try {
      const response = await applyMutation.mutateAsync({
        schedule_date: scheduleDate,
        assignments: results.assignments,
      });

      if (response.success) {
        setIsApplied(true);
        toast.success('Schedule Applied', {
          description: `Created ${response.appointments_created} appointments for ${formattedDate}`,
        });
      }
    } catch (error) {
      toast.error('Failed to Apply Schedule', {
        description: error instanceof Error ? error.message : 'Unknown error occurred',
      });
    }
  };

  const handleViewSchedule = () => {
    navigate('/schedule');
  };

  return (
    <div className="space-y-8" data-testid="schedule-results">
      {/* Summary Card */}
      <Card className="bg-white rounded-2xl shadow-sm border border-slate-100">
        <CardHeader className="p-6 border-b border-slate-100">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2 text-lg font-bold text-slate-800">
                <CheckCircle className="h-5 w-5 text-emerald-500" />
                Schedule Completed for {formattedDate}
              </CardTitle>
              <CardDescription className="text-slate-500 mt-1">
                {results.total_assigned} jobs assigned
                {results.unassigned_jobs.length > 0 &&
                  `, ${results.unassigned_jobs.length} could not fit in today's schedule`}
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <ScheduleExplanationModal results={results} scheduleDate={scheduleDate} />
              {isApplied ? (
                <Button
                  variant="outline"
                  onClick={handleViewSchedule}
                  data-testid="view-schedule-btn"
                >
                  <Calendar className="h-4 w-4 mr-2" />
                  View Schedule
                </Button>
              ) : (
                <Button
                  onClick={handleApplySchedule}
                  disabled={applyMutation.isPending || results.total_assigned === 0}
                  data-testid="apply-schedule-btn"
                >
                  {applyMutation.isPending ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Applying...
                    </>
                  ) : (
                    <>
                      <Calendar className="h-4 w-4 mr-2" />
                      Apply Schedule
                    </>
                  )}
                </Button>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-6">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div className="text-center">
              <div
                className="text-3xl font-bold text-emerald-600"
                data-testid="total-assigned"
              >
                {results.total_assigned}
              </div>
              <div className="text-sm text-slate-500">Assigned</div>
            </div>
            <div className="text-center">
              <div
                className="text-3xl font-bold text-red-600"
                data-testid="total-unassigned"
              >
                {results.unassigned_jobs.length}
              </div>
              <div className="text-sm text-slate-500">Unassigned</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-slate-800" data-testid="total-travel">
                {results.total_travel_minutes}m
              </div>
              <div className="text-sm text-slate-500">Travel Time</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-slate-800" data-testid="generation-time">
                {results.optimization_time_seconds.toFixed(2)}s
              </div>
              <div className="text-sm text-slate-500">Gen Time</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-slate-800">{results.assignments.length}</div>
              <div className="text-sm text-slate-500">Staff Used</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Staff Assignments */}
      {results.assignments.length > 0 && (
        <Card className="bg-white rounded-2xl shadow-sm border border-slate-100">
          <CardHeader className="p-6 border-b border-slate-100">
            <CardTitle className="text-lg font-bold text-slate-800">Staff Assignments</CardTitle>
            <CardDescription className="text-slate-500">
              Route assignments grouped by staff member
            </CardDescription>
          </CardHeader>
          <CardContent className="p-6">
            <Accordion type="multiple" className="w-full">
              {results.assignments.map((staffAssignment) => (
                <AccordionItem
                  key={staffAssignment.staff_id}
                  value={staffAssignment.staff_id}
                  data-testid={`staff-group-${staffAssignment.staff_id}`}
                  className="border-b border-slate-100 last:border-0"
                >
                  <AccordionTrigger className="hover:no-underline py-4">
                    <div className="flex items-center justify-between w-full pr-4">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-teal-100 text-teal-700 flex items-center justify-center font-semibold text-sm">
                          {staffAssignment.staff_name.split(' ').map(n => n[0]).join('')}
                        </div>
                        <span className="font-semibold text-slate-800">{staffAssignment.staff_name}</span>
                      </div>
                      <div className="flex items-center gap-4 text-sm text-slate-500">
                        <span className="font-medium">{staffAssignment.total_jobs} jobs</span>
                        <span className="flex items-center gap-1">
                          <MapPin className="h-3 w-3" />
                          {staffAssignment.total_travel_minutes}m travel
                        </span>
                      </div>
                    </div>
                  </AccordionTrigger>
                  <AccordionContent className="pt-4">
                    <div className="bg-slate-50 rounded-xl overflow-hidden">
                      <Table>
                        <TableHeader>
                          <TableRow className="bg-slate-50/50 hover:bg-slate-50/50">
                            <TableHead className="w-12 text-slate-500 text-xs uppercase tracking-wider font-medium">#</TableHead>
                            <TableHead className="text-slate-500 text-xs uppercase tracking-wider font-medium">Time</TableHead>
                            <TableHead className="text-slate-500 text-xs uppercase tracking-wider font-medium">Customer</TableHead>
                            <TableHead className="text-slate-500 text-xs uppercase tracking-wider font-medium">Location</TableHead>
                            <TableHead className="text-slate-500 text-xs uppercase tracking-wider font-medium">Service</TableHead>
                            <TableHead className="text-right text-slate-500 text-xs uppercase tracking-wider font-medium">Duration</TableHead>
                            <TableHead className="text-right text-slate-500 text-xs uppercase tracking-wider font-medium">Travel</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {staffAssignment.jobs
                            .sort((a, b) => a.sequence_index - b.sequence_index)
                            .map((job) => (
                              <TableRow
                                key={job.job_id}
                                data-testid={`assignment-${job.job_id}`}
                                className="hover:bg-white/80 transition-colors"
                              >
                                <TableCell className="font-semibold text-slate-700">
                                  {job.sequence_index + 1}
                                </TableCell>
                                <TableCell className="text-sm text-slate-600">
                                  {job.start_time.slice(0, 5)} - {job.end_time.slice(0, 5)}
                                </TableCell>
                                <TableCell className="font-medium text-slate-700">{job.customer_name}</TableCell>
                                <TableCell>
                                  <div className="text-sm text-slate-600">{job.address || 'N/A'}</div>
                                  <div className="text-xs text-slate-400">
                                    {job.city || ''}
                                  </div>
                                </TableCell>
                                <TableCell>
                                  <Badge variant="outline" className="bg-teal-50 text-teal-600 border-teal-100">{job.service_type}</Badge>
                                </TableCell>
                                <TableCell className="text-right text-sm text-slate-600">
                                  {job.duration_minutes}m
                                </TableCell>
                                <TableCell className="text-right text-sm text-slate-600">
                                  {job.travel_time_minutes}m
                                </TableCell>
                              </TableRow>
                            ))}
                        </TableBody>
                      </Table>
                    </div>
                  </AccordionContent>
                </AccordionItem>
              ))}
            </Accordion>
          </CardContent>
        </Card>
      )}

      {/* Unassigned Jobs */}
      {results.unassigned_jobs.length > 0 && (
        <Card className="bg-amber-50 rounded-2xl shadow-sm border border-amber-100" data-testid="unassigned-jobs-section">
          <CardHeader className="p-6 border-b border-amber-100">
            <CardTitle className="flex items-center gap-2 text-lg font-bold text-amber-800">
              <AlertTriangle className="h-5 w-5" />
              Unassigned Jobs ({results.unassigned_jobs.length})
            </CardTitle>
            <CardDescription className="text-amber-700">
              These jobs could not be scheduled. Click "Why?" for detailed explanations.
            </CardDescription>
          </CardHeader>
          <CardContent className="p-6">
            <div className="bg-white rounded-xl overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow className="bg-slate-50/50 hover:bg-slate-50/50">
                    <TableHead className="text-slate-500 text-xs uppercase tracking-wider font-medium">Customer</TableHead>
                    <TableHead className="text-slate-500 text-xs uppercase tracking-wider font-medium">Service Type</TableHead>
                    <TableHead className="text-slate-500 text-xs uppercase tracking-wider font-medium">Reason</TableHead>
                    <TableHead className="w-24 text-slate-500 text-xs uppercase tracking-wider font-medium">Details</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {results.unassigned_jobs.map((job) => (
                    <TableRow
                      key={job.job_id}
                      data-testid={`unassigned-${job.job_id}`}
                      className="hover:bg-slate-50/80 transition-colors"
                    >
                      <TableCell className="font-medium text-slate-700">{job.customer_name}</TableCell>
                      <TableCell>
                        <Badge variant="outline" className="bg-amber-50 text-amber-600 border-amber-100">{job.service_type}</Badge>
                      </TableCell>
                      <TableCell className="text-sm text-amber-800">{job.reason}</TableCell>
                      <TableCell>
                        <UnassignedJobExplanationCard job={job} />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
