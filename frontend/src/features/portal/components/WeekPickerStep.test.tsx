import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { WeekPickerStep, mapServicesToPickerList, SERVICE_MONTH_RANGES } from './WeekPickerStep';

/* ------------------------------------------------------------------ */
/* mapServicesToPickerList — tier mapping tests                        */
/* ------------------------------------------------------------------ */

describe('mapServicesToPickerList', () => {
  const essentialServices = [
    { service_type: 'spring_startup', description: 'Spring system activation and inspection' },
    { service_type: 'fall_winterization', description: 'Fall system winterization and blowout' },
  ];

  const professionalServices = [
    essentialServices[0],
    { service_type: 'mid_season_inspection', description: 'Mid-season system inspection and adjustment' },
    essentialServices[1],
  ];

  const premiumServices = [
    essentialServices[0],
    { service_type: 'monthly_visit', description: 'Monthly system check and adjustment (May-Sep)' },
    essentialServices[1],
  ];

  /**
   * Validates: Requirements 13.2
   */
  it('Essential tier maps to exactly 2 pickers (spring startup, fall winterization)', () => {
    const result = mapServicesToPickerList(essentialServices);
    expect(result).toHaveLength(2);
    expect(result.map((s) => s.jobType)).toEqual(['spring_startup', 'fall_winterization']);
  });

  /**
   * Validates: Requirements 13.2
   */
  it('Professional tier maps to exactly 3 pickers (+ mid-season inspection)', () => {
    const result = mapServicesToPickerList(professionalServices);
    expect(result).toHaveLength(3);
    expect(result.map((s) => s.jobType)).toEqual([
      'spring_startup',
      'mid_season_inspection',
      'fall_winterization',
    ]);
  });

  /**
   * Validates: Requirements 13.2
   */
  it('Premium tier maps to exactly 7 pickers (+ monthly visits May-Sep)', () => {
    const result = mapServicesToPickerList(premiumServices);
    expect(result).toHaveLength(7);
    expect(result.map((s) => s.jobType)).toEqual([
      'spring_startup',
      'monthly_visit_5',
      'monthly_visit_6',
      'monthly_visit_7',
      'monthly_visit_8',
      'monthly_visit_9',
      'fall_winterization',
    ]);
  });

  /**
   * Validates: Requirements 13.7
   */
  it('no service appears twice in any tier', () => {
    for (const services of [essentialServices, professionalServices, premiumServices]) {
      const result = mapServicesToPickerList(services);
      const jobTypes = result.map((s) => s.jobType);
      expect(new Set(jobTypes).size).toBe(jobTypes.length);
    }
  });

  /**
   * Validates: Requirements 13.7
   */
  it('lower tiers do not get extra pickers from higher tiers', () => {
    const essential = mapServicesToPickerList(essentialServices);
    const professional = mapServicesToPickerList(professionalServices);

    // Essential should NOT have mid_season_inspection or monthly visits
    const essentialTypes = essential.map((s) => s.jobType);
    expect(essentialTypes).not.toContain('mid_season_inspection');
    expect(essentialTypes).not.toContain('monthly_visit_5');

    // Professional should NOT have monthly visits
    const proTypes = professional.map((s) => s.jobType);
    expect(proTypes).not.toContain('monthly_visit_5');
    expect(proTypes).not.toContain('monthly_visit_6');
  });

  it('ignores unknown service types not in SERVICE_MONTH_RANGES', () => {
    const services = [
      { service_type: 'spring_startup' },
      { service_type: 'unknown_service' },
      { service_type: 'fall_winterization' },
    ];
    const result = mapServicesToPickerList(services);
    expect(result).toHaveLength(2);
    expect(result.map((s) => s.jobType)).toEqual(['spring_startup', 'fall_winterization']);
  });

  it('deduplicates if same service_type appears multiple times', () => {
    const services = [
      { service_type: 'spring_startup' },
      { service_type: 'spring_startup' },
      { service_type: 'fall_winterization' },
    ];
    const result = mapServicesToPickerList(services);
    expect(result).toHaveLength(2);
  });
});


/* ------------------------------------------------------------------ */
/* SERVICE_MONTH_RANGES — month restriction tests                     */
/* ------------------------------------------------------------------ */

