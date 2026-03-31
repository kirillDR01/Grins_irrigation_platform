# Issue: Premium Package Monthly Visit Count Mismatch

**Date discovered:** 2026-03-28
**Severity:** Low (cosmetic / business logic clarification)
**Affects:** Premium Residential and Premium Commercial tiers
**Status:** Needs business decision

---

## Summary

The public-facing service packages page advertises **"4 Monthly Monitoring Visits and Tune Ups"** for the Premium tier, but the job generator creates **5 monthly visits** (May through September).

---

## Details

| Source | What it says | Count |
|--------|-------------|-------|
| Landing page (grinsirrigation.com/service-packages) | "4 Monthly Monitoring Visits and Tune Ups" | 4 |
| Tier `included_services` in DB | "Monthly system check and adjustment (May-Sep)" | 5 (implied) |
| Onboarding success page | "Monthly system check and adjustment (May-Sep)" | 5 (implied) |
| Job generator (`_PREMIUM_JOBS`) | Monthly visits for May, Jun, Jul, Aug, Sep | 5 |
| Admin dashboard (AGR-2026-050) | "0 of 7 completed" | 7 total (1 spring + 5 monthly + 1 fall) |

---

## Root Cause

The job generator in `src/grins_platform/services/job_generator.py` (lines 34-42) creates monthly visits for all 5 months May through September:

```python
_PREMIUM_JOBS = [
    ("spring_startup", ..., 4, 4),      # April
    ("monthly_visit", ..., 5, 5),       # May
    ("monthly_visit", ..., 6, 6),       # June
    ("monthly_visit", ..., 7, 7),       # July
    ("monthly_visit", ..., 8, 8),       # August
    ("monthly_visit", ..., 9, 9),       # September
    ("fall_winterization", ..., 10, 10), # October
]
```

The landing page in the public frontend repo (`Grins_irrigation`) says "4 Monthly Monitoring Visits."

---

## Options

**Option A: Fix the landing page (if 5 visits is correct)**
- Change "4 Monthly Monitoring Visits" to "5 Monthly Monitoring Visits" on the service packages page
- No backend changes needed

**Option B: Fix the job generator (if 4 visits is correct)**
- Remove the May monthly visit from `_PREMIUM_JOBS` since the April spring startup already covers early-season
- Result: Spring (Apr) → Monthly (Jun, Jul, Aug, Sep) → Fall (Oct) = 6 total jobs
- The May visit is only ~2 weeks after the April spring startup, so it may be redundant

**Option C: Keep as-is (if "4" is marketing shorthand)**
- The "4 Monthly Monitoring Visits" could be intentional marketing simplification
- Customers actually get 5 monthly visits which exceeds expectations

---

## Decision Needed

Which count is the business intent — 4 or 5 monthly visits for Premium?
