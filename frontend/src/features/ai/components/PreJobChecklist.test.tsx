/**
 * Tests for PreJobChecklist component.
 * Validates: Requirements 30.6, 30.7, 30.8
 */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect } from 'vitest';
import { PreJobChecklist, type PreJobChecklistData } from './PreJobChecklist';

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
  MapPin: () => <span>📍</span>,
  Wrench: () => <span>🔧</span>,
  AlertTriangle: () => <span>⚠️</span>,
  Key: () => <span>🔑</span>,
  FileText: () => <span>📄</span>,
  Clock: () => <span>🕐</span>,
}));

const sampleChecklist: PreJobChecklistData = {
  job_type: 'Spring Opening',
  customer_name: 'John Smith',
  customer_address: '123 Main St, Eden Prairie, MN',
  required_equipment: ['Backflow tester', 'Pipe wrench', 'Teflon tape'],
  known_issues: ['Low water pressure reported last visit', 'Dog in backyard'],
  gate_code: '4521',
  special_instructions: 'Enter through side gate. Ring doorbell first.',
  estimated_duration: 90,
};

describe('PreJobChecklist', () => {
  it('renders with data-testid', () => {
    render(<PreJobChecklist checklist={sampleChecklist} />);
    expect(screen.getByTestId('prejob-checklist')).toBeInTheDocument();
  });

  it('displays job type', () => {
    render(<PreJobChecklist checklist={sampleChecklist} />);
    expect(screen.getByText('Spring Opening')).toBeInTheDocument();
  });

  it('displays customer name', () => {
    render(<PreJobChecklist checklist={sampleChecklist} />);
    expect(screen.getByText('John Smith')).toBeInTheDocument();
  });

  it('displays customer address', () => {
    render(<PreJobChecklist checklist={sampleChecklist} />);
    expect(screen.getByText('123 Main St, Eden Prairie, MN')).toBeInTheDocument();
  });

  it('displays estimated duration', () => {
    render(<PreJobChecklist checklist={sampleChecklist} />);
    expect(screen.getByText('Est. 90 min')).toBeInTheDocument();
  });

  it('displays gate code', () => {
    render(<PreJobChecklist checklist={sampleChecklist} />);
    expect(screen.getByText('4521')).toBeInTheDocument();
  });

  it('displays special instructions', () => {
    render(<PreJobChecklist checklist={sampleChecklist} />);
    expect(screen.getByText('Enter through side gate. Ring doorbell first.')).toBeInTheDocument();
  });

  it('displays known issues', () => {
    render(<PreJobChecklist checklist={sampleChecklist} />);
    expect(screen.getByText('Low water pressure reported last visit')).toBeInTheDocument();
    expect(screen.getByText('Dog in backyard')).toBeInTheDocument();
  });

  it('renders equipment checkboxes', () => {
    render(<PreJobChecklist checklist={sampleChecklist} />);
    expect(screen.getByTestId('equipment-check-backflow-tester')).toBeInTheDocument();
    expect(screen.getByTestId('equipment-check-pipe-wrench')).toBeInTheDocument();
    expect(screen.getByTestId('equipment-check-teflon-tape')).toBeInTheDocument();
  });

  it('toggles equipment checkbox on click', async () => {
    const user = userEvent.setup();
    render(<PreJobChecklist checklist={sampleChecklist} />);

    const checkbox = screen.getByTestId('equipment-check-backflow-tester');
    expect(checkbox).not.toBeChecked();

    await user.click(checkbox);
    expect(checkbox).toBeChecked();

    await user.click(checkbox);
    expect(checkbox).not.toBeChecked();
  });

  it('hides gate code section when null', () => {
    const noGate = { ...sampleChecklist, gate_code: null };
    render(<PreJobChecklist checklist={noGate} />);
    expect(screen.queryByText('Gate code:')).not.toBeInTheDocument();
  });

  it('hides special instructions when null', () => {
    const noInstructions = { ...sampleChecklist, special_instructions: null };
    render(<PreJobChecklist checklist={noInstructions} />);
    expect(screen.queryByText('Enter through side gate.')).not.toBeInTheDocument();
  });

  it('hides known issues section when empty', () => {
    const noIssues = { ...sampleChecklist, known_issues: [] };
    render(<PreJobChecklist checklist={noIssues} />);
    expect(screen.queryByText('Known Issues')).not.toBeInTheDocument();
  });

  it('hides equipment section when empty', () => {
    const noEquipment = { ...sampleChecklist, required_equipment: [] };
    render(<PreJobChecklist checklist={noEquipment} />);
    expect(screen.queryByText('Required Equipment')).not.toBeInTheDocument();
  });
});
