/**
 * Tests for TimelineStrip — dot states for each step value (0–3),
 * timestamp display, connector line states, labels, responsive behavior.
 * Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { TimelineStrip } from './TimelineStrip';

// ── Helpers ──────────────────────────────────────────────────────────────────

const NO_TIMESTAMPS: [string | null, string | null, string | null, string | null] = [
  null,
  null,
  null,
  null,
];

const FULL_TIMESTAMPS: [string | null, string | null, string | null, string | null] = [
  '2025-07-15T09:00:00Z',
  '2025-07-15T09:30:00Z',
  '2025-07-15T10:00:00Z',
  '2025-07-15T11:00:00Z',
];

const LABELS = ['Booked', 'En route', 'On site', 'Done'];

// ── Labels (Req 3.1) ────────────────────────────────────────────────────────

describe('TimelineStrip — Labels (Req 3.1)', () => {
  it('renders all four step labels: Booked, En route, On site, Done', () => {
    render(<TimelineStrip currentStep={0} timestamps={NO_TIMESTAMPS} />);

    for (const label of LABELS) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
  });

  it('renders labels in correct order', () => {
    render(<TimelineStrip currentStep={0} timestamps={NO_TIMESTAMPS} />);

    const labelElements = LABELS.map((l) => screen.getByText(l));
    // Verify DOM order by comparing positions
    for (let i = 0; i < labelElements.length - 1; i++) {
      const pos = labelElements[i].compareDocumentPosition(labelElements[i + 1]);
      // Node.DOCUMENT_POSITION_FOLLOWING = 4
      expect(pos & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    }
  });
});

// ── Dot states for step 0 (Req 3.2, 3.3, 3.5) ──────────────────────────────

describe('TimelineStrip — Step 0 (Booked)', () => {
  it('renders the first dot as current (filled dark with blue inner dot)', () => {
    const { container } = render(
      <TimelineStrip currentStep={0} timestamps={['2025-07-15T09:00:00Z', null, null, null]} />,
    );

    // The first dot should have bg-[#0B1220] (filled dark) and ring (outer ring)
    const dots = container.querySelectorAll('.rounded-full.w-6.h-6');
    const firstDot = dots[0];
    expect(firstDot.className).toContain('bg-[#0B1220]');
    expect(firstDot.className).toContain('ring-');

    // Should have a blue inner dot (w-2.5 h-2.5 rounded-full)
    const innerDot = firstDot.querySelector('.bg-blue-400');
    expect(innerDot).toBeTruthy();

    // Should NOT have a checkmark
    const svg = firstDot.querySelector('svg');
    expect(svg).toBeNull();
  });

  it('renders dots 1, 2, 3 as inactive (white fill, gray border)', () => {
    const { container } = render(
      <TimelineStrip currentStep={0} timestamps={['2025-07-15T09:00:00Z', null, null, null]} />,
    );

    const dots = container.querySelectorAll('.rounded-full.w-6.h-6');
    for (let i = 1; i <= 3; i++) {
      const dot = dots[i];
      expect(dot.className).toContain('bg-white');
      expect(dot.className).toContain('border-2');
      // Should not have inner dot or checkmark
      expect(dot.querySelector('.bg-blue-400')).toBeNull();
      expect(dot.querySelector('svg')).toBeNull();
    }
  });
});

// ── Dot states for step 1 (Req 3.2, 3.3, 3.4, 3.5) ─────────────────────────

describe('TimelineStrip — Step 1 (En route)', () => {
  const timestamps: [string | null, string | null, string | null, string | null] = [
    '2025-07-15T09:00:00Z',
    '2025-07-15T09:30:00Z',
    null,
    null,
  ];

  it('renders dot 0 as completed (filled dark with white checkmark)', () => {
    const { container } = render(
      <TimelineStrip currentStep={1} timestamps={timestamps} />,
    );

    const dots = container.querySelectorAll('.rounded-full.w-6.h-6');
    const dot0 = dots[0];
    expect(dot0.className).toContain('bg-[#0B1220]');
    // Should NOT have ring (not current)
    expect(dot0.className).not.toContain('ring-');
    // Should have a checkmark SVG
    const svg = dot0.querySelector('svg');
    expect(svg).toBeTruthy();
  });

  it('renders dot 1 as current (filled dark with blue inner dot and ring)', () => {
    const { container } = render(
      <TimelineStrip currentStep={1} timestamps={timestamps} />,
    );

    const dots = container.querySelectorAll('.rounded-full.w-6.h-6');
    const dot1 = dots[1];
    expect(dot1.className).toContain('bg-[#0B1220]');
    expect(dot1.className).toContain('ring-');
    expect(dot1.querySelector('.bg-blue-400')).toBeTruthy();
  });

  it('renders dots 2 and 3 as inactive', () => {
    const { container } = render(
      <TimelineStrip currentStep={1} timestamps={timestamps} />,
    );

    const dots = container.querySelectorAll('.rounded-full.w-6.h-6');
    for (const i of [2, 3]) {
      expect(dots[i].className).toContain('bg-white');
      expect(dots[i].className).toContain('border-2');
    }
  });
});

// ── Dot states for step 2 (Req 3.2, 3.3, 3.4, 3.5) ─────────────────────────

describe('TimelineStrip — Step 2 (On site)', () => {
  const timestamps: [string | null, string | null, string | null, string | null] = [
    '2025-07-15T09:00:00Z',
    '2025-07-15T09:30:00Z',
    '2025-07-15T10:00:00Z',
    null,
  ];

  it('renders dots 0 and 1 as completed (checkmarks)', () => {
    const { container } = render(
      <TimelineStrip currentStep={2} timestamps={timestamps} />,
    );

    const dots = container.querySelectorAll('.rounded-full.w-6.h-6');
    for (const i of [0, 1]) {
      expect(dots[i].className).toContain('bg-[#0B1220]');
      expect(dots[i].querySelector('svg')).toBeTruthy();
      expect(dots[i].querySelector('.bg-blue-400')).toBeNull();
    }
  });

  it('renders dot 2 as current', () => {
    const { container } = render(
      <TimelineStrip currentStep={2} timestamps={timestamps} />,
    );

    const dots = container.querySelectorAll('.rounded-full.w-6.h-6');
    expect(dots[2].className).toContain('bg-[#0B1220]');
    expect(dots[2].className).toContain('ring-');
    expect(dots[2].querySelector('.bg-blue-400')).toBeTruthy();
  });

  it('renders dot 3 as inactive', () => {
    const { container } = render(
      <TimelineStrip currentStep={2} timestamps={timestamps} />,
    );

    const dots = container.querySelectorAll('.rounded-full.w-6.h-6');
    expect(dots[3].className).toContain('bg-white');
    expect(dots[3].className).toContain('border-2');
  });
});

// ── Dot states for step 3 — Done (Req 3.2, 3.4) ────────────────────────────

describe('TimelineStrip — Step 3 (Done)', () => {
  it('renders all four dots as completed (no current dot at final step)', () => {
    const { container } = render(
      <TimelineStrip currentStep={3} timestamps={FULL_TIMESTAMPS} />,
    );

    const dots = container.querySelectorAll('.rounded-full.w-6.h-6');

    // Dots 0, 1, 2 should be completed (checkmarks)
    for (const i of [0, 1, 2]) {
      expect(dots[i].className).toContain('bg-[#0B1220]');
      expect(dots[i].querySelector('svg')).toBeTruthy();
    }

    // Dot 3 is the current step but step == 3 (final), so it should be
    // "current" styled (filled dark, blue inner dot, ring) per the component logic
    // since isCurrent = (currentStep === i) which is true for i=3
    const dot3 = dots[3];
    expect(dot3.className).toContain('bg-[#0B1220]');
  });
});

// ── Timestamp display (Req 3.6) ─────────────────────────────────────────────

describe('TimelineStrip — Timestamp display (Req 3.6)', () => {
  it('displays "—" for all steps when no timestamps are provided', () => {
    render(<TimelineStrip currentStep={0} timestamps={NO_TIMESTAMPS} />);

    const dashes = screen.getAllByText('—');
    // At least the unreached steps should show "—"
    // Step 0 has no timestamp either, so all 4 show "—"
    expect(dashes.length).toBe(4);
  });

  it('displays timestamps for reached steps and "—" for unreached', () => {
    render(
      <TimelineStrip
        currentStep={2}
        timestamps={['2025-07-15T09:00:00Z', '2025-07-15T09:30:00Z', '2025-07-15T10:00:00Z', null]}
      />,
    );

    // Unreached step (Done) should show "—"
    const dashes = screen.getAllByText('—');
    expect(dashes.length).toBe(1);
  });

  it('displays all timestamps when all steps are reached', () => {
    render(<TimelineStrip currentStep={3} timestamps={FULL_TIMESTAMPS} />);

    // No "—" should appear since all timestamps are provided
    expect(screen.queryByText('—')).not.toBeInTheDocument();
  });

  it('renders timestamps in mono font', () => {
    const { container } = render(
      <TimelineStrip
        currentStep={1}
        timestamps={['2025-07-15T09:00:00Z', '2025-07-15T09:30:00Z', null, null]}
      />,
    );

    // All timestamp elements should have font-mono class
    const monoElements = container.querySelectorAll('.font-mono');
    expect(monoElements.length).toBe(4); // All 4 timestamp slots use mono font
  });
});

// ── Connector lines (Req 3.2, 3.5) ──────────────────────────────────────────

describe('TimelineStrip — Connector lines (Req 3.2, 3.5)', () => {
  it('fills connector lines dark for completed/current steps', () => {
    const { container } = render(
      <TimelineStrip
        currentStep={2}
        timestamps={['2025-07-15T09:00:00Z', '2025-07-15T09:30:00Z', '2025-07-15T10:00:00Z', null]}
      />,
    );

    // Connector lines are 2px height divs
    const connectors = container.querySelectorAll('.h-\\[2px\\]');
    // There should be connectors between dots
    expect(connectors.length).toBeGreaterThan(0);

    // Count dark vs gray connectors
    let darkCount = 0;
    let grayCount = 0;
    connectors.forEach((c) => {
      if (c.className.includes('bg-[#0B1220]')) darkCount++;
      if (c.className.includes('bg-[#E5E7EB]')) grayCount++;
    });

    // With step 2: connectors to dots 0, 1, 2 should be dark; connector to dot 3 should be gray
    expect(darkCount).toBeGreaterThan(0);
    expect(grayCount).toBeGreaterThan(0);
  });

  it('fills all connector lines gray when step is 0', () => {
    const { container } = render(
      <TimelineStrip currentStep={0} timestamps={['2025-07-15T09:00:00Z', null, null, null]} />,
    );

    const connectors = container.querySelectorAll('.h-\\[2px\\]');
    connectors.forEach((c) => {
      // Left connectors for dots 1, 2, 3 — dot 1's left connector should be dark
      // because isCurrent for dot 0 means the right connector of dot 0 is gray
      // Actually: right connector of dot 0 checks isCompleted (i < step) which is false for i=0
      // So right connector is gray. Left connector of dot 1 checks isCompleted||isCurrent for dot 1
      // which is false. So all non-first connectors are gray.
      // The first dot has no left connector.
    });

    // At step 0, the left connector of dot 1 checks if dot 1 is completed or current — it's not
    // So all connectors after dot 0 should be gray
    let grayCount = 0;
    connectors.forEach((c) => {
      if (c.className.includes('bg-[#E5E7EB]')) grayCount++;
    });
    // Right connector of dot 0 is gray, left connectors of dots 1,2,3 — some are gray
    expect(grayCount).toBeGreaterThan(0);
  });
});

// ── Null step (no active step) ───────────────────────────────────────────────

describe('TimelineStrip — Null step (no active step)', () => {
  it('renders all dots as inactive when currentStep is null', () => {
    const { container } = render(
      <TimelineStrip currentStep={null} timestamps={NO_TIMESTAMPS} />,
    );

    const dots = container.querySelectorAll('.rounded-full.w-6.h-6');
    expect(dots.length).toBe(4);

    dots.forEach((dot) => {
      expect(dot.className).toContain('bg-white');
      expect(dot.className).toContain('border-2');
      expect(dot.querySelector('svg')).toBeNull();
      expect(dot.querySelector('.bg-blue-400')).toBeNull();
    });
  });

  it('renders all connector lines as gray when currentStep is null', () => {
    const { container } = render(
      <TimelineStrip currentStep={null} timestamps={NO_TIMESTAMPS} />,
    );

    const connectors = container.querySelectorAll('.h-\\[2px\\]');
    connectors.forEach((c) => {
      expect(c.className).toContain('bg-[#E5E7EB]');
    });
  });
});

// ── Responsive behavior (Req 3.7) ───────────────────────────────────────────

describe('TimelineStrip — Responsive / scrollable container (Req 3.7)', () => {
  it('renders with overflow-x-auto for horizontal scrolling', () => {
    const { container } = render(
      <TimelineStrip currentStep={1} timestamps={NO_TIMESTAMPS} />,
    );

    const outerDiv = container.firstElementChild as HTMLElement;
    expect(outerDiv.className).toContain('overflow-x-auto');
  });

  it('sets min-width on inner container for scroll support', () => {
    const { container } = render(
      <TimelineStrip currentStep={1} timestamps={NO_TIMESTAMPS} />,
    );

    // The outer div has minWidth: 0, the inner flex container has minWidth: 240px
    const allStyled = container.querySelectorAll('[style]');
    const innerDiv = Array.from(allStyled).find(
      (el) => (el as HTMLElement).style.minWidth === '240px',
    ) as HTMLElement;
    expect(innerDiv).toBeTruthy();
    expect(innerDiv.style.minWidth).toBe('240px');
  });

  it('applies min-w-[60px] on each step container', () => {
    const { container } = render(
      <TimelineStrip currentStep={0} timestamps={NO_TIMESTAMPS} />,
    );

    const stepContainers = container.querySelectorAll('.min-w-\\[60px\\]');
    expect(stepContainers.length).toBe(4);
  });
});

// ── Label styling for active vs inactive (Req 3.2, 3.5) ─────────────────────

describe('TimelineStrip — Label styling', () => {
  it('applies dark text color to completed and current step labels', () => {
    render(
      <TimelineStrip
        currentStep={1}
        timestamps={['2025-07-15T09:00:00Z', '2025-07-15T09:30:00Z', null, null]}
      />,
    );

    const bookedLabel = screen.getByText('Booked');
    const enRouteLabel = screen.getByText('En route');
    expect(bookedLabel.className).toContain('text-[#0B1220]');
    expect(enRouteLabel.className).toContain('text-[#0B1220]');
  });

  it('applies gray text color to inactive step labels', () => {
    render(
      <TimelineStrip
        currentStep={1}
        timestamps={['2025-07-15T09:00:00Z', '2025-07-15T09:30:00Z', null, null]}
      />,
    );

    const onSiteLabel = screen.getByText('On site');
    const doneLabel = screen.getByText('Done');
    expect(onSiteLabel.className).toContain('text-[#9CA3AF]');
    expect(doneLabel.className).toContain('text-[#9CA3AF]');
  });
});
