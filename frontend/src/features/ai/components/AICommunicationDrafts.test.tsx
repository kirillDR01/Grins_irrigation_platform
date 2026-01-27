import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { AICommunicationDrafts } from './AICommunicationDrafts';
import type { CommunicationDraft } from '../types';

const mockDraft: CommunicationDraft = {
  draft_id: 'draft-1',
  customer_name: 'John Doe',
  customer_phone: '6125551234',
  message_type: 'appointment_confirmation',
  message_content: 'Your appointment is confirmed for tomorrow at 10am.',
  ai_notes: 'Customer prefers morning appointments',
  is_slow_payer: false,
};

describe('AICommunicationDrafts', () => {
  it('renders loading state', () => {
    render(<AICommunicationDrafts draft={null} isLoading={true} />);
    expect(screen.getByTestId('ai-loading-state')).toBeInTheDocument();
  });

  it('renders error state', () => {
    const error = new Error('Failed to load draft');
    render(<AICommunicationDrafts draft={null} error={error} />);
    expect(screen.getByTestId('ai-error-state')).toBeInTheDocument();
  });

  it('renders empty state when no draft', () => {
    render(<AICommunicationDrafts draft={null} />);
    expect(screen.getByTestId('ai-communication-drafts-empty')).toBeInTheDocument();
    expect(screen.getByText(/no draft available/i)).toBeInTheDocument();
  });

  it('renders draft with all required elements', () => {
    render(<AICommunicationDrafts draft={mockDraft} />);
    
    expect(screen.getByTestId('ai-communication-drafts')).toBeInTheDocument();
    expect(screen.getByTestId('draft-message')).toBeInTheDocument();
    expect(screen.getByTestId('send-now-btn')).toBeInTheDocument();
    expect(screen.getByTestId('edit-draft-btn')).toBeInTheDocument();
    expect(screen.getByTestId('schedule-later-btn')).toBeInTheDocument();
  });

  it('displays recipient information', () => {
    render(<AICommunicationDrafts draft={mockDraft} />);
    
    expect(screen.getByText('John Doe')).toBeInTheDocument();
    expect(screen.getByText('6125551234')).toBeInTheDocument();
  });

  it('displays message content', () => {
    render(<AICommunicationDrafts draft={mockDraft} />);
    
    expect(screen.getByText(/your appointment is confirmed/i)).toBeInTheDocument();
  });

  it('displays AI notes when present', () => {
    render(<AICommunicationDrafts draft={mockDraft} />);
    
    expect(screen.getByTestId('ai-notes')).toBeInTheDocument();
    expect(screen.getByText(/customer prefers morning appointments/i)).toBeInTheDocument();
  });

  it('displays slow payer warning when applicable', () => {
    const slowPayerDraft = { ...mockDraft, is_slow_payer: true };
    render(<AICommunicationDrafts draft={slowPayerDraft} />);
    
    expect(screen.getByTestId('slow-payer-warning')).toBeInTheDocument();
  });

  it('calls onSendNow when send button clicked', () => {
    const onSendNow = vi.fn();
    render(<AICommunicationDrafts draft={mockDraft} onSendNow={onSendNow} />);
    
    screen.getByTestId('send-now-btn').click();
    expect(onSendNow).toHaveBeenCalledWith('draft-1');
  });

  it('calls onEdit when edit button clicked', () => {
    const onEdit = vi.fn();
    render(<AICommunicationDrafts draft={mockDraft} onEdit={onEdit} />);
    
    screen.getByTestId('edit-draft-btn').click();
    expect(onEdit).toHaveBeenCalledWith('draft-1');
  });

  it('calls onScheduleLater when schedule button clicked', () => {
    const onScheduleLater = vi.fn();
    render(<AICommunicationDrafts draft={mockDraft} onScheduleLater={onScheduleLater} />);
    
    screen.getByTestId('schedule-later-btn').click();
    expect(onScheduleLater).toHaveBeenCalledWith('draft-1');
  });

  it('formats message type correctly', () => {
    render(<AICommunicationDrafts draft={mockDraft} />);
    
    expect(screen.getByText('appointment confirmation')).toBeInTheDocument();
  });
});