describe('SERVICE_MONTH_RANGES', () => {
  it('spring_startup is restricted to March-May', () => {
    const range = SERVICE_MONTH_RANGES['spring_startup'];
    expect(range.monthStart).toBe(3);
    expect(range.monthEnd).toBe(5);
  });

  it('mid_season_inspection is restricted to June-August', () => {
    const range = SERVICE_MONTH_RANGES['mid_season_inspection'];
    expect(range.monthStart).toBe(6);
    expect(range.monthEnd).toBe(8);
  });

  it('fall_winterization is restricted to September-November', () => {
    const range = SERVICE_MONTH_RANGES['fall_winterization'];
    expect(range.monthStart).toBe(9);
    expect(range.monthEnd).toBe(11);
  });

  it('monthly visits are restricted to their specific month', () => {
    for (let month = 5; month <= 9; month++) {
      const range = SERVICE_MONTH_RANGES[`monthly_visit_${month}`];
      expect(range.monthStart).toBe(month);
      expect(range.monthEnd).toBe(month);
    }
  });
});

/* ------------------------------------------------------------------ */
/* WeekPickerStep component — rendering and "No preference" tests     */
/* ------------------------------------------------------------------ */

describe('WeekPickerStep', () => {
  const essentialServices = [
    { jobType: 'spring_startup', label: 'Spring Startup' },
    { jobType: 'fall_winterization', label: 'Fall Winterization' },
  ];

  const premiumServices = [
    { jobType: 'spring_startup', label: 'Spring Startup' },
    { jobType: 'monthly_visit_5', label: 'Monthly Visit — May' },
    { jobType: 'monthly_visit_6', label: 'Monthly Visit — June' },
    { jobType: 'monthly_visit_7', label: 'Monthly Visit — July' },
    { jobType: 'monthly_visit_8', label: 'Monthly Visit — August' },
    { jobType: 'monthly_visit_9', label: 'Monthly Visit — September' },
    { jobType: 'fall_winterization', label: 'Fall Winterization' },
  ];

  it('renders correct number of pickers for Essential tier', () => {
    render(
      <WeekPickerStep services={essentialServices} value={{}} onChange={vi.fn()} />,
    );
    const rows = screen.getAllByTestId(/^picker-row-/);
    expect(rows).toHaveLength(2);
  });

  it('renders correct number of pickers for Premium tier', () => {
    render(
      <WeekPickerStep services={premiumServices} value={{}} onChange={vi.fn()} />,
    );
    const rows = screen.getAllByTestId(/^picker-row-/);
    expect(rows).toHaveLength(7);
  });

  it('shows "No preference" button for each picker', () => {
    render(
      <WeekPickerStep services={essentialServices} value={{}} onChange={vi.fn()} />,
    );
    const noPrefBtns = screen.getAllByTestId(/^no-pref-btn-/);
    expect(noPrefBtns).toHaveLength(2);
    expect(noPrefBtns[0]).toHaveTextContent('No preference');
  });

  it('clicking "No preference" shows "Assign for me" label and removes selection', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <WeekPickerStep
        services={essentialServices}
        value={{ spring_startup: '2026-04-06' }}
        onChange={onChange}
      />,
    );

    const noPrefBtn = screen.getByTestId('no-pref-btn-spring_startup');
    await user.click(noPrefBtn);

    // onChange should be called with spring_startup removed
    expect(onChange).toHaveBeenCalledWith({});
    // The label should now show "Assign for me"
    expect(screen.getByTestId('no-pref-label-spring_startup')).toHaveTextContent('Assign for me');
  });

  it('clicking "Pick a week" after "No preference" restores the picker', async () => {
    const user = userEvent.setup();
    render(
      <WeekPickerStep services={essentialServices} value={{}} onChange={vi.fn()} />,
    );

    // Click "No preference" first
    const noPrefBtn = screen.getByTestId('no-pref-btn-spring_startup');
    await user.click(noPrefBtn);
    expect(screen.getByTestId('no-pref-label-spring_startup')).toBeInTheDocument();

    // Now click "Pick a week" to restore
    const pickBtn = screen.getByTestId('no-pref-btn-spring_startup');
    expect(pickBtn).toHaveTextContent('Pick a week');
    await user.click(pickBtn);

    // Picker should be back
    expect(screen.getByTestId('week-picker-spring_startup')).toBeInTheDocument();
  });

  it('displays service labels correctly', () => {
    render(
      <WeekPickerStep services={essentialServices} value={{}} onChange={vi.fn()} />,
    );
    expect(screen.getByText('Spring Startup')).toBeInTheDocument();
    expect(screen.getByText('Fall Winterization')).toBeInTheDocument();
  });
});
