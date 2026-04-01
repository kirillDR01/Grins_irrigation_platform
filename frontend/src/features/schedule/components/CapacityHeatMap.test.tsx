/**
 * Tests for CapacityHeatMap component.
 * Validates: Requirements 30.6, 30.7, 30.8
 */

import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { CapacityHeatMap, type CapacityHeatMapData } from './CapacityHeatMap';

const sampleData: CapacityHeatMapData[] = [
  { day: 'mon', utilization: 95 },
  { day: 'tue', utilization: 75 },
  { day: 'wed', utilization: 45 },
  { day: 'thu', utilization: 60 },
  { day: 'fri', utilization: 91 },
];

describe('CapacityHeatMap', () => {
  it('renders with data-testid', () => {
    render(<CapacityHeatMap data={sampleData} />);
    expect(screen.getByTestId('capacity-heat-map')).toBeInTheDocument();
  });

  it('renders a cell for each day', () => {
    render(<CapacityHeatMap data={sampleData} />);
    for (const item of sampleData) {
      expect(screen.getByTestId(`capacity-cell-${item.day}`)).toBeInTheDocument();
    }
  });

  it('displays utilization percentages', () => {
    render(<CapacityHeatMap data={sampleData} />);
    expect(screen.getByTestId('capacity-cell-mon')).toHaveTextContent('95%');
    expect(screen.getByTestId('capacity-cell-tue')).toHaveTextContent('75%');
    expect(screen.getByTestId('capacity-cell-wed')).toHaveTextContent('45%');
  });

  it('applies red styling for >90% utilization (overbooking)', () => {
    render(<CapacityHeatMap data={sampleData} />);
    const cell = screen.getByTestId('capacity-cell-mon');
    expect(cell.className).toContain('bg-red');
    expect(cell).toHaveTextContent('Overbooking risk');
  });

  it('applies green styling for 60-90% utilization (healthy)', () => {
    render(<CapacityHeatMap data={sampleData} />);
    const cell = screen.getByTestId('capacity-cell-tue');
    expect(cell.className).toContain('bg-green');
    expect(cell).toHaveTextContent('Healthy');
  });

  it('applies yellow styling for <60% utilization (underutilized)', () => {
    render(<CapacityHeatMap data={sampleData} />);
    const cell = screen.getByTestId('capacity-cell-wed');
    expect(cell.className).toContain('bg-yellow');
    expect(cell).toHaveTextContent('Underutilized');
  });

  it('renders empty when no data provided', () => {
    render(<CapacityHeatMap data={[]} />);
    expect(screen.getByTestId('capacity-heat-map')).toBeInTheDocument();
  });

  it('treats exactly 60% as healthy (green)', () => {
    render(<CapacityHeatMap data={[{ day: 'boundary', utilization: 60 }]} />);
    const cell = screen.getByTestId('capacity-cell-boundary');
    expect(cell.className).toContain('bg-green');
  });
});
