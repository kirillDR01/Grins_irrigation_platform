import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { ServiceOfferingDrawer } from './ServiceOfferingDrawer';
import { serviceApi } from '../api/serviceApi';
import type { ServiceOffering } from '../types';

vi.mock('../api/serviceApi', () => ({
  serviceApi: {
    list: vi.fn(),
    get: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    deactivate: vi.fn(),
    history: vi.fn(),
    exportMarkdown: vi.fn(),
  },
}));

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

function wrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
}

const mockOffering: ServiceOffering = {
  id: '11111111-1111-1111-1111-111111111111',
  name: 'Spring Start-Up',
  display_name: 'Spring Start-Up',
  slug: 'spring_startup_residential',
  category: 'seasonal',
  customer_type: 'residential',
  subcategory: 'maintenance',
  pricing_model: 'flat',
  pricing_rule: { price: 199 },
  description: null,
  base_price: '199.00',
  price_per_zone: null,
  estimated_duration_minutes: 60,
  duration_per_zone_minutes: null,
  staffing_required: 1,
  equipment_required: null,
  buffer_minutes: 10,
  lien_eligible: false,
  requires_prepay: false,
  is_active: true,
  replaced_by_id: null,
  includes_materials: false,
  source_text: null,
  created_at: '2026-05-01T00:00:00Z',
  updated_at: '2026-05-01T00:00:00Z',
};

describe('ServiceOfferingDrawer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders create form when offering is null', () => {
    render(
      <ServiceOfferingDrawer open onOpenChange={() => undefined} offering={null} />,
      { wrapper: wrapper() },
    );
    expect(screen.getByText('New offering')).toBeInTheDocument();
    expect(screen.getByTestId('offering-name-input')).toHaveValue('');
  });

  it('prefills fields when editing', () => {
    render(
      <ServiceOfferingDrawer
        open
        onOpenChange={() => undefined}
        offering={mockOffering}
      />,
      { wrapper: wrapper() },
    );
    expect(screen.getByText('Edit offering')).toBeInTheDocument();
    expect(screen.getByTestId('offering-name-input')).toHaveValue('Spring Start-Up');
    // Slug is locked when editing.
    expect(screen.getByTestId('offering-slug-input')).toBeDisabled();
  });

  it('renders structured field for the selected pricing_model', () => {
    render(
      <ServiceOfferingDrawer
        open
        onOpenChange={() => undefined}
        offering={mockOffering}
      />,
      { wrapper: wrapper() },
    );
    expect(screen.getByTestId('rule-price')).toHaveValue(199);
  });

  it('disables save when JSON is invalid', async () => {
    render(
      <ServiceOfferingDrawer
        open
        onOpenChange={() => undefined}
        offering={mockOffering}
      />,
      { wrapper: wrapper() },
    );
    const json = screen.getByTestId('offering-rule-json');
    // userEvent.type interprets `{` as a key chord — drop into fireEvent.
    fireEvent.change(json, { target: { value: '{ not json' } });
    await waitFor(() => {
      expect(screen.getByTestId('offering-save')).toBeDisabled();
    });
  });

  it('submitting calls update API with payload', async () => {
    vi.mocked(serviceApi.update).mockResolvedValue(mockOffering);
    const user = userEvent.setup();
    render(
      <ServiceOfferingDrawer
        open
        onOpenChange={() => undefined}
        offering={mockOffering}
      />,
      { wrapper: wrapper() },
    );
    await user.click(screen.getByTestId('offering-save'));
    await waitFor(() => {
      expect(serviceApi.update).toHaveBeenCalledWith(
        mockOffering.id,
        expect.objectContaining({
          name: 'Spring Start-Up',
          pricing_model: 'flat',
        }),
      );
    });
  });
});
