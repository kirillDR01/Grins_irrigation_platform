import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { NewTextCampaignModal } from './NewTextCampaignModal';

// --- Mocks ---

const mockCreateCampaign = { mutateAsync: vi.fn(), isPending: false };
const mockSendCampaign = { mutateAsync: vi.fn(), isPending: false };
const mockAudiencePreview = { mutate: vi.fn(), isPending: false };

vi.mock('@/features/auth', () => ({
  useAuth: () => ({ user: { id: 'test-user-1' } }),
}));

vi.mock('../hooks', () => ({
  useCreateCampaign: () => mockCreateCampaign,
  useSendCampaign: () => mockSendCampaign,
  useAudiencePreview: () => mockAudiencePreview,
}));

// Mock child components to isolate wizard logic
vi.mock('./AudienceBuilder', () => ({
  AudienceBuilder: ({ onChange, preSelectedCustomerIds, preSelectedLeadIds }: {
    value: Record<string, unknown>;
    onChange: (v: Record<string, unknown>) => void;
    preSelectedCustomerIds?: string[];
    preSelectedLeadIds?: string[];
  }) => (
    <div data-testid="audience-builder-mock">
      <button
        data-testid="mock-select-customers"
        onClick={() => onChange({ customers: { ids_include: ['c1', 'c2'] } })}
      >
        Select Customers
      </button>
      {preSelectedCustomerIds && (
        <span data-testid="pre-customer-ids">{preSelectedCustomerIds.join(',')}</span>
      )}
      {preSelectedLeadIds && (
        <span data-testid="pre-lead-ids">{preSelectedLeadIds.join(',')}</span>
      )}
    </div>
  ),
}));

vi.mock('./MessageComposer', () => ({
  MessageComposer: ({ value, onChange }: { value: string; onChange: (v: string) => void }) => (
    <div data-testid="message-composer-mock">
      <input
        data-testid="mock-message-input"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  ),
}));

vi.mock('./CampaignReview', () => ({
  CampaignReview: ({ onSendNow }: { onSendNow: () => void }) => (
    <div data-testid="campaign-review-mock">
      <button data-testid="mock-send-now" onClick={onSendNow}>Send</button>
    </div>
  ),
}));

function createWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
}

