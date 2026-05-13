/**
 * TagPicker tests — combobox autocomplete + inline create + save flow.
 *
 * Validates: Cluster A — tag-picker combobox UX.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TagPicker } from './TagPicker';
import type { CustomerTag } from '@/features/schedule/types';

const mockMutate = vi.fn();
let mockTags: CustomerTag[] = [];

vi.mock('@/features/schedule/hooks/useCustomerTags', () => ({
  useCustomerTags: () => ({ data: mockTags, isLoading: false, error: null }),
  useSaveCustomerTags: () => ({
    mutate: mockMutate,
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  customerTagKeys: {
    all: ['customer-tags'] as const,
    byCustomer: (id: string) => ['customer-tags', id] as const,
  },
}));

vi.mock('sonner', () => ({
  toast: { error: vi.fn(), success: vi.fn() },
}));

function makeTag(label: string, source: 'manual' | 'system' = 'manual'): CustomerTag {
  return {
    id: `tag-${label}`,
    customer_id: 'cust-1',
    label,
    tone: 'neutral',
    source,
    created_at: '2026-05-13T00:00:00Z',
  };
}

describe('TagPicker', () => {
  beforeEach(() => {
    mockMutate.mockClear();
    mockTags = [];
  });

  it('renders existing tags as chips', () => {
    mockTags = [makeTag('VIP', 'manual'), makeTag('Priority', 'system')];
    render(<TagPicker customerId="cust-1" />);
    expect(screen.getByText('VIP')).toBeInTheDocument();
    expect(screen.getByText('Priority')).toBeInTheDocument();
  });

  it('shows empty placeholder + Add button when no tags', () => {
    render(<TagPicker customerId="cust-1" />);
    expect(screen.getByText(/no tags yet/i)).toBeInTheDocument();
    expect(screen.getByTestId('tag-picker-add-button')).toBeInTheDocument();
  });

  it('typing a non-matching label surfaces the inline create row', async () => {
    const user = userEvent.setup();
    render(<TagPicker customerId="cust-1" />);
    await user.click(screen.getByTestId('tag-picker-add-button'));
    const input = await screen.findByTestId('tag-picker-input');
    await user.type(input, 'BrandNew');
    expect(screen.getByTestId('tag-picker-create-item')).toHaveTextContent(
      /Create.+BrandNew/,
    );
  });

  it('selecting the create item invokes useSaveCustomerTags.mutate with the new tag', async () => {
    const user = userEvent.setup();
    render(<TagPicker customerId="cust-1" />);
    await user.click(screen.getByTestId('tag-picker-add-button'));
    const input = await screen.findByTestId('tag-picker-input');
    await user.type(input, 'NewLabel');
    await user.click(screen.getByTestId('tag-picker-create-item'));
    expect(mockMutate).toHaveBeenCalledTimes(1);
    const [{ customerId, data }] = mockMutate.mock.calls[0];
    expect(customerId).toBe('cust-1');
    expect(data.tags).toEqual([{ label: 'NewLabel', tone: 'neutral' }]);
  });
});
