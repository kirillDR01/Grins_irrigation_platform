import { describe, it, expect } from 'vitest';
import * as fc from 'fast-check';
import { nowContent, sanitizeCopy } from './nowContent';
import { statusToStageKey } from '../types/pipeline';
import type { SalesEntryStatus, StageKey, NowCardInputs } from '../types/pipeline';

// ─── helpers ────────────────────────────────────────────────────────────────

function baseInputs(stage: StageKey, overrides: Partial<NowCardInputs> = {}): NowCardInputs & { firstName: string } {
  return {
    stage,
    hasEstimateDoc: false,
    hasSignedAgreement: false,
    hasCustomerEmail: true,
    firstName: 'Alice',
    ...overrides,
  };
}

// ─── snapshot tests for each variation ──────────────────────────────────────

describe('nowContent', () => {
  it('schedule_estimate variation', () => {
    const result = nowContent(baseInputs('schedule_estimate'));
    expect(result).not.toBeNull();
    expect(result!.pill).toEqual({ tone: 'you', label: 'Your move' });
    expect(result!.title).toContain('Alice');
    expect(result!.actions.length).toBeGreaterThan(0);
    expect(result!.actions[0]).toMatchObject({ kind: 'primary', onClickId: 'schedule_visit' });
  });

  it('send_estimate — has email (Build & send CTA)', () => {
    // Structured-estimate landing: no PDF dropzone, no lockBanner —
    // primary action is "Build & send estimate", which opens the
    // line-item sheet.
    const result = nowContent(baseInputs('send_estimate', { hasCustomerEmail: true }));
    expect(result).not.toBeNull();
    expect(result!.dropzone).toBeUndefined();
    expect(result!.lockBanner).toBeUndefined();
    const sendAction = result!.actions.find(
      a => a.testId === 'now-action-build-send-estimate',
    );
    expect(sendAction?.kind).toBe('primary');
  });

  it('send_estimate — no email locks build action', () => {
    const result = nowContent(baseInputs('send_estimate', { hasCustomerEmail: false }));
    expect(result).not.toBeNull();
    const sendAction = result!.actions.find(
      a => a.testId === 'now-action-build-send-estimate',
    );
    expect(sendAction?.kind).toBe('locked');
    const addEmailAction = result!.actions.find(
      a => a.testId === 'now-action-add-email',
    );
    expect(addEmailAction?.kind).toBe('primary');
  });

  it('pending_approval variation', () => {
    const result = nowContent(baseInputs('pending_approval'));
    expect(result).not.toBeNull();
    expect(result!.pill).toEqual({ tone: 'cust', label: 'Waiting on customer' });
    expect(result!.showNudgeSchedule).toBe(true);
    expect(result!.title).toContain('Alice');
  });

  describe('pending_approval pause label', () => {
    it('shows "Pause auto-follow-up" when not paused', () => {
      const content = nowContent(
        baseInputs('pending_approval', { nudgesPaused: false }),
      );
      expect(
        content?.actions.some(
          (a) => 'label' in a && a.label === 'Pause auto-follow-up',
        ),
      ).toBe(true);
    });

    it('flips to "Resume auto-follow-up" when paused', () => {
      const content = nowContent(
        baseInputs('pending_approval', { nudgesPaused: true }),
      );
      expect(
        content?.actions.some(
          (a) => 'label' in a && a.label === 'Resume auto-follow-up',
        ),
      ).toBe(true);
    });
  });

  it('send_contract — no agreement (locked)', () => {
    const result = nowContent(baseInputs('send_contract', { hasSignedAgreement: false }));
    expect(result).not.toBeNull();
    expect(result!.dropzone).toEqual({ kind: 'agreement', filled: false });
    expect(result!.showWeekOfPicker).toBe(true);
    const convertAction = result!.actions.find(a => a.testId === 'now-action-convert');
    expect(convertAction?.kind).toBe('locked');
  });

  it('send_contract — agreement uploaded', () => {
    const result = nowContent(baseInputs('send_contract', { hasSignedAgreement: true }));
    expect(result).not.toBeNull();
    expect(result!.dropzone).toEqual({ kind: 'agreement', filled: true });
    const convertAction = result!.actions.find(a => a.testId === 'now-action-convert');
    expect(convertAction?.kind).toBe('primary');
  });

  it('closed_won variation', () => {
    const result = nowContent(baseInputs('closed_won'));
    expect(result).not.toBeNull();
    expect(result!.pill).toEqual({ tone: 'done', label: 'Complete' });
    expect(result!.actions.some(a => 'onClickId' in a && a.onClickId === 'view_job')).toBe(true);
  });

  it('returns null for closed_lost via statusToStageKey', () => {
    // closed_lost maps to null, so nowContent is not called with it
    expect(statusToStageKey('closed_lost')).toBeNull();
  });
});

// ─── statusToStageKey mapping tests ─────────────────────────────────────────

