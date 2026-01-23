/**
 * Tests for MetricsCard component.
 */

import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { Users } from 'lucide-react';
import { MetricsCard } from './MetricsCard';

describe('MetricsCard', () => {
  it('renders title and value', () => {
    render(<MetricsCard title="Total Customers" value={150} testId="test-card" />);

    expect(screen.getByText('Total Customers')).toBeInTheDocument();
    expect(screen.getByText('150')).toBeInTheDocument();
    expect(screen.getByTestId('test-card')).toBeInTheDocument();
  });

  it('renders description when provided', () => {
    render(
      <MetricsCard
        title="Total Customers"
        value={150}
        description="120 active"
        testId="test-card"
      />
    );

    expect(screen.getByText('120 active')).toBeInTheDocument();
  });

  it('renders icon when provided', () => {
    render(
      <MetricsCard
        title="Total Customers"
        value={150}
        icon={Users}
        testId="test-card"
      />
    );

    // Icon should be rendered (lucide-react renders as svg)
    const card = screen.getByTestId('test-card');
    expect(card.querySelector('svg')).toBeInTheDocument();
  });

  it('renders positive trend indicator', () => {
    render(
      <MetricsCard
        title="Total Customers"
        value={150}
        trend={{ value: 12, isPositive: true }}
        testId="test-card"
      />
    );

    expect(screen.getByText('+12% from last period')).toBeInTheDocument();
  });

  it('renders negative trend indicator', () => {
    render(
      <MetricsCard
        title="Total Customers"
        value={150}
        trend={{ value: 5, isPositive: false }}
        testId="test-card"
      />
    );

    expect(screen.getByText('-5% from last period')).toBeInTheDocument();
  });

  it('renders string value', () => {
    render(
      <MetricsCard title="Status" value="Active" testId="test-card" />
    );

    expect(screen.getByText('Active')).toBeInTheDocument();
  });

  it('renders without optional props', () => {
    render(<MetricsCard title="Simple Card" value={42} />);

    expect(screen.getByText('Simple Card')).toBeInTheDocument();
    expect(screen.getByText('42')).toBeInTheDocument();
  });
});
