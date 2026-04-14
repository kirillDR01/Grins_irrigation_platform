# Path H — November onboarding year rollover (M-4)

Verifies Sprint 7 M-4: when a service agreement is onboarded past the month
for a seasonal job, `JobGenerator._resolve_dates` rolls the year forward.

## Why not a live test

Simulating a specific "current month" via a live agreement means
time-travelling the dev container — not worth the effort. Instead, call
`_resolve_dates` directly from a local shell.

## Live-checkable via Python shell

```bash
cd "/Users/kirillrakitin/Grins_irrigation_platform"
uv run python -c "
from datetime import date
from grins_platform.services.job_generator import JobGenerator

# November 2026 → Spring Startup (month 4) should roll to 2027.
s, e = JobGenerator._resolve_dates('spring_startup', 4, 4, 2026, {}, current_month=11)
assert s == date(2027, 4, 1), f'got {s}'
print('✅ November → Spring 2027')

# March 2026 → same month = April 2026 (no rollover)
s, e = JobGenerator._resolve_dates('spring_startup', 4, 4, 2026, {}, current_month=3)
assert s == date(2026, 4, 1), f'got {s}'
print('✅ March → Spring 2026')

# Same month edge
s, e = JobGenerator._resolve_dates('spring_startup', 4, 4, 2026, {}, current_month=4)
assert s == date(2026, 4, 1), f'got {s}'
print('✅ April → Spring 2026')

# Fall Winterization (month 10) in November → 2027
s, e = JobGenerator._resolve_dates('fall_winterization', 10, 10, 2026, {}, current_month=11)
assert s == date(2027, 10, 1), f'got {s}'
print('✅ November → Fall Winterization 2027')
"
```

All four assertions must pass. Zero stdout on failure = the fix regressed.

## Acceptance

- [ ] All four assertions above print ✅.
