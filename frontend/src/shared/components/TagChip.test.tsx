/**
 * Tests for TagChip — tone colors, static/removable variants, accessibility, nowrap.
 * Validates: Requirements 17.1, 17.2, 17.3, 17.4, 17.5, 18.4
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TagChip, type TagTone } from './TagChip';

// ── Tone color tests (Req 17.2, 17.5) ───────────────────────────────────────

describe('TagChip — Tone colors render correct classes (Req 17.2, 17.5)', () => {
  const toneExpectations: Record<TagTone, { bg: string; text: string; border: string }> = {
    neutral: { bg: 'bg-gray-100', text: 'text-gray-700', border: 'border-gray-300' },
    blue: { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-300' },
    green: { bg: 'bg-green-50', text: 'text-green-700', border: 'border-green-300' },
    amber: { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-300' },
    violet: { bg: 'bg-violet-50', text: 'text-violet-700', border: 'border-violet-300' },
  };

  it.each(Object.entries(toneExpectations) as [TagTone, { bg: string; text: string; border: string }][])(
    'renders correct bg/text/border classes for "%s" tone',
    (tone, { bg, text, border }) => {
      render(<TagChip label="Test" tone={tone} />);

      const chip = screen.getByText('Test');
      expect(chip.className).toContain(bg);
      expect(chip.className).toContain(text);
      expect(chip.className).toContain(border);
    },
  );

  it('renders all 5 tones without errors', () => {
    const tones: TagTone[] = ['neutral', 'blue', 'green', 'amber', 'violet'];
    const { container } = render(
      <>
        {tones.map((tone) => (
          <TagChip key={tone} label={tone} tone={tone} />
        ))}
      </>,
    );

    expect(container.querySelectorAll('.inline-flex')).toHaveLength(5);
  });
});

// ── Static vs removable variants (Req 17.1, 17.3) ───────────────────────────

describe('TagChip — Static vs removable variants (Req 17.1, 17.3)', () => {
  it('renders as static (no remove button) when onRemove is not provided', () => {
    render(<TagChip label="Static tag" tone="blue" />);

    const chip = screen.getByText('Static tag');
    expect(chip).toBeInTheDocument();
    // No remove button should exist
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('applies static padding (px-[10px] py-[5px]) when not removable', () => {
    render(<TagChip label="Static" tone="neutral" />);

    const chip = screen.getByText('Static');
    expect(chip.className).toContain('px-[10px]');
    expect(chip.className).toContain('py-[5px]');
  });

  it('renders remove button when onRemove is provided', () => {
    render(<TagChip label="Removable tag" tone="green" onRemove={() => {}} />);

    expect(screen.getByRole('button', { name: /remove tag: removable tag/i })).toBeInTheDocument();
  });

  it('applies removable padding (pl-[10px] pr-[6px] py-[5px]) when removable', () => {
    render(<TagChip label="Removable" tone="amber" onRemove={() => {}} />);

    const chip = screen.getByText('Removable');
    expect(chip.className).toContain('pl-[10px]');
    expect(chip.className).toContain('pr-[6px]');
    expect(chip.className).toContain('py-[5px]');
  });

  it('calls onRemove when remove button is clicked', async () => {
    const onRemove = vi.fn();
    const user = userEvent.setup();

    render(<TagChip label="Click me" tone="violet" onRemove={onRemove} />);

    await user.click(screen.getByRole('button', { name: /remove tag: click me/i }));
    expect(onRemove).toHaveBeenCalledOnce();
  });

  it('does not call onRemove when removeDisabled is true', async () => {
    const onRemove = vi.fn();
    const user = userEvent.setup();

    render(
      <TagChip
        label="System tag"
        tone="amber"
        onRemove={onRemove}
        removeDisabled
        removeDisabledTooltip="System tags cannot be removed"
      />,
    );

    const removeBtn = screen.getByRole('button', { name: /remove tag: system tag/i });
    await user.click(removeBtn);
    expect(onRemove).not.toHaveBeenCalled();
  });

  it('renders remove button as disabled with tooltip for system tags', () => {
    render(
      <TagChip
        label="Overdue balance"
        tone="amber"
        onRemove={() => {}}
        removeDisabled
        removeDisabledTooltip="System tags cannot be removed"
      />,
    );

    const removeBtn = screen.getByRole('button', { name: /remove tag: overdue balance/i });
    expect(removeBtn).toBeDisabled();
    expect(removeBtn).toHaveAttribute('title', 'System tags cannot be removed');
  });
});

// ── Aria-label on remove button (Req 18.4) ───────────────────────────────────

describe('TagChip — Remove button aria-label (Req 18.4)', () => {
  it('has aria-label="Remove tag: [label]" on the remove button', () => {
    render(<TagChip label="Repeat customer" tone="green" onRemove={() => {}} />);

    const removeBtn = screen.getByRole('button');
    expect(removeBtn).toHaveAttribute('aria-label', 'Remove tag: Repeat customer');
  });

  it('includes the exact label text in the aria-label', () => {
    render(<TagChip label="Dog on property" tone="amber" onRemove={() => {}} />);

    expect(
      screen.getByLabelText('Remove tag: Dog on property'),
    ).toBeInTheDocument();
  });

  it('handles special characters in label for aria-label', () => {
    render(<TagChip label="VIP — Priority" tone="violet" onRemove={() => {}} />);

    expect(
      screen.getByLabelText('Remove tag: VIP — Priority'),
    ).toBeInTheDocument();
  });
});

// ── White-space nowrap (Req 17.4) ────────────────────────────────────────────

describe('TagChip — White-space nowrap (Req 17.4)', () => {
  it('applies whitespace-nowrap class to prevent label wrapping', () => {
    render(<TagChip label="A very long tag label that should not wrap" tone="neutral" />);

    const chip = screen.getByText('A very long tag label that should not wrap');
    expect(chip.className).toContain('whitespace-nowrap');
  });

  it('applies whitespace-nowrap on removable variant too', () => {
    render(
      <TagChip
        label="Long removable tag"
        tone="blue"
        onRemove={() => {}}
      />,
    );

    const chip = screen.getByText('Long removable tag');
    expect(chip.className).toContain('whitespace-nowrap');
  });
});

// ── Typography and shape (Req 17.1) ──────────────────────────────────────────

describe('TagChip — Typography and shape (Req 17.1)', () => {
  it('renders as inline-flex pill with rounded-full', () => {
    render(<TagChip label="Pill" tone="blue" />);

    const chip = screen.getByText('Pill');
    expect(chip.className).toContain('inline-flex');
    expect(chip.className).toContain('rounded-full');
  });

  it('applies font-extrabold and correct text size', () => {
    render(<TagChip label="Bold" tone="green" />);

    const chip = screen.getByText('Bold');
    expect(chip.className).toContain('font-extrabold');
    expect(chip.className).toContain('text-[12.5px]');
  });

  it('applies border class', () => {
    render(<TagChip label="Bordered" tone="violet" />);

    const chip = screen.getByText('Bordered');
    expect(chip.className).toContain('border');
  });

  it('accepts custom className', () => {
    render(<TagChip label="Custom" tone="neutral" className="mt-2" />);

    const chip = screen.getByText('Custom');
    expect(chip.className).toContain('mt-2');
  });
});
