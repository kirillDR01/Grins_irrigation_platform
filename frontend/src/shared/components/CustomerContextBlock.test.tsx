/**
 * Tests for CustomerContextBlock component (appointment modal context).
 *
 * Validates: april-16th-fixes-enhancements Requirement 10A
 * - Customer context block renders all fields
 * - Safety warnings display correctly
 * - Links work (tap-to-call, maps)
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { CustomerContextBlock } from './CustomerContextBlock';

const fullContextData = {
  customer_name: 'John Doe',
  customer_phone: '6125551234',
  primary_address: '123 Main St',
  primary_city: 'Minneapolis',
  primary_state: 'MN',
  primary_zip: '55401',
  job_type: 'Spring Startup',
  last_contacted_at: '2025-04-10T10:00:00Z',
  preferred_service_time: 'Morning',
  is_priority: true,
  dogs_on_property: true,
  gate_code: '1234',
  access_instructions: 'Enter through side gate',
  is_red_flag: true,
  is_slow_payer: true,
};

describe('CustomerContextBlock', () => {
  it('renders the context block container', () => {
    render(<CustomerContextBlock data={fullContextData} />);
    expect(screen.getByTestId('customer-context-block')).toBeInTheDocument();
  });

  it('displays customer name', () => {
    render(<CustomerContextBlock data={fullContextData} />);
    expect(screen.getByTestId('ctx-customer-name')).toHaveTextContent('John Doe');
  });

  it('displays customer phone as tap-to-call link', () => {
    render(<CustomerContextBlock data={fullContextData} />);
    const phoneLink = screen.getByTestId('ctx-customer-phone');
    expect(phoneLink).toHaveTextContent('6125551234');
    expect(phoneLink).toHaveAttribute('href', 'tel:6125551234');
  });

  it('displays primary address with maps link', () => {
    render(<CustomerContextBlock data={fullContextData} />);
    const addressLink = screen.getByTestId('ctx-address');
    expect(addressLink).toBeInTheDocument();
    expect(addressLink).toHaveAttribute('href', expect.stringContaining('google.com/maps'));
    expect(addressLink).toHaveAttribute('target', '_blank');
  });

  it('displays job type', () => {
    render(<CustomerContextBlock data={fullContextData} />);
    expect(screen.getByTestId('ctx-job-type')).toHaveTextContent('Spring Startup');
  });

  it('displays last contacted date', () => {
    render(<CustomerContextBlock data={fullContextData} />);
    expect(screen.getByTestId('ctx-last-contacted')).toBeInTheDocument();
  });

  it('displays preferred service time', () => {
    render(<CustomerContextBlock data={fullContextData} />);
    expect(screen.getByTestId('ctx-preferred-time')).toHaveTextContent('Preferred: Morning');
  });

  it('displays is_priority badge', () => {
    render(<CustomerContextBlock data={fullContextData} />);
    expect(screen.getByTestId('ctx-priority-badge')).toBeInTheDocument();
    expect(screen.getByText('Priority')).toBeInTheDocument();
  });

  it('displays dogs_on_property warning', () => {
    render(<CustomerContextBlock data={fullContextData} />);
    expect(screen.getByTestId('ctx-dogs-warning')).toBeInTheDocument();
    expect(screen.getByText('Dogs on Property')).toBeInTheDocument();
  });

  it('displays gate_code', () => {
    render(<CustomerContextBlock data={fullContextData} />);
    expect(screen.getByTestId('ctx-gate-code')).toHaveTextContent('Gate: 1234');
  });

  it('displays access_instructions', () => {
    render(<CustomerContextBlock data={fullContextData} />);
    expect(screen.getByTestId('ctx-access-instructions')).toHaveTextContent(
      'Enter through side gate'
    );
  });

  it('displays is_red_flag pill', () => {
    render(<CustomerContextBlock data={fullContextData} />);
    expect(screen.getByTestId('ctx-red-flag-pill')).toBeInTheDocument();
    expect(screen.getByText('Red Flag')).toBeInTheDocument();
  });

  it('displays is_slow_payer pill', () => {
    render(<CustomerContextBlock data={fullContextData} />);
    expect(screen.getByTestId('ctx-slow-payer-pill')).toBeInTheDocument();
    expect(screen.getByText('Slow Payer')).toBeInTheDocument();
  });

  it('displays warnings section', () => {
    render(<CustomerContextBlock data={fullContextData} />);
    expect(screen.getByTestId('ctx-warnings')).toBeInTheDocument();
  });

  it('hides warnings section when no warnings', () => {
    render(
      <CustomerContextBlock
        data={{
          customer_name: 'Jane Smith',
          customer_phone: '6125559876',
        }}
      />
    );
    expect(screen.queryByTestId('ctx-warnings')).not.toBeInTheDocument();
  });

  it('handles partial data gracefully', () => {
    render(<CustomerContextBlock data={{ customer_name: 'Partial Data' }} />);
    expect(screen.getByTestId('ctx-customer-name')).toHaveTextContent('Partial Data');
    expect(screen.queryByTestId('ctx-customer-phone')).not.toBeInTheDocument();
    expect(screen.queryByTestId('ctx-address')).not.toBeInTheDocument();
    expect(screen.queryByTestId('ctx-job-type')).not.toBeInTheDocument();
  });

  it('handles empty data without crashing', () => {
    render(<CustomerContextBlock data={{}} />);
    expect(screen.getByTestId('customer-context-block')).toBeInTheDocument();
  });
});
