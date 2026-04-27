# 99 — Consolidated clarification questions

All the ❓ items from the per-feature docs, gathered here so you can answer in one pass.
Answering these unblocks the corresponding TODOs.

---

## 01 — Customer tags → jobs
1. **Cascade scope on edit:** when tags are edited from the appointment modal, should the update hit only `TO_BE_SCHEDULED` future jobs, also `SCHEDULED`/`IN_PROGRESS`, or historical jobs too?
2. **Job-specific tags:** can a job hold tags beyond the customer's set, or must it mirror the customer exactly?
3. **Tag deletion:** when a customer tag is removed, should it disappear from historical jobs or stay as audit?

## 02 — Job "week of" editability after scheduling
4. Option A: keep the lock (user unschedules first). Option B: allow edit, auto-handle the attached appointment. Option C: allow edit with a required reason. Which do you want? If B/C, what should happen to the existing scheduled appointment?

## 03 — Staff auth and session
5. Separate per-staff logins with RBAC (infrastructure is 80% in place) **vs** everyone is admin and toggles views. Your preference?
6. Is "~1 week re-login" literal 7 days, or whatever makes "every Monday 8am" work?
7. How should new staff get their first password — admin-set + SMS/email, or magic-link invite?

## 04 — Lead → customer lifecycle
8. **Auto-convert on SignWell signature**, or require admin to click "Convert" after reviewing?
9. **Estimate builder**: is the in-app flow sufficient, or are you still drafting in Google Sheets and just logging the sent date?
10. Follow-up cadence: keep current Day 3/7/14/21, or strict weekly (7/14/21/28…) as you described?

## 05 — Node 4 document carry-over
11. On conversion, move docs (remove from lead), copy (both), or re-link (customer owns, lead keeps reference)?
12. Which document types qualify — estimate, contract, inspection photos, notes, waivers? Confirm scope.
13. If a conversion is reversed, what happens to the migrated docs?

## 06 — On-site payment collection
14. Should every on-site collection also create an `Invoice` row (keeps #08 as source of truth)? Recommend: yes.
15. Customer gets an auto-receipt SMS/email after payment?
16. Which Stripe Terminal reader model (WisePOS, Tap to Pay on iPhone, …)?

## 07 — Estimate button + auto-job on approval
17. SMS copy OK as plain: `Estimate from Grins: ... Reply YES or view: <link>`?
18. Does an approved estimate need a formal SignWell signature before becoming a job, or is "Yes" click enough?
19. After approval, can an estimate be edited and re-issued, or is it locked?

## 08 — Invoices tab reminders + 3% fee + 2-wk due
20. **"1.5 weeks"** — from send date or from due date?
21. Do you want a formal cadence research writeup, or ship a sensible default (10d after send + day-before-due + weekly past-due) and iterate?
22. 3% surcharge disclosure — show to customer at checkout (recommended, may be required by card-brand rules) or add silently?
23. Follow-up toggle: global only, or per-invoice opt-out too?

## 09 — Admin price list UI
24. Location: own "Settings → Price List" top-level tab, or under existing settings?
25. Grouped by category or flat searchable list?
26. When a price is edited/archived, do existing estimates and invoices retain the old value? (Recommend: yes, snapshot at issue time.)
27. Deprecate `pricelist.md` after launch, or auto-render from DB?

## 10 — Multi-staff calendar overlay
28. Scope of "staff" in the filter — include crews and sales as well? (Sounds like yes — confirm.)
29. Default-on-login: admin sees everyone, tech sees only themselves?
30. Flat alphabetical or grouped by role?

## 11 — Next-customer ETA
31. Trigger style: manual "Send ETA to next" button vs automatic on status change? Recommend manual for v1.
32. Rough `+30 min` first, or real Google Maps drive-time from day one?
33. Confirm message copy (draft in 11.md).

## 12 — Directions picker
34. Auto-default by device (iOS→Apple, others→Google) or keep always-picker?

---

## General
35. Priority / sequencing — which Tier A item do you want shipped first? My recommendation: #01 (tags to jobs) + #05 (doc carry-over) + #10 (multi-staff overlay) in parallel — all are low-risk and high-value.
