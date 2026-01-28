/**
 * Schedule Results component.
 * Displays generated schedule assignments grouped by staff.
 */

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
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
import { CheckCircle, XCircle, MapPin, AlertTriangle } from 'lucide-react';
import { ScheduleExplanationModal } from './ScheduleExplanationModal';
import { UnassignedJobExplanationCard } from './UnassignedJobExplanationCard';
import type { ScheduleGenerateResponse } from '../types';

interface ScheduleResultsProps {
  results: ScheduleGenerateResponse;
  scheduleDate: string;
}

export function ScheduleResults({ results, scheduleDate }: ScheduleResultsProps) {
  return (
    <div className="space-y-6" data-testid="schedule-results">
      {/* Summary Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                {results.is_feasible ? (
                  <CheckCircle className="h-5 w-5 text-green-600" />
                ) : (
                  <XCircle className="h-5 w-5 text-red-600" />
                )}
                Schedule {results.is_feasible ? 'Generated' : 'Incomplete'}
              </CardTitle>
              <CardDescription>
                {results.is_feasible
                  ? 'All jobs successfully assigned'
                  : 'Some jobs could not be assigned'}
              </CardDescription>
            </div>
            <ScheduleExplanationModal results={results} scheduleDate={scheduleDate} />
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div className="text-center">
              <div
                className="text-2xl font-bold text-green-600"
                data-testid="total-assigned"
              >
                {results.total_assigned}
              </div>
              <div className="text-sm text-muted-foreground">Assigned</div>
            </div>
            <div className="text-center">
              <div
                className="text-2xl font-bold text-red-600"
                data-testid="total-unassigned"
              >
                {results.unassigned_jobs.length}
              </div>
              <div className="text-sm text-muted-foreground">Unassigned</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold" data-testid="total-travel">
                {results.total_travel_minutes}m
              </div>
              <div className="text-sm text-muted-foreground">Travel Time</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold" data-testid="generation-time">
                {results.optimization_time_seconds.toFixed(2)}s
              </div>
              <div className="text-sm text-muted-foreground">Gen Time</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold">{results.assignments.length}</div>
              <div className="text-sm text-muted-foreground">Staff Used</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Staff Assignments */}
      {results.assignments.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Staff Assignments</CardTitle>
            <CardDescription>
              Route assignments grouped by staff member
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Accordion type="multiple" className="w-full">
              {results.assignments.map((staffAssignment) => (
                <AccordionItem
                  key={staffAssignment.staff_id}
                  value={staffAssignment.staff_id}
                  data-testid={`staff-group-${staffAssignment.staff_id}`}
                >
                  <AccordionTrigger className="hover:no-underline">
                    <div className="flex items-center justify-between w-full pr-4">
                      <span className="font-medium">{staffAssignment.staff_name}</span>
                      <div className="flex items-center gap-4 text-sm text-muted-foreground">
                        <span>{staffAssignment.total_jobs} jobs</span>
                        <span className="flex items-center gap-1">
                          <MapPin className="h-3 w-3" />
                          {staffAssignment.total_travel_minutes}m travel
                        </span>
                      </div>
                    </div>
                  </AccordionTrigger>
                  <AccordionContent>
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead className="w-12">#</TableHead>
                          <TableHead>Time</TableHead>
                          <TableHead>Customer</TableHead>
                          <TableHead>Location</TableHead>
                          <TableHead>Service</TableHead>
                          <TableHead className="text-right">Duration</TableHead>
                          <TableHead className="text-right">Travel</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {staffAssignment.jobs
                          .sort((a, b) => a.sequence_index - b.sequence_index)
                          .map((job) => (
                            <TableRow
                              key={job.job_id}
                              data-testid={`assignment-${job.job_id}`}
                            >
                              <TableCell className="font-medium">
                                {job.sequence_index + 1}
                              </TableCell>
                              <TableCell>
                                {job.start_time.slice(0, 5)} - {job.end_time.slice(0, 5)}
                              </TableCell>
                              <TableCell>{job.customer_name}</TableCell>
                              <TableCell>
                                <div>{job.address || 'N/A'}</div>
                                <div className="text-xs text-muted-foreground">
                                  {job.city || ''}
                                </div>
                              </TableCell>
                              <TableCell>
                                <Badge variant="outline">{job.service_type}</Badge>
                              </TableCell>
                              <TableCell className="text-right">
                                {job.duration_minutes}m
                              </TableCell>
                              <TableCell className="text-right">
                                {job.travel_time_minutes}m
                              </TableCell>
                            </TableRow>
                          ))}
                      </TableBody>
                    </Table>
                  </AccordionContent>
                </AccordionItem>
              ))}
            </Accordion>
          </CardContent>
        </Card>
      )}

      {/* Unassigned Jobs */}
      {results.unassigned_jobs.length > 0 && (
        <Card className="border-yellow-200" data-testid="unassigned-jobs-section">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-yellow-800">
              <AlertTriangle className="h-5 w-5" />
              Unassigned Jobs
            </CardTitle>
            <CardDescription>
              These jobs could not be scheduled. Click "Why?" for detailed explanations.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Customer</TableHead>
                  <TableHead>Service Type</TableHead>
                  <TableHead>Reason</TableHead>
                  <TableHead className="w-24">Details</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {results.unassigned_jobs.map((job) => (
                  <TableRow
                    key={job.job_id}
                    data-testid={`unassigned-${job.job_id}`}
                  >
                    <TableCell>{job.customer_name}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{job.service_type}</Badge>
                    </TableCell>
                    <TableCell className="text-yellow-800">{job.reason}</TableCell>
                    <TableCell>
                      <UnassignedJobExplanationCard
                        job={job}
                        scheduleDate={scheduleDate}
                        availableStaff={results.assignments.map((a) => a.staff_name)}
                      />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
