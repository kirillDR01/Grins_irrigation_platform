import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { PreJobChecklist } from './PreJobChecklist';
import type { PreJobChecklist as PreJobChecklistData } from '../types/aiScheduling';

const checklist: PreJobChecklistData = {
  job_type: 'Spring Opening',
  customer_name: 'John Smith',
  customer_address: '123 Main St, Minneapolis MN',
  required_equipment: ['Backflow tester', 'Zone controller'],
  known_issues: 'Zone 3 valve sticks.',
  gate_code: '1234',
  special_instructions: 'Ring doorbell twice.',
  estimated_duration: 90,
};

describe('PreJobChecklist', () => {
  it('renders with data-testid="prejob-checklist"', () => {
    render(<PreJobChecklist checklist={checklist} />);
    expect(screen.getByTestId('prejob-checklist')).toBeInTheDocument();
  });

  it('shows job type, customer name, address, and duration', () => {
    render(<PreJobChecklist checklist={checklist} />);
    expect(screen.getByText('Spring Opening')).toBeInTheDocument();
    expect(screen.getByText('John Smith')).toBeInTheDocument();
    expect(screen.getByText('123 Main St, Minneapolis MN')).toBeInTheDocument();
    expect(screen.getByText('90 min')).toBeInTheDocument();
  });

  it('shows gate code', () => {
    render(<PreJobChecklist checklist={checklist} />);
    expect(screen.getByText(/Gate Code:/)).toBeInTheDocument();
    expect(screen.getByText('1234')).toBeInTheDocument();
  });

  it('shows known issues', () => {
    render(<PreJobChecklist checklist={checklist} />);
    expect(screen.getByText('Zone 3 valve sticks.')).toBeInTheDocument();
  });

  it('shows special instructions', () => {
    render(<PreJobChecklist checklist={checklist} />);
    expect(screen.getByText('Ring doorbell twice.')).toBeInTheDocument();
  });

  it('renders equipment checkboxes', () => {
    render(<PreJobChecklist checklist={checklist} />);
    expect(screen.getByLabelText('Backflow tester')).toBeInTheDocument();
    expect(screen.getByLabelText('Zone controller')).toBeInTheDocument();
  });

  it('toggles equipment checkbox on click', () => {
    render(<PreJobChecklist checklist={checklist} />);
    const checkbox = screen.getByLabelText('Backflow tester') as HTMLInputElement;
    expect(checkbox.checked).toBe(false);
    fireEvent.click(checkbox);
    expect(checkbox.checked).toBe(true);
  });

  it('shows all-verified message when all equipment checked', () => {
    render(<PreJobChecklist checklist={checklist} />);
    fireEvent.click(screen.getByLabelText('Backflow tester'));
    fireEvent.click(screen.getByLabelText('Zone controller'));
    expect(screen.getByText('✓ All equipment verified')).toBeInTheDocument();
  });

  it('does not show gate code section when gate_code is null', () => {
    const noGate = { ...checklist, gate_code: undefined };
    render(<PreJobChecklist checklist={noGate as PreJobChecklistData} />);
    expect(screen.queryByText(/Gate Code:/)).toBeNull();
  });
});
