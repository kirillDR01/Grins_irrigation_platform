import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { CapacityHeatMap } from './CapacityHeatMap';
import type { CapacityDay } from './CapacityHeatMap';

const days: CapacityDay[] = [
  { date: '2026-02-16', label: 'Mon 2/16', utilization: 95 },
  { date: '2026-02-17', label: 'Tue 2/17', utilization: 75 },
  { date: '2026-02-18', label: 'Wed 2/18', utilization: 40 },
];

describe('CapacityHeatMap', () => {
  it('renders with data-testid="capacity-heat-map"', () => {
    render(<CapacityHeatMap days={days} />);
    expect(screen.getByTestId('capacity-heat-map')).toBeInTheDocument();
  });

  it('renders a cell for each day with correct data-testid', () => {
    render(<CapacityHeatMap days={days} />);
    expect(screen.getByTestId('capacity-cell-2026-02-16')).toBeInTheDocument();
    expect(screen.getByTestId('capacity-cell-2026-02-17')).toBeInTheDocument();
    expect(screen.getByTestId('capacity-cell-2026-02-18')).toBeInTheDocument();
  });

  it('displays utilization percentages', () => {
    render(<CapacityHeatMap days={days} />);
    expect(screen.getByTestId('capacity-cell-2026-02-16')).toHaveTextContent('95%');
    expect(screen.getByTestId('capacity-cell-2026-02-17')).toHaveTextContent('75%');
    expect(screen.getByTestId('capacity-cell-2026-02-18')).toHaveTextContent('40%');
  });

  it('applies red color class for >90% utilization', () => {
    render(<CapacityHeatMap days={days} />);
    const cell = screen.getByTestId('capacity-cell-2026-02-16');
    expect(cell.className).toContain('bg-red-100');
  });

  it('applies green color class for 60–90% utilization', () => {
    render(<CapacityHeatMap days={days} />);
    const cell = screen.getByTestId('capacity-cell-2026-02-17');
    expect(cell.className).toContain('bg-green-100');
  });

  it('applies yellow color class for <60% utilization', () => {
    render(<CapacityHeatMap days={days} />);
    const cell = screen.getByTestId('capacity-cell-2026-02-18');
    expect(cell.className).toContain('bg-yellow-100');
  });

  it('renders empty when no days provided', () => {
    render(<CapacityHeatMap days={[]} />);
    expect(screen.getByTestId('capacity-heat-map')).toBeInTheDocument();
    expect(screen.queryByTestId(/capacity-cell-/)).toBeNull();
  });
});
