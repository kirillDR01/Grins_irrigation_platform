import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { AIStreamingText } from './AIStreamingText';

describe('AIStreamingText', () => {
  it('renders streaming text container', () => {
    render(<AIStreamingText text="Hello" isStreaming={false} />);
    expect(screen.getByTestId('ai-streaming-text')).toBeInTheDocument();
  });

  it('displays text content', () => {
    render(<AIStreamingText text="Hello world" isStreaming={false} />);
    expect(screen.getByText('Hello world')).toBeInTheDocument();
  });

  it('displays empty string when text is empty', () => {
    render(<AIStreamingText text="" isStreaming={false} />);
    const element = screen.getByTestId('ai-streaming-text');
    expect(element).toBeInTheDocument();
    expect(element.textContent).toBe('');
  });

  it('updates text content when prop changes', () => {
    const { rerender } = render(<AIStreamingText text="Initial" isStreaming={false} />);
    expect(screen.getByText('Initial')).toBeInTheDocument();
    
    rerender(<AIStreamingText text="Updated" isStreaming={false} />);
    expect(screen.getByText('Updated')).toBeInTheDocument();
  });

  it('handles multiline text with whitespace-pre-wrap', () => {
    const multilineText = 'Line 1\nLine 2\nLine 3';
    render(<AIStreamingText text={multilineText} isStreaming={false} />);
    const element = screen.getByTestId('ai-streaming-text');
    expect(element).toHaveClass('whitespace-pre-wrap');
    expect(element.textContent).toBe(multilineText);
  });
});