describe('statusToStageKey', () => {
  it('maps estimate_scheduled → schedule_estimate', () => {
    expect(statusToStageKey('estimate_scheduled')).toBe('schedule_estimate');
  });

  it('maps closed_lost → null', () => {
    expect(statusToStageKey('closed_lost')).toBeNull();
  });

  it('maps all other statuses to themselves', () => {
    const passthrough: SalesEntryStatus[] = [
      'schedule_estimate', 'send_estimate', 'pending_approval', 'send_contract', 'closed_won',
    ];
    for (const s of passthrough) {
      expect(statusToStageKey(s)).toBe(s);
    }
  });
});

// ─── sanitizeCopy tests ──────────────────────────────────────────────────────

describe('sanitizeCopy', () => {
  it('strips disallowed tags', () => {
    expect(sanitizeCopy('<script>alert(1)</script>hello')).toBe('alert(1)hello');
    expect(sanitizeCopy('<div><p>text</p></div>')).toBe('text');
  });

  it('preserves <em> and <b>', () => {
    expect(sanitizeCopy('<em>italic</em> and <b>bold</b>')).toBe('<em>italic</em> and <b>bold</b>');
  });

  it('strips mixed allowed/disallowed', () => {
    const result = sanitizeCopy('<span><em>keep</em></span>');
    expect(result).toBe('<em>keep</em>');
  });
});

// ─── Property 1: statusToStageKey Mapping Correctness ───────────────────────

describe('Property 1: statusToStageKey Mapping Correctness', () => {
  const ALL_STATUSES: SalesEntryStatus[] = [
    'schedule_estimate', 'estimate_scheduled', 'send_estimate',
    'pending_approval', 'send_contract', 'closed_won', 'closed_lost',
  ];

  it('maps correctly for all statuses (100+ iterations)', () => {
    fc.assert(
      fc.property(fc.constantFrom(...ALL_STATUSES), (status) => {
        const result = statusToStageKey(status);
        if (status === 'closed_lost') return result === null;
        if (status === 'estimate_scheduled') return result === 'schedule_estimate';
        return result === status;
      }),
      { numRuns: 100 },
    );
  });
});

// ─── Property 6: sanitizeCopy HTML Allowlist ─────────────────────────────────

describe('Property 6: sanitizeCopy HTML Allowlist', () => {
  it('output contains no disallowed HTML tags (100+ iterations)', () => {
    const tags = ['div', 'span', 'script', 'p', 'a', 'strong', 'i', 'ul', 'li', 'h1'];
    fc.assert(
      fc.property(
        fc.array(fc.constantFrom(...tags, 'em', 'b'), { minLength: 0, maxLength: 10 }),
        fc.string({ maxLength: 20 }),
        (tagList, text) => {
          const html = tagList.map(t => `<${t}>${text}</${t}>`).join('');
          const result = sanitizeCopy(html);
          // Must not contain any tag other than em/b
          const disallowedTagPattern = /<(?!\/?(?:em|b)\b)[^>]*>/i;
          return !disallowedTagPattern.test(result);
        },
      ),
      { numRuns: 100 },
    );
  });
});

// ─── Property 7: nowContent Output Structure ─────────────────────────────────

describe('Property 7: nowContent Output Structure', () => {
  const STAGES: StageKey[] = [
    'schedule_estimate', 'send_estimate', 'pending_approval', 'send_contract', 'closed_won',
  ];

  it('produces valid structure for all input combinations (100+ iterations)', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(...STAGES),
        fc.boolean(),
        fc.boolean(),
        fc.boolean(),
        fc.string({ minLength: 1, maxLength: 20 }),
        (stage, hasEstimateDoc, hasSignedAgreement, hasCustomerEmail, firstName) => {
          const inputs = { stage, hasEstimateDoc, hasSignedAgreement, hasCustomerEmail, firstName };
          const result = nowContent(inputs);

          // All non-null stages must return content
          if (result === null) return false;

          // pill tone matches expected
          const expectedTone: Record<StageKey, 'you' | 'cust' | 'done'> = {
            schedule_estimate: 'you',
            send_estimate: 'you',
            pending_approval: 'cust',
            send_contract: 'you',
            closed_won: 'done',
          };
          if (result.pill.tone !== expectedTone[stage]) return false;

          // title contains firstName for stages that use it.
          // closed_won uses jobId; send_estimate's title is now generic
          // ("Build the estimate and send it.") and no longer references
          // the customer name.
          const titleNeedsFirstName =
            stage !== 'closed_won' && stage !== 'send_estimate';
          if (titleNeedsFirstName && !result.title.includes(firstName)) return false;

          // actions is non-empty
          if (result.actions.length === 0) return false;

          // send_estimate has no PDF dropzone or lockBanner after the
          // structured-estimate landing — both must be absent regardless
          // of hasEstimateDoc.
          if (stage === 'send_estimate') {
            if (result.lockBanner) return false;
            if (result.dropzone) return false;
          }

          // send_contract without agreement has locked convert action
          if (stage === 'send_contract' && !hasSignedAgreement) {
            const convertAction = result.actions.find(a => a.testId === 'now-action-convert');
            if (!convertAction || convertAction.kind !== 'locked') return false;
          }

          // determinism — identical inputs produce deeply equal results
          const result2 = nowContent(inputs);
          return JSON.stringify(result) === JSON.stringify(result2);
        },
      ),
      { numRuns: 100 },
    );
  });
});
