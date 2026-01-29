/**
 * Tests for Appointment API client.
 * Requirements: All appointment API requirements
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { appointmentApi } from './appointmentApi';
import { apiClient } from '@/core/api/client';

// Mock the API client
vi.mock('@/core/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

const mockAppointment = {
  id: 'appt-123',
  job_id: 'job-123',
  staff_id: 'staff-123',
  scheduled_date: '2025-01-29',
  time_window_start: '09:00',
  time_window_end: '11:00',
  status: 'scheduled',
  created_at: '2025-01-29T00:00:00Z',
};

describe('appointmentApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('list', () => {
    it('fetches appointments without params', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: { items: [mockAppointment], total: 1, page: 1, page_size: 20 },
      });

      const result = await appointmentApi.list();

      expect(apiClient.get).toHaveBeenCalledWith('/appointments', { params: undefined });
      expect(result.items).toHaveLength(1);
    });

    it('fetches appointments with params', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: { items: [mockAppointment], total: 1, page: 1, page_size: 20 },
      });

      const params = { scheduled_date: '2025-01-29', staff_id: 'staff-123' };
      await appointmentApi.list(params);

      expect(apiClient.get).toHaveBeenCalledWith('/appointments', { params });
    });
  });

  describe('getById', () => {
    it('fetches single appointment by ID', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockAppointment });

      const result = await appointmentApi.getById('appt-123');

      expect(apiClient.get).toHaveBeenCalledWith('/appointments/appt-123');
      expect(result.id).toBe('appt-123');
    });
  });

  describe('create', () => {
    it('creates new appointment', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({ data: mockAppointment });

      const data = {
        job_id: 'job-123',
        staff_id: 'staff-123',
        scheduled_date: '2025-01-29',
        time_window_start: '09:00',
        time_window_end: '11:00',
      };
      const result = await appointmentApi.create(data);

      expect(apiClient.post).toHaveBeenCalledWith('/appointments', data);
      expect(result.id).toBe('appt-123');
    });
  });

  describe('update', () => {
    it('updates existing appointment', async () => {
      vi.mocked(apiClient.put).mockResolvedValue({ data: mockAppointment });

      const data = { time_window_start: '10:00' };
      const result = await appointmentApi.update('appt-123', data);

      expect(apiClient.put).toHaveBeenCalledWith('/appointments/appt-123', data);
      expect(result.id).toBe('appt-123');
    });
  });

  describe('cancel', () => {
    it('cancels appointment', async () => {
      vi.mocked(apiClient.delete).mockResolvedValue({});

      await appointmentApi.cancel('appt-123');

      expect(apiClient.delete).toHaveBeenCalledWith('/appointments/appt-123');
    });
  });

  describe('getDailySchedule', () => {
    it('fetches daily schedule', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: { date: '2025-01-29', appointments: [mockAppointment] },
      });

      const result = await appointmentApi.getDailySchedule('2025-01-29');

      expect(apiClient.get).toHaveBeenCalledWith('/appointments/daily/2025-01-29');
      expect(result.date).toBe('2025-01-29');
    });
  });

  describe('getStaffDailySchedule', () => {
    it('fetches staff daily schedule', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: { staff_id: 'staff-123', date: '2025-01-29', appointments: [mockAppointment] },
      });

      const result = await appointmentApi.getStaffDailySchedule('staff-123', '2025-01-29');

      expect(apiClient.get).toHaveBeenCalledWith('/appointments/staff/staff-123/daily/2025-01-29');
      expect(result.staff_id).toBe('staff-123');
    });
  });

  describe('getWeeklySchedule', () => {
    it('fetches weekly schedule without dates', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: { start_date: '2025-01-27', end_date: '2025-02-02', days: [] },
      });

      await appointmentApi.getWeeklySchedule();

      expect(apiClient.get).toHaveBeenCalledWith('/appointments/weekly', { params: {} });
    });

    it('fetches weekly schedule with dates', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: { start_date: '2025-01-27', end_date: '2025-02-02', days: [] },
      });

      await appointmentApi.getWeeklySchedule('2025-01-27', '2025-02-02');

      expect(apiClient.get).toHaveBeenCalledWith('/appointments/weekly', {
        params: { start_date: '2025-01-27', end_date: '2025-02-02' },
      });
    });
  });

  describe('confirm', () => {
    it('confirms appointment', async () => {
      const confirmedAppt = { ...mockAppointment, status: 'confirmed' };
      vi.mocked(apiClient.put).mockResolvedValue({ data: confirmedAppt });

      const result = await appointmentApi.confirm('appt-123');

      expect(apiClient.put).toHaveBeenCalledWith('/appointments/appt-123', { status: 'confirmed' });
      expect(result.status).toBe('confirmed');
    });
  });

  describe('markArrived', () => {
    it('marks appointment as arrived', async () => {
      const arrivedAppt = { ...mockAppointment, status: 'in_progress' };
      vi.mocked(apiClient.put).mockResolvedValue({ data: arrivedAppt });

      const result = await appointmentApi.markArrived('appt-123');

      expect(apiClient.put).toHaveBeenCalledWith('/appointments/appt-123', { status: 'in_progress' });
      expect(result.status).toBe('in_progress');
    });
  });

  describe('markCompleted', () => {
    it('marks appointment as completed', async () => {
      const completedAppt = { ...mockAppointment, status: 'completed' };
      vi.mocked(apiClient.put).mockResolvedValue({ data: completedAppt });

      const result = await appointmentApi.markCompleted('appt-123');

      expect(apiClient.put).toHaveBeenCalledWith('/appointments/appt-123', { status: 'completed' });
      expect(result.status).toBe('completed');
    });
  });

  describe('markNoShow', () => {
    it('marks appointment as no show', async () => {
      const noShowAppt = { ...mockAppointment, status: 'no_show' };
      vi.mocked(apiClient.put).mockResolvedValue({ data: noShowAppt });

      const result = await appointmentApi.markNoShow('appt-123');

      expect(apiClient.put).toHaveBeenCalledWith('/appointments/appt-123', { status: 'no_show' });
      expect(result.status).toBe('no_show');
    });
  });
});
