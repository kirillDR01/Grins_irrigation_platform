/**
 * Tests for TagEditorSheet — current tags display, suggested filtering,
 * add/remove draft, save flow, system tag protection, custom tag input,
 * info banner.
 * Validates: Requirements 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 13.7,
 *            13.9, 13.10, 13.12
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TagEditorSheet } from './TagEditorSheet';
import type { CustomerTag } from '../../types';

// ── Mock data ────────────────────────────────────────────────────────────────

const manualTag1: CustomerTag = {
  id: 'tag-1',
  customer_id: 'cust-001',
  label: 'Repeat customer',
  tone: 'green',
  source: 'manual',
  created_at: '2025-07-01T12:00:00Z',
};

const manualTag2: CustomerTag = {
  id: 'tag-2',
  customer_id: 'cust-001',
  label: 'Dog on property',
  tone: 'amber',
  source: 'manual',
  created_at: '2025-07-02T12:00:00Z',
};

const systemTag: CustomerTag = {
  id: 'tag-sys-1',
  customer_id: 'cust-001',
  label: 'Overdue balance',
  tone: 'amber',
  source: 'system',
  created_at: '2025-06-15T12:00:00Z',
};

// ── Mock hooks ───────────────────────────────────────────────────────────────

const mockMutateAsync = vi.fn();
let mockTagsData: CustomerTag[] = [];

vi.mock('../../hooks/useCustomerTags', () => ({
  useCustomerTags: () => ({
    data: mockTagsData,
    isLoading: false,
    error: null,
  }),
  useSaveCustomerTags: () => ({
    mutateAsync: mockMutateAsync,
    isPending: false,
  }),
  customerTagKeys: {
    all: ['customer-tags'] as const,
    byCustomer: (id: string) => ['customer-tags', id] as const,
  },
}));

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}));

// ── Helpers ──────────────────────────────────────────────────────────────────

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

function renderSheet(props?: Partial<Parameters<typeof TagEditorSheet>[0]>) {
  return render(
    <TagEditorSheet
      customerId="cust-001"
      customerName="Jane Smith"
      onClose={vi.fn()}
      {...props}
    />,
    { wrapper: createWrapper() },
  );
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe('TagEditorSheet — Sheet title and subtitle (Req 13.1)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockTagsData = [];
  });

  it('renders "Edit tags" as the sheet title', () => {
    renderSheet();
    expect(screen.getByText('Edit tags')).toBeInTheDocument();
  });

  it('renders subtitle with customer name', () => {
    renderSheet({ customerName: 'Jane Smith' });
    expect(
      screen.getByText('Tags apply to Jane Smith across every job — past and future'),
    ).toBeInTheDocument();
  });

  it('renders subtitle with a different customer name', () => {
    renderSheet({ customerName: 'Bob Johnson' });
    expect(
      screen.getByText('Tags apply to Bob Johnson across every job — past and future'),
    ).toBeInTheDocument();
  });
});

describe('TagEditorSheet — Current tags display (Req 13.2)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('displays current manual tags as removable TagChips', () => {
    mockTagsData = [manualTag1, manualTag2];
    renderSheet();

    expect(screen.getByText('Repeat customer')).toBeInTheDocument();
    expect(screen.getByText('Dog on property')).toBeInTheDocument();
  });

  it('displays "CURRENT TAGS" section label', () => {
    mockTagsData = [];
    renderSheet();

    expect(screen.getByText('Current tags')).toBeInTheDocument();
  });

  it('shows "No tags yet" when there are no tags', () => {
    mockTagsData = [];
    renderSheet();

    expect(screen.getByText('No tags yet')).toBeInTheDocument();
  });

  it('displays both system and manual tags', () => {
    mockTagsData = [systemTag, manualTag1];
    renderSheet();

    expect(screen.getByText('Overdue balance')).toBeInTheDocument();
    expect(screen.getByText('Repeat customer')).toBeInTheDocument();
  });
});

describe('TagEditorSheet — Suggested tags filtering (Req 13.5)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows all suggestions when no tags are applied', () => {
    mockTagsData = [];
    renderSheet();

    expect(screen.getByText('Suggested')).toBeInTheDocument();
    expect(screen.getByText('+ Repeat customer')).toBeInTheDocument();
    expect(screen.getByText('+ Commercial')).toBeInTheDocument();
    expect(screen.getByText('+ Difficult access')).toBeInTheDocument();
    expect(screen.getByText('+ Dog on property')).toBeInTheDocument();
    expect(screen.getByText('+ Prefers text')).toBeInTheDocument();
    expect(screen.getByText('+ Gate code needed')).toBeInTheDocument();
    expect(screen.getByText('+ Corner lot')).toBeInTheDocument();
  });

  it('filters out already-applied tags from suggestions', () => {
    mockTagsData = [manualTag1, manualTag2]; // "Repeat customer" and "Dog on property"
    renderSheet();

    // These should NOT appear in suggestions
    expect(screen.queryByText('+ Repeat customer')).not.toBeInTheDocument();
    expect(screen.queryByText('+ Dog on property')).not.toBeInTheDocument();

    // These should still appear
    expect(screen.getByText('+ Commercial')).toBeInTheDocument();
    expect(screen.getByText('+ Difficult access')).toBeInTheDocument();
    expect(screen.getByText('+ Prefers text')).toBeInTheDocument();
    expect(screen.getByText('+ Gate code needed')).toBeInTheDocument();
    expect(screen.getByText('+ Corner lot')).toBeInTheDocument();
  });

  it('hides the suggested section when all suggestions are applied', () => {
    // Apply all 7 suggested labels
    const allSuggested: CustomerTag[] = [
      'Repeat customer', 'Commercial', 'Difficult access',
      'Dog on property', 'Prefers text', 'Gate code needed', 'Corner lot',
    ].map((label, i) => ({
      id: `tag-${i}`,
      customer_id: 'cust-001',
      label,
      tone: 'neutral' as const,
      source: 'manual' as const,
      created_at: '2025-07-01T12:00:00Z',
    }));
    mockTagsData = allSuggested;
    renderSheet();

    expect(screen.queryByText('Suggested')).not.toBeInTheDocument();
  });
});

describe('TagEditorSheet — Add suggested tag to draft (Req 13.6)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('adds a suggested tag to the current tags when clicked', async () => {
    mockTagsData = [];
    const user = userEvent.setup();
    renderSheet();

    await user.click(screen.getByText('+ Commercial'));

    // "Commercial" should now appear in the current tags section
    expect(screen.getByText('Commercial')).toBeInTheDocument();
    // And should be removed from suggestions
    expect(screen.queryByText('+ Commercial')).not.toBeInTheDocument();
  });

  it('does not add duplicate tags', async () => {
    mockTagsData = [];
    const user = userEvent.setup();
    renderSheet();

    // Add "Commercial" once
    await user.click(screen.getByText('+ Commercial'));

    // "Commercial" should appear in current tags and not in suggestions
    expect(screen.getByText('Commercial')).toBeInTheDocument();
    expect(screen.queryByText('+ Commercial')).not.toBeInTheDocument();
  });
});

describe('TagEditorSheet — Remove tag from draft (Req 13.3)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('removes a manual tag from the draft when remove button is clicked', async () => {
    mockTagsData = [manualTag1];
    const user = userEvent.setup();
    renderSheet();

    // The tag should be visible
    expect(screen.getByText('Repeat customer')).toBeInTheDocument();

    // Click the remove button
    const removeBtn = screen.getByLabelText('Remove tag: Repeat customer');
    await user.click(removeBtn);

    // Tag should be removed from current tags
    // After removal, "No tags yet" should appear since it was the only tag
    expect(screen.getByText('No tags yet')).toBeInTheDocument();
  });

  it('re-adds removed tag to suggestions list', async () => {
    mockTagsData = [manualTag1]; // "Repeat customer"
    const user = userEvent.setup();
    renderSheet();

    // "Repeat customer" should NOT be in suggestions initially
    expect(screen.queryByText('+ Repeat customer')).not.toBeInTheDocument();

    // Remove the tag
    await user.click(screen.getByLabelText('Remove tag: Repeat customer'));

    // Now "Repeat customer" should reappear in suggestions
    expect(screen.getByText('+ Repeat customer')).toBeInTheDocument();
  });
});

describe('TagEditorSheet — System tag protection (Req 13.4, 13.12)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders system tag remove button as disabled', () => {
    mockTagsData = [systemTag];
    renderSheet();

    const removeBtn = screen.getByLabelText('Remove tag: Overdue balance');
    expect(removeBtn).toBeDisabled();
  });

  it('shows tooltip on disabled system tag remove button', () => {
    mockTagsData = [systemTag];
    renderSheet();

    const removeBtn = screen.getByLabelText('Remove tag: Overdue balance');
    expect(removeBtn).toHaveAttribute('title', 'System tags cannot be removed');
  });

  it('does not remove system tag when remove button is clicked', async () => {
    mockTagsData = [systemTag];
    const user = userEvent.setup();
    renderSheet();

    const removeBtn = screen.getByLabelText('Remove tag: Overdue balance');
    await user.click(removeBtn);

    // System tag should still be present
    expect(screen.getByText('Overdue balance')).toBeInTheDocument();
  });

  it('has accessible aria-label on system tag remove button (Req 13.12)', () => {
    mockTagsData = [systemTag];
    renderSheet();

    expect(
      screen.getByLabelText('Remove tag: Overdue balance'),
    ).toBeInTheDocument();
  });
});

describe('TagEditorSheet — Save flow (Req 13.9, 13.10)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('calls PUT endpoint with manual tags on save', async () => {
    mockTagsData = [manualTag1, systemTag];
    mockMutateAsync.mockResolvedValue({ tags: [], system_tags_preserved: 1 });
    const onClose = vi.fn();
    const user = userEvent.setup();
    renderSheet({ onClose });

    await user.click(screen.getByText('Save tags · applies everywhere'));

    expect(mockMutateAsync).toHaveBeenCalledWith({
      customerId: 'cust-001',
      data: {
        tags: [{ label: 'Repeat customer', tone: 'green' }],
      },
    });
  });

  it('closes the sheet on successful save', async () => {
    mockTagsData = [manualTag1];
    mockMutateAsync.mockResolvedValue({ tags: [], system_tags_preserved: 0 });
    const onClose = vi.fn();
    const user = userEvent.setup();
    renderSheet({ onClose });

    await user.click(screen.getByText('Save tags · applies everywhere'));

    await waitFor(() => {
      expect(onClose).toHaveBeenCalled();
    });
  });

  it('shows error toast on save failure (Req 13.10)', async () => {
    const { toast } = await import('sonner');
    mockTagsData = [manualTag1];
    mockMutateAsync.mockRejectedValue(new Error('Network error'));
    const onClose = vi.fn();
    const user = userEvent.setup();
    renderSheet({ onClose });

    await user.click(screen.getByText('Save tags · applies everywhere'));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith("Couldn't save tags — try again");
    });
    // Sheet should NOT close on failure
    expect(onClose).not.toHaveBeenCalled();
  });

  it('includes newly added tags in the save payload', async () => {
    mockTagsData = [];
    mockMutateAsync.mockResolvedValue({ tags: [], system_tags_preserved: 0 });
    const user = userEvent.setup();
    renderSheet();

    // Add a suggested tag
    await user.click(screen.getByText('+ Commercial'));

    // Save
    await user.click(screen.getByText('Save tags · applies everywhere'));

    expect(mockMutateAsync).toHaveBeenCalledWith({
      customerId: 'cust-001',
      data: {
        tags: [{ label: 'Commercial', tone: 'neutral' }],
      },
    });
  });

  it('excludes removed tags from the save payload', async () => {
    mockTagsData = [manualTag1, manualTag2];
    mockMutateAsync.mockResolvedValue({ tags: [], system_tags_preserved: 0 });
    const user = userEvent.setup();
    renderSheet();

    // Remove "Dog on property"
    await user.click(screen.getByLabelText('Remove tag: Dog on property'));

    // Save
    await user.click(screen.getByText('Save tags · applies everywhere'));

    expect(mockMutateAsync).toHaveBeenCalledWith({
      customerId: 'cust-001',
      data: {
        tags: [{ label: 'Repeat customer', tone: 'green' }],
      },
    });
  });

  it('does not include system tags in the save payload', async () => {
    mockTagsData = [systemTag, manualTag1];
    mockMutateAsync.mockResolvedValue({ tags: [], system_tags_preserved: 1 });
    const user = userEvent.setup();
    renderSheet();

    await user.click(screen.getByText('Save tags · applies everywhere'));

    // Only manual tags should be in the payload
    const callArgs = mockMutateAsync.mock.calls[0][0];
    const labels = callArgs.data.tags.map((t: { label: string }) => t.label);
    expect(labels).not.toContain('Overdue balance');
    expect(labels).toContain('Repeat customer');
  });
});

describe('TagEditorSheet — Custom tag input (Req 13.7)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockTagsData = [];
  });

  it('renders custom tag input with placeholder', () => {
    renderSheet();

    expect(screen.getByPlaceholderText('Add custom tag…')).toBeInTheDocument();
  });

  it('adds a custom tag when Add button is clicked', async () => {
    const user = userEvent.setup();
    renderSheet();

    const input = screen.getByPlaceholderText('Add custom tag…');
    await user.type(input, 'VIP Client');
    await user.click(screen.getByText('Add'));

    expect(screen.getByText('VIP Client')).toBeInTheDocument();
  });

  it('adds a custom tag when Enter is pressed', async () => {
    const user = userEvent.setup();
    renderSheet();

    const input = screen.getByPlaceholderText('Add custom tag…');
    await user.type(input, 'Priority{Enter}');

    expect(screen.getByText('Priority')).toBeInTheDocument();
  });

  it('clears the input after adding a custom tag', async () => {
    const user = userEvent.setup();
    renderSheet();

    const input = screen.getByPlaceholderText('Add custom tag…') as HTMLInputElement;
    await user.type(input, 'New tag');
    await user.click(screen.getByText('Add'));

    expect(input.value).toBe('');
  });

  it('caps custom tag input at 32 characters', async () => {
    const user = userEvent.setup();
    renderSheet();

    const input = screen.getByPlaceholderText('Add custom tag…') as HTMLInputElement;
    expect(input).toHaveAttribute('maxLength', '32');
  });

  it('disables Add button when input is empty', () => {
    renderSheet();

    const addBtn = screen.getByText('Add');
    expect(addBtn).toBeDisabled();
  });

  it('does not add duplicate custom tags', async () => {
    mockTagsData = [manualTag1]; // "Repeat customer"
    const user = userEvent.setup();
    renderSheet();

    const input = screen.getByPlaceholderText('Add custom tag…');
    await user.type(input, 'Repeat customer');
    await user.click(screen.getByText('Add'));

    // Should only have one instance of "Repeat customer"
    const chips = screen.getAllByText('Repeat customer');
    expect(chips).toHaveLength(1);
  });

  it('does not add empty/whitespace-only tags', async () => {
    const user = userEvent.setup();
    renderSheet();

    const input = screen.getByPlaceholderText('Add custom tag…');
    await user.type(input, '   ');
    await user.click(screen.getByText('Add'));

    // "No tags yet" should still be visible
    expect(screen.getByText('No tags yet')).toBeInTheDocument();
  });
});

describe('TagEditorSheet — Info banner (Req 13.8)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockTagsData = [];
  });

  it('displays the info banner about customer-scoped save', () => {
    renderSheet();

    expect(
      screen.getByText(
        'Tags are saved to the customer profile and appear on all their appointments.',
      ),
    ).toBeInTheDocument();
  });

  it('renders the info banner with blue background styling', () => {
    renderSheet();

    const banner = screen.getByText(
      'Tags are saved to the customer profile and appear on all their appointments.',
    );
    expect(banner.className).toContain('bg-[#DBEAFE]');
  });
});

describe('TagEditorSheet — Cancel button', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockTagsData = [];
  });

  it('calls onClose when Cancel is clicked', async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();
    renderSheet({ onClose });

    await user.click(screen.getByText('Cancel'));

    expect(onClose).toHaveBeenCalled();
  });
});

describe('TagEditorSheet — Close button in header', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockTagsData = [];
  });

  it('calls onClose when the sheet close button is clicked', async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();
    renderSheet({ onClose });

    await user.click(screen.getByLabelText('Close'));

    expect(onClose).toHaveBeenCalled();
  });
});
