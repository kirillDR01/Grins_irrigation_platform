/**
 * Tests for AIQueryChat component
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AIQueryChat } from './AIQueryChat';
import * as aiApi from '../api/aiApi';

// Mock the AI API
vi.mock('../api/aiApi', () => ({
  aiApi: {
    chat: vi.fn(),
  },
}));

// Mock scrollIntoView
Element.prototype.scrollIntoView = vi.fn();

describe('AIQueryChat', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders chat interface', () => {
    render(<AIQueryChat />);
    
    expect(screen.getByTestId('ai-chat')).toBeInTheDocument();
    expect(screen.getByTestId('ai-chat-input')).toBeInTheDocument();
    expect(screen.getByTestId('ai-send-btn')).toBeInTheDocument();
    expect(screen.getByTestId('ai-chat-clear')).toBeInTheDocument();
  });

  it('displays example queries when no messages', () => {
    render(<AIQueryChat />);
    
    expect(screen.getByTestId('example-queries')).toBeInTheDocument();
    expect(screen.getByTestId('example-query-0')).toBeInTheDocument();
    expect(screen.getByTestId('example-query-1')).toBeInTheDocument();
  });

  it('fills input when example query is clicked', () => {
    render(<AIQueryChat />);
    
    const exampleButton = screen.getByTestId('example-query-0');
    fireEvent.click(exampleButton);
    
    const input = screen.getByTestId('ai-chat-input') as HTMLInputElement;
    expect(input.value).toBeTruthy();
  });

  it('sends message and displays response', async () => {
    const mockResponse = {
      message: 'You have 5 jobs scheduled today.',
      session_id: 'test-session',
      tokens_used: 50,
    };
    
    vi.mocked(aiApi.aiApi.chat).mockResolvedValue(mockResponse);
    
    render(<AIQueryChat />);
    
    const input = screen.getByTestId('ai-chat-input');
    const submitButton = screen.getByTestId('ai-send-btn');
    
    fireEvent.change(input, { target: { value: 'How many jobs today?' } });
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(screen.getByTestId('message-history')).toBeInTheDocument();
    });
    
    expect(screen.getByText('How many jobs today?')).toBeInTheDocument();
    expect(screen.getByText('You have 5 jobs scheduled today.')).toBeInTheDocument();
  });

  it('displays loading state while sending message', async () => {
    vi.mocked(aiApi.aiApi.chat).mockImplementation(
      () => new Promise(resolve => setTimeout(resolve, 100))
    );
    
    render(<AIQueryChat />);
    
    const input = screen.getByTestId('ai-chat-input');
    const submitButton = screen.getByTestId('ai-send-btn');
    
    fireEvent.change(input, { target: { value: 'Test message' } });
    fireEvent.click(submitButton);
    
    expect(screen.getByTestId('ai-chat-loading')).toBeInTheDocument();
  });

  it('displays error when API call fails', async () => {
    vi.mocked(aiApi.aiApi.chat).mockRejectedValue(new Error('API Error'));
    
    render(<AIQueryChat />);
    
    const input = screen.getByTestId('ai-chat-input');
    const submitButton = screen.getByTestId('ai-send-btn');
    
    fireEvent.change(input, { target: { value: 'Test message' } });
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(screen.getByTestId('ai-chat-error')).toBeInTheDocument();
    });
    
    expect(screen.getByText('API Error')).toBeInTheDocument();
  });

  it('clears chat when clear button is clicked', async () => {
    const mockResponse = {
      message: 'Response',
      session_id: 'test-session',
      tokens_used: 50,
    };
    
    vi.mocked(aiApi.aiApi.chat).mockResolvedValue(mockResponse);
    
    render(<AIQueryChat />);
    
    // Send a message
    const input = screen.getByTestId('ai-chat-input');
    fireEvent.change(input, { target: { value: 'Test' } });
    fireEvent.click(screen.getByTestId('ai-send-btn'));
    
    await waitFor(() => {
      expect(screen.getByTestId('message-history')).toBeInTheDocument();
    });
    
    // Clear chat
    fireEvent.click(screen.getByTestId('ai-chat-clear'));
    
    // After clearing, example queries should be visible again
    await waitFor(() => {
      expect(screen.getByTestId('example-queries')).toBeInTheDocument();
    });
  });

  it('displays message count', async () => {
    const mockResponse = {
      message: 'Response',
      session_id: 'test-session',
      tokens_used: 50,
    };
    
    vi.mocked(aiApi.aiApi.chat).mockResolvedValue(mockResponse);
    
    render(<AIQueryChat />);
    
    expect(screen.getByTestId('message-count')).toHaveTextContent('0 / 50 messages');
    
    // Send a message (adds 2 messages: user + assistant)
    const input = screen.getByTestId('ai-chat-input');
    fireEvent.change(input, { target: { value: 'Test' } });
    fireEvent.click(screen.getByTestId('ai-send-btn'));
    
    await waitFor(() => {
      expect(screen.getByTestId('message-count')).toHaveTextContent('2 / 50 messages');
    });
  });

  it('disables input and submit when loading', async () => {
    vi.mocked(aiApi.aiApi.chat).mockImplementation(
      () => new Promise(resolve => setTimeout(resolve, 100))
    );
    
    render(<AIQueryChat />);
    
    const input = screen.getByTestId('ai-chat-input') as HTMLInputElement;
    const submitButton = screen.getByTestId('ai-send-btn') as HTMLButtonElement;
    
    fireEvent.change(input, { target: { value: 'Test' } });
    fireEvent.click(submitButton);
    
    expect(input.disabled).toBe(true);
    expect(submitButton.disabled).toBe(true);
  });

  it('does not submit empty messages', () => {
    render(<AIQueryChat />);
    
    const submitButton = screen.getByTestId('ai-send-btn') as HTMLButtonElement;
    
    expect(submitButton.disabled).toBe(true);
    
    fireEvent.click(submitButton);
    
    expect(aiApi.aiApi.chat).not.toHaveBeenCalled();
  });
});
