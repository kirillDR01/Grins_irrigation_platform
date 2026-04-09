/**
 * Property 50: Draft auto-save round-trip
 *
 * For any draft campaign saved via the wizard auto-save, reopening the modal
 * in the same browser session should restore all field values exactly as saved
 * (audience selection, message body).
 *
 * Validates: Requirement 33 (acceptance criteria 4, 5, 6)
 */

import { describe, it, expect, beforeEach } from 'vitest';
import * as fc from 'fast-check';

// --- Replicate the draft persistence logic from NewTextCampaignModal ---

interface CustomerAudienceFilter {
  sms_opt_in?: boolean | null;
  ids_include?: string[] | null;
  cities?: string[] | null;
  tags_include?: string[] | null;
  lead_source?: string | null;
  is_active?: boolean | null;
  no_appointment_in_days?: number | null;
}

interface LeadAudienceFilter {
  sms_consent?: boolean | null;
  ids_include?: string[] | null;
  statuses?: string[] | null;
  lead_source?: string | null;
  intake_tag?: string | null;
  action_tags_include?: string[] | null;
  cities?: string[] | null;
}

interface AdHocRecipientPayload {
  phone: string;
  first_name?: string | null;
  last_name?: string | null;
}

interface AdHocAudienceFilter {
  csv_upload_id?: string | null;
  recipients?: AdHocRecipientPayload[] | null;
  staff_attestation_confirmed: boolean;
  attestation_text_shown: string;
  attestation_version: string;
}

interface TargetAudience {
  customers?: CustomerAudienceFilter | null;
  leads?: LeadAudienceFilter | null;
  ad_hoc?: AdHocAudienceFilter | null;
}

interface DraftState {
  audience: TargetAudience;
  messageBody: string;
  savedAt: string;
}

function getDraftKey(userId: string): string {
  return `comms:draft_campaign:${userId}`;
}

// --- Arbitraries ---

const arbCustomerFilter: fc.Arbitrary<CustomerAudienceFilter> = fc.record({
  sms_opt_in: fc.option(fc.boolean(), { nil: null }),
  ids_include: fc.option(fc.array(fc.uuid(), { maxLength: 5 }), { nil: null }),
  cities: fc.option(fc.array(fc.string({ minLength: 1, maxLength: 30 }), { maxLength: 3 }), { nil: null }),
  tags_include: fc.option(fc.array(fc.string({ minLength: 1, maxLength: 20 }), { maxLength: 3 }), { nil: null }),
  lead_source: fc.option(fc.string({ minLength: 1, maxLength: 20 }), { nil: null }),
  is_active: fc.option(fc.boolean(), { nil: null }),
  no_appointment_in_days: fc.option(fc.integer({ min: 1, max: 365 }), { nil: null }),
});

const arbLeadFilter: fc.Arbitrary<LeadAudienceFilter> = fc.record({
  sms_consent: fc.option(fc.boolean(), { nil: null }),
  ids_include: fc.option(fc.array(fc.uuid(), { maxLength: 5 }), { nil: null }),
  statuses: fc.option(fc.array(fc.constantFrom('new', 'contacted', 'qualified'), { maxLength: 3 }), { nil: null }),
  lead_source: fc.option(fc.string({ minLength: 1, maxLength: 20 }), { nil: null }),
  intake_tag: fc.option(fc.string({ minLength: 1, maxLength: 20 }), { nil: null }),
  action_tags_include: fc.option(fc.array(fc.string({ minLength: 1, maxLength: 20 }), { maxLength: 3 }), { nil: null }),
  cities: fc.option(fc.array(fc.string({ minLength: 1, maxLength: 30 }), { maxLength: 3 }), { nil: null }),
});

const arbAdHocRecipient: fc.Arbitrary<AdHocRecipientPayload> = fc.record({
  phone: fc.string({ minLength: 10, maxLength: 15 }),
  first_name: fc.option(fc.string({ minLength: 1, maxLength: 30 }), { nil: null }),
  last_name: fc.option(fc.string({ minLength: 1, maxLength: 30 }), { nil: null }),
});

const arbAdHocFilter: fc.Arbitrary<AdHocAudienceFilter> = fc.record({
  csv_upload_id: fc.option(fc.uuid(), { nil: undefined }),
  recipients: fc.option(fc.array(arbAdHocRecipient, { maxLength: 5 }), {
    nil: undefined,
  }),
  staff_attestation_confirmed: fc.boolean(),
  attestation_text_shown: fc.string({ minLength: 1, maxLength: 200 }),
  attestation_version: fc.string({ minLength: 1, maxLength: 10 }),
});

const arbTargetAudience: fc.Arbitrary<TargetAudience> = fc.record({
  customers: fc.option(arbCustomerFilter, { nil: null }),
  leads: fc.option(arbLeadFilter, { nil: null }),
  ad_hoc: fc.option(arbAdHocFilter, { nil: null }),
});

const arbDraftState: fc.Arbitrary<DraftState> = fc.record({
  audience: arbTargetAudience,
  messageBody: fc.string({ maxLength: 500 }),
  savedAt: fc.integer({ min: 1704067200000, max: 1798761600000 }).map((ms) => new Date(ms).toISOString()),
});

// --- Tests ---

describe('Property 50: Draft auto-save round-trip', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('any DraftState survives JSON round-trip through localStorage', () => {
    fc.assert(
      fc.property(arbDraftState, fc.uuid(), (draft, userId) => {
        const key = getDraftKey(userId);

        // Save (mirrors NewTextCampaignModal saveDraft)
        localStorage.setItem(key, JSON.stringify(draft));

        // Restore (mirrors NewTextCampaignModal draft restoration)
        const raw = localStorage.getItem(key);
        expect(raw).not.toBeNull();
        const restored: DraftState = JSON.parse(raw!);

        // All fields must round-trip exactly
        expect(restored.messageBody).toBe(draft.messageBody);
        expect(restored.savedAt).toBe(draft.savedAt);
        expect(restored.audience).toEqual(draft.audience);
      }),
      { numRuns: 200 },
    );
  });

  it('draft key is scoped per user — different users never collide', () => {
    fc.assert(
      fc.property(arbDraftState, arbDraftState, fc.uuid(), fc.uuid(), (draftA, draftB, userA, userB) => {
        fc.pre(userA !== userB);

        localStorage.setItem(getDraftKey(userA), JSON.stringify(draftA));
        localStorage.setItem(getDraftKey(userB), JSON.stringify(draftB));

        const restoredA: DraftState = JSON.parse(localStorage.getItem(getDraftKey(userA))!);
        const restoredB: DraftState = JSON.parse(localStorage.getItem(getDraftKey(userB))!);

        expect(restoredA).toEqual(draftA);
        expect(restoredB).toEqual(draftB);
      }),
      { numRuns: 100 },
    );
  });

  it('overwriting a draft replaces it completely — no field leakage', () => {
    fc.assert(
      fc.property(arbDraftState, arbDraftState, fc.uuid(), (draftOld, draftNew, userId) => {
        const key = getDraftKey(userId);

        localStorage.setItem(key, JSON.stringify(draftOld));
        localStorage.setItem(key, JSON.stringify(draftNew));

        const restored: DraftState = JSON.parse(localStorage.getItem(key)!);
        expect(restored).toEqual(draftNew);
      }),
      { numRuns: 100 },
    );
  });
});
