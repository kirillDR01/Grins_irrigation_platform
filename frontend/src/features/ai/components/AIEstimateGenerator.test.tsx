import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { AIEstimateGenerator } from './AIEstimateGenerator';
import type { EstimateResponse } from '../types';

const mockEstimate: EstimateResponse = {
  estimated_price: 1500.0,
  estimated_zones: 5,
  confidence_score: 0.92,
  breakdown: {
    materials: 400.0,
    labor: 800.0,
    equipment: 150.0,
    margin: 150.0,
  },
  similar_jobs: [
    {
      service_type: 'Spring Startup',
      zone_count: 5,
      final_price: 1450.0,
      similarity_score: 0.95,
    },
    {
      service_type: 'System Installation',
      zone_count: 4,
      final_price: 1200.0,
      similarity_score: 0.88,
    },
  ],
  recommendation: 'Site visit recommended to verify zone count',
  ai_notes: 'Property size suggests 5 zones based on similar properties',
};

describe('AIEstimateGenerator', () => {
  it('renders loading state', () => {
    render(
      <AIEstimateGenerator
        estimate={null}
        isLoading={true}
        error={null}
        onGeneratePDF={vi.fn()}
        onScheduleSiteVisit={vi.fn()}
        onAdjustQuote={vi.fn()}
      />
    );

    expect(screen.getByTestId('ai-estimate-generator')).toBeInTheDocument();
    expect(screen.getByText('Generating estimate...')).toBeInTheDocument();
  });

  it('renders error state', () => {
    const error = new Error('Failed to generate estimate');
    render(
      <AIEstimateGenerator
        estimate={null}
        isLoading={false}
        error={error}
        onGeneratePDF={vi.fn()}
        onScheduleSiteVisit={vi.fn()}
        onAdjustQuote={vi.fn()}
      />
    );

    expect(screen.getByTestId('ai-estimate-generator')).toBeInTheDocument();
    expect(screen.getByText('Failed to generate estimate')).toBeInTheDocument();
  });

  it('renders estimate with all sections', () => {
    render(
      <AIEstimateGenerator
        estimate={mockEstimate}
        isLoading={false}
        error={null}
        onGeneratePDF={vi.fn()}
        onScheduleSiteVisit={vi.fn()}
        onAdjustQuote={vi.fn()}
      />
    );

    expect(screen.getByTestId('ai-estimate-generator')).toBeInTheDocument();
    expect(screen.getByText('AI-Generated Estimate')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument(); // zones
    expect(screen.getByText('92%')).toBeInTheDocument(); // confidence
  });

  it('renders price breakdown', () => {
    render(
      <AIEstimateGenerator
        estimate={mockEstimate}
        isLoading={false}
        error={null}
        onGeneratePDF={vi.fn()}
        onScheduleSiteVisit={vi.fn()}
        onAdjustQuote={vi.fn()}
      />
    );

    const breakdown = screen.getByTestId('estimate-breakdown');
    expect(breakdown).toBeInTheDocument();
    expect(screen.getByText('$400.00')).toBeInTheDocument(); // materials
    expect(screen.getByText('$800.00')).toBeInTheDocument(); // labor
    expect(screen.getAllByText('$150.00')).toHaveLength(2); // equipment and margin
    expect(screen.getByText('$1500.00')).toBeInTheDocument(); // total
  });

  it('renders similar jobs', () => {
    render(
      <AIEstimateGenerator
        estimate={mockEstimate}
        isLoading={false}
        error={null}
        onGeneratePDF={vi.fn()}
        onScheduleSiteVisit={vi.fn()}
        onAdjustQuote={vi.fn()}
      />
    );

    expect(screen.getByTestId('similar-jobs')).toBeInTheDocument();
    expect(screen.getByText('Spring Startup')).toBeInTheDocument();
    expect(screen.getByText('System Installation')).toBeInTheDocument();
  });

  it('renders AI recommendation', () => {
    render(
      <AIEstimateGenerator
        estimate={mockEstimate}
        isLoading={false}
        error={null}
        onGeneratePDF={vi.fn()}
        onScheduleSiteVisit={vi.fn()}
        onAdjustQuote={vi.fn()}
      />
    );

    expect(screen.getByText(/Site visit recommended/)).toBeInTheDocument();
  });

  it('renders action buttons with correct data-testid', () => {
    render(
      <AIEstimateGenerator
        estimate={mockEstimate}
        isLoading={false}
        error={null}
        onGeneratePDF={vi.fn()}
        onScheduleSiteVisit={vi.fn()}
        onAdjustQuote={vi.fn()}
      />
    );

    expect(screen.getByTestId('generate-pdf-btn')).toBeInTheDocument();
    expect(screen.getByTestId('schedule-visit-btn')).toBeInTheDocument();
    expect(screen.getByTestId('adjust-quote-btn')).toBeInTheDocument();
  });

  it('calls onGeneratePDF when Generate PDF button clicked', () => {
    const onGeneratePDF = vi.fn();
    render(
      <AIEstimateGenerator
        estimate={mockEstimate}
        isLoading={false}
        error={null}
        onGeneratePDF={onGeneratePDF}
        onScheduleSiteVisit={vi.fn()}
        onAdjustQuote={vi.fn()}
      />
    );

    screen.getByTestId('generate-pdf-btn').click();
    expect(onGeneratePDF).toHaveBeenCalledOnce();
  });

  it('calls onScheduleSiteVisit when Schedule Site Visit button clicked', () => {
    const onScheduleSiteVisit = vi.fn();
    render(
      <AIEstimateGenerator
        estimate={mockEstimate}
        isLoading={false}
        error={null}
        onGeneratePDF={vi.fn()}
        onScheduleSiteVisit={onScheduleSiteVisit}
        onAdjustQuote={vi.fn()}
      />
    );

    screen.getByTestId('schedule-visit-btn').click();
    expect(onScheduleSiteVisit).toHaveBeenCalledOnce();
  });

  it('calls onAdjustQuote when Adjust Quote button clicked', () => {
    const onAdjustQuote = vi.fn();
    render(
      <AIEstimateGenerator
        estimate={mockEstimate}
        isLoading={false}
        error={null}
        onGeneratePDF={vi.fn()}
        onScheduleSiteVisit={vi.fn()}
        onAdjustQuote={onAdjustQuote}
      />
    );

    screen.getByTestId('adjust-quote-btn').click();
    expect(onAdjustQuote).toHaveBeenCalledOnce();
  });

  it('returns null when no estimate and not loading', () => {
    const { container } = render(
      <AIEstimateGenerator
        estimate={null}
        isLoading={false}
        error={null}
        onGeneratePDF={vi.fn()}
        onScheduleSiteVisit={vi.fn()}
        onAdjustQuote={vi.fn()}
      />
    );

    expect(container.firstChild).toBeNull();
  });
});
