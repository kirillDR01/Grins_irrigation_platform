import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { CustomerSearch } from './CustomerSearch';

describe('CustomerSearch', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders search input', () => {
    const onSearch = vi.fn();
    render(<CustomerSearch onSearch={onSearch} />);

    expect(screen.getByTestId('customer-search')).toBeInTheDocument();
    expect(screen.getByTestId('customer-search-input')).toBeInTheDocument();
  });

  it('renders with custom placeholder', () => {
    const onSearch = vi.fn();
    render(<CustomerSearch onSearch={onSearch} placeholder="Find customers..." />);

    expect(screen.getByPlaceholderText('Find customers...')).toBeInTheDocument();
  });

  it('renders with initial value', () => {
    const onSearch = vi.fn();
    render(<CustomerSearch onSearch={onSearch} initialValue="John" />);

    expect(screen.getByDisplayValue('John')).toBeInTheDocument();
  });

  it('shows clear button when value is present', async () => {
    const onSearch = vi.fn();
    render(<CustomerSearch onSearch={onSearch} initialValue="test" />);

    expect(screen.getByTestId('customer-search-clear')).toBeInTheDocument();
  });

  it('hides clear button when value is empty', () => {
    const onSearch = vi.fn();
    render(<CustomerSearch onSearch={onSearch} />);

    expect(screen.queryByTestId('customer-search-clear')).not.toBeInTheDocument();
  });

  it('clears input when clear button is clicked', async () => {
    const onSearch = vi.fn();
    render(<CustomerSearch onSearch={onSearch} initialValue="test" />);

    const clearButton = screen.getByTestId('customer-search-clear');
    fireEvent.click(clearButton);

    expect(screen.getByTestId('customer-search-input')).toHaveValue('');
    expect(onSearch).toHaveBeenCalledWith('');
  });

  it('clears input when Escape key is pressed', async () => {
    const onSearch = vi.fn();
    render(<CustomerSearch onSearch={onSearch} initialValue="test" />);

    const input = screen.getByTestId('customer-search-input');
    fireEvent.keyDown(input, { key: 'Escape' });

    expect(input).toHaveValue('');
    expect(onSearch).toHaveBeenCalledWith('');
  });

  it('debounces search callback', async () => {
    vi.useRealTimers(); // Use real timers for this test
    const onSearch = vi.fn();
    render(<CustomerSearch onSearch={onSearch} />);

    const input = screen.getByTestId('customer-search-input');
    
    // Type in the input
    fireEvent.change(input, { target: { value: 'John' } });

    // Wait for debounce (300ms + buffer)
    await new Promise((resolve) => setTimeout(resolve, 400));

    // After debounce, should be called with final value
    expect(onSearch).toHaveBeenCalledWith('John');
  });
});