describe('NewTextCampaignModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    mockCreateCampaign.mutateAsync.mockResolvedValue({ id: 'campaign-1' });
    mockSendCampaign.mutateAsync.mockResolvedValue({});
  });

  it('renders step 1 (Audience) when opened', () => {
    render(
      <NewTextCampaignModal open onOpenChange={vi.fn()} />,
      { wrapper: createWrapper() },
    );
    expect(screen.getByTestId('new-campaign-modal')).toBeInTheDocument();
    expect(screen.getByTestId('audience-builder-mock')).toBeInTheDocument();
    expect(screen.getByText(/Step 1 of 3/)).toBeInTheDocument();
  });

  it('shows step indicator with 3 steps', () => {
    render(
      <NewTextCampaignModal open onOpenChange={vi.fn()} />,
      { wrapper: createWrapper() },
    );
    expect(screen.getByTestId('step-indicator')).toBeInTheDocument();
    expect(screen.getByTestId('step-indicator').children).toHaveLength(3);
  });

  it('navigates to step 2 after selecting audience and clicking Next', async () => {
    render(
      <NewTextCampaignModal open onOpenChange={vi.fn()} />,
      { wrapper: createWrapper() },
    );

    // Select some customers
    fireEvent.click(screen.getByTestId('mock-select-customers'));
    // Click Next
    fireEvent.click(screen.getByTestId('wizard-next-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('message-composer-mock')).toBeInTheDocument();
    });
    expect(screen.getByText(/Step 2 of 3/)).toBeInTheDocument();
  });

  it('navigates back from step 2 to step 1', async () => {
    render(
      <NewTextCampaignModal open onOpenChange={vi.fn()} />,
      { wrapper: createWrapper() },
    );

    fireEvent.click(screen.getByTestId('mock-select-customers'));
    fireEvent.click(screen.getByTestId('wizard-next-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('message-composer-mock')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('wizard-back-btn'));
    expect(screen.getByTestId('audience-builder-mock')).toBeInTheDocument();
  });

  it('back button is disabled on step 1', () => {
    render(
      <NewTextCampaignModal open onOpenChange={vi.fn()} />,
      { wrapper: createWrapper() },
    );
    expect(screen.getByTestId('wizard-back-btn')).toBeDisabled();
  });

  it('creates DB draft on first Next click', async () => {
    render(
      <NewTextCampaignModal open onOpenChange={vi.fn()} />,
      { wrapper: createWrapper() },
    );

    fireEvent.click(screen.getByTestId('mock-select-customers'));
    fireEvent.click(screen.getByTestId('wizard-next-btn'));

    await waitFor(() => {
      expect(mockCreateCampaign.mutateAsync).toHaveBeenCalledOnce();
    });
  });

  it('passes preSelectedCustomerIds to AudienceBuilder', () => {
    render(
      <NewTextCampaignModal open onOpenChange={vi.fn()} preSelectedCustomerIds={['c1', 'c2']} />,
      { wrapper: createWrapper() },
    );
    expect(screen.getByTestId('pre-customer-ids')).toHaveTextContent('c1,c2');
  });

  it('passes preSelectedLeadIds to AudienceBuilder', () => {
    render(
      <NewTextCampaignModal open onOpenChange={vi.fn()} preSelectedLeadIds={['l1']} />,
      { wrapper: createWrapper() },
    );
    expect(screen.getByTestId('pre-lead-ids')).toHaveTextContent('l1');
  });

  describe('draft persistence', () => {
    it('saves draft to localStorage on field change', async () => {
      vi.useFakeTimers();
      render(
        <NewTextCampaignModal open onOpenChange={vi.fn()} />,
        { wrapper: createWrapper() },
      );

      fireEvent.click(screen.getByTestId('mock-select-customers'));

      // Advance past debounce
      vi.advanceTimersByTime(600);

      const stored = localStorage.getItem('comms:draft_campaign:test-user-1');
      expect(stored).not.toBeNull();
      const draft = JSON.parse(stored!);
      expect(draft.savedAt).toBeDefined();
      expect(draft.audience).toBeDefined();

      vi.useRealTimers();
    });

    it('clears draft from localStorage after successful send', async () => {
      vi.useFakeTimers();
      const onOpenChange = vi.fn();
      render(
        <NewTextCampaignModal open onOpenChange={onOpenChange} />,
        { wrapper: createWrapper() },
      );

      // Set some draft data
      fireEvent.click(screen.getByTestId('mock-select-customers'));
      vi.advanceTimersByTime(600);
      expect(localStorage.getItem('comms:draft_campaign:test-user-1')).not.toBeNull();

      // Navigate to step 2
      fireEvent.click(screen.getByTestId('wizard-next-btn'));
      await vi.waitFor(() => {
        expect(screen.getByTestId('message-composer-mock')).toBeInTheDocument();
      });

      // Type message and go to step 3
      fireEvent.change(screen.getByTestId('mock-message-input'), { target: { value: 'Hello!' } });
      fireEvent.click(screen.getByTestId('wizard-next-btn'));
      await vi.waitFor(() => {
        expect(screen.getByTestId('campaign-review-mock')).toBeInTheDocument();
      });

      // Send
      fireEvent.click(screen.getByTestId('mock-send-now'));
      await vi.waitFor(() => {
        expect(mockSendCampaign.mutateAsync).toHaveBeenCalled();
      });

      // Draft should be cleared
      await vi.waitFor(() => {
        expect(localStorage.getItem('comms:draft_campaign:test-user-1')).toBeNull();
      });

      vi.useRealTimers();
    });
  });
});
