import { describe, it, expect } from 'vitest';
import { getCustomerTagStyle } from './customer-tag-colors';

describe('getCustomerTagStyle', () => {
  it('maps priority to VIP / vip variant', () => {
    expect(getCustomerTagStyle('priority')).toEqual({ label: 'VIP', variant: 'vip' });
  });

  it('maps red_flag to Red Flag / red variant', () => {
    expect(getCustomerTagStyle('red_flag')).toEqual({ label: 'Red Flag', variant: 'red' });
  });

  it('maps slow_payer to Slow Payer / amber variant', () => {
    expect(getCustomerTagStyle('slow_payer')).toEqual({ label: 'Slow Payer', variant: 'amber' });
  });

  it('maps new_customer to New / prepaid variant', () => {
    expect(getCustomerTagStyle('new_customer')).toEqual({ label: 'New', variant: 'prepaid' });
  });

  it('falls back to neutral with title-cased label for unknown tags', () => {
    expect(getCustomerTagStyle('needs_ladder')).toEqual({
      label: 'Needs Ladder',
      variant: 'neutral',
    });
  });

  it('handles single-word unknown tags', () => {
    expect(getCustomerTagStyle('vip_customer')).toEqual({
      label: 'Vip Customer',
      variant: 'neutral',
    });
  });

  it('lowercases all-caps unknown tags then title-cases them', () => {
    expect(getCustomerTagStyle('HOA')).toEqual({ label: 'Hoa', variant: 'neutral' });
  });

  it('returns empty label for empty input', () => {
    expect(getCustomerTagStyle('')).toEqual({ label: '', variant: 'neutral' });
  });
});
