import { describe, it, expect } from 'vitest';
import { getJobTypeColorClass } from './job-type-colors';

describe('getJobTypeColorClass', () => {
  it('maps spring_startup to spring', () => {
    expect(getJobTypeColorClass('spring_startup')).toBe('spring');
  });

  it('maps fall_winterization to fall', () => {
    expect(getJobTypeColorClass('fall_winterization')).toBe('fall');
  });

  it('maps mid_season_inspection to mid', () => {
    expect(getJobTypeColorClass('mid_season_inspection')).toBe('mid');
  });

  it('returns neutral for an unknown job type', () => {
    expect(getJobTypeColorClass('repair')).toBe('neutral');
    expect(getJobTypeColorClass('blowout')).toBe('neutral');
  });

  it('returns neutral for an empty string', () => {
    expect(getJobTypeColorClass('')).toBe('neutral');
  });

  it('returns neutral for a case-mismatched canonical key', () => {
    // Backend canonicalises to lowercase; case mismatches fall through.
    expect(getJobTypeColorClass('Spring_Startup')).toBe('neutral');
    expect(getJobTypeColorClass('SPRING_STARTUP')).toBe('neutral');
  });
});
