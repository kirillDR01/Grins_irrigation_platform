import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { SheetContainer } from './SheetContainer';

describe('SheetContainer', () => {
  it('renders root with responsive width tokens (regression guard for BUG-1)', () => {
    const { container } = render(
      <SheetContainer title="Tag editor" onClose={() => {}}>
        <p>body</p>
      </SheetContainer>,
    );
    const root = container.querySelector('div.flex.flex-col');
    expect(root).not.toBeNull();
    const className = root!.className;
    expect(className).toContain('w-full');
    expect(className).toContain('sm:w-[560px]');
    expect(className).toContain('max-w-full');
    expect(className).not.toMatch(/(?<!sm:)w-\[560px\]/);
  });
});
