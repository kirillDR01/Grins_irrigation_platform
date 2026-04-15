import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MessageComposer } from './MessageComposer';

// Mock the audience preview hook
vi.mock('../hooks', () => ({
  useAudiencePreview: () => ({
    mutate: vi.fn(),
    isPending: false,
  }),
}));

function createWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
}

function renderComposer(overrides: Partial<Parameters<typeof MessageComposer>[0]> = {}) {
  const defaults = {
    value: '',
    onChange: vi.fn(),
    audience: {},
  };
  return {
    ...render(<MessageComposer {...defaults} {...overrides} />, { wrapper: createWrapper() }),
    ...defaults,
    ...overrides,
  };
}

describe('MessageComposer', () => {
  it('renders textarea and merge field buttons', () => {
    renderComposer();
    expect(screen.getByTestId('message-body-input')).toBeInTheDocument();
    expect(screen.getByTestId('insert-first_name')).toBeInTheDocument();
    expect(screen.getByTestId('insert-last_name')).toBeInTheDocument();
    expect(screen.getByTestId('insert-next_appointment_date')).toBeInTheDocument();
  });

  it('shows segment info with GSM-7 encoding for plain text', () => {
    renderComposer({ value: 'Hello' });
    expect(screen.getByTestId('segment-info')).toHaveTextContent('GSM-7');
  });

  it('shows UCS-2 encoding when emoji present', () => {
    renderComposer({ value: 'Hello 😀' });
    expect(screen.getByTestId('segment-info')).toHaveTextContent('UCS-2');
  });

  it('shows segment badge', () => {
    renderComposer({ value: 'Hi' });
    expect(screen.getByTestId('segment-badge')).toHaveTextContent('1 segment');
  });

  it('shows multi-segment warning for long messages', () => {
    // Long enough to exceed 160 GSM-7 chars with prefix+footer
    renderComposer({ value: 'A'.repeat(150) });
    expect(screen.getByTestId('segment-warning')).toBeInTheDocument();
  });

  it('shows invalid merge field warning', () => {
    renderComposer({ value: 'Hi {unknown_field}!' });
    expect(screen.getByTestId('invalid-merge-fields')).toBeInTheDocument();
    expect(screen.getByTestId('invalid-merge-fields')).toHaveTextContent('unknown_field');
  });

  it('does not show invalid merge field warning for valid fields', () => {
    renderComposer({ value: 'Hi {first_name}!' });
    expect(screen.queryByTestId('invalid-merge-fields')).not.toBeInTheDocument();
  });

  it('calls onChange when typing in textarea', () => {
    const onChange = vi.fn();
    renderComposer({ onChange });
    fireEvent.change(screen.getByTestId('message-body-input'), { target: { value: 'test' } });
    expect(onChange).toHaveBeenCalledWith('test');
  });

  it('calls onChange with merge field when button clicked', () => {
    const onChange = vi.fn();
    renderComposer({ onChange, value: '' });
    fireEvent.click(screen.getByTestId('insert-first_name'));
    expect(onChange).toHaveBeenCalledWith(expect.stringContaining('{first_name}'));
  });

  it('shows empty preview message when no audience', () => {
    renderComposer();
    expect(screen.getByTestId('preview-empty')).toBeInTheDocument();
  });
});
