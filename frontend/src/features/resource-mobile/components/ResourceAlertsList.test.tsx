import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ResourceAlertsList } from './ResourceAlertsList';
import type { ResourceAlert } from '../types';

const alerts: ResourceAlert[] = [
  {
    id: 'a1',
    type: 'job_added',
    title: 'New job added to your route',
    description: 'Spring Opening at 789 Elm St added at 2:00 PM.',
    job_id: 'j3',
    created_at: new Date().toISOString(),
  },
  {
    id: 'a2',
    type: 'route_resequenced',
    title: 'Route updated',
    description: 'Your route has been resequenced for efficiency.',
    job_id: null,
    created_at: new Date().toISOString(),
  },
  {
    id: 'a3',
    type: 'customer_access',
    title: 'Gate code updated',
    description: 'New gate code: 5678.',
    job_id: 'j1',
    created_at: new Date().toISOString(),
  },
];

describe('ResourceAlertsList', () => {
  it('renders with data-testid="resource-alerts-list"', () => {
    render(<ResourceAlertsList alerts={alerts} onDismiss={vi.fn()} />);
    expect(screen.getByTestId('resource-alerts-list')).toBeInTheDocument();
  });

  it('renders alert items with correct data-testid', () => {
    render(<ResourceAlertsList alerts={alerts} onDismiss={vi.fn()} />);
    expect(screen.getByTestId('resource-alert-a1')).toBeInTheDocument();
    expect(screen.getByTestId('resource-alert-a2')).toBeInTheDocument();
    expect(screen.getByTestId('resource-alert-a3')).toBeInTheDocument();
  });

  it('shows alert titles and descriptions', () => {
    render(<ResourceAlertsList alerts={alerts} onDismiss={vi.fn()} />);
    expect(screen.getByText('New job added to your route')).toBeInTheDocument();
    expect(screen.getByText('Spring Opening at 789 Elm St added at 2:00 PM.')).toBeInTheDocument();
  });

  it('shows correct label for job_added type', () => {
    render(<ResourceAlertsList alerts={[alerts[0]]} onDismiss={vi.fn()} />);
    expect(screen.getByText('Job Added')).toBeInTheDocument();
  });

  it('shows correct label for route_resequenced type', () => {
    render(<ResourceAlertsList alerts={[alerts[1]]} onDismiss={vi.fn()} />);
    expect(screen.getByText('Route Updated')).toBeInTheDocument();
  });

  it('shows correct label for customer_access type', () => {
    render(<ResourceAlertsList alerts={[alerts[2]]} onDismiss={vi.fn()} />);
    expect(screen.getByText('Access Info')).toBeInTheDocument();
  });

  it('calls onDismiss with alert id when dismiss button clicked', () => {
    const onDismiss = vi.fn();
    render(<ResourceAlertsList alerts={alerts} onDismiss={onDismiss} />);
    const dismissButtons = screen.getAllByRole('button');
    fireEvent.click(dismissButtons[0]);
    expect(onDismiss).toHaveBeenCalledWith('a1');
  });

  it('shows empty state when no alerts', () => {
    render(<ResourceAlertsList alerts={[]} onDismiss={vi.fn()} />);
    expect(screen.getByText('No alerts.')).toBeInTheDocument();
  });
});
