import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ApprovalConfirmation } from './ApprovalConfirmation';

function renderWithState(action: string) {
  // MemoryRouter doesn't support location.state directly in initialEntries,
  // so we use a wrapper that provides the state via the location object
  return render(
    <MemoryRouter initialEntries={[{ pathname: '/confirmed', state: { action } }]}>
      <ApprovalConfirmation />
    </MemoryRouter>
  );
}

describe('ApprovalConfirmation', () => {
  it('renders approved confirmation', () => {
    renderWithState('approved');

    expect(screen.getByTestId('approval-confirmation-page')).toBeInTheDocument();
    expect(screen.getByTestId('confirmation-title')).toHaveTextContent('Estimate Approved!');
    expect(screen.getByTestId('next-steps-list')).toBeInTheDocument();
  });

  it('renders rejected confirmation', () => {
    renderWithState('rejected');

    expect(screen.getByTestId('confirmation-title')).toHaveTextContent('Estimate Declined');
  });

  it('renders signed confirmation', () => {
    renderWithState('signed');

    expect(screen.getByTestId('confirmation-title')).toHaveTextContent('Contract Signed!');
  });

  it('defaults to approved when no state provided', () => {
    render(
      <MemoryRouter initialEntries={['/confirmed']}>
        <ApprovalConfirmation />
      </MemoryRouter>
    );

    expect(screen.getByTestId('confirmation-title')).toHaveTextContent('Estimate Approved!');
  });

  it('does not expose internal IDs', () => {
    const { container } = renderWithState('approved');
    const html = container.innerHTML;

    expect(html).not.toMatch(/customer_id|lead_id|staff_id|job_id/);
  });

  it('shows next steps list', () => {
    renderWithState('approved');

    const nextSteps = screen.getByTestId('next-steps-list');
    const items = nextSteps.querySelectorAll('li');
    expect(items.length).toBeGreaterThan(0);
  });
});
