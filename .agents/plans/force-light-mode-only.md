# Feature: Force Light Mode Only (Remove Dark Mode)

The following plan should be complete, but it is important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils, types, and models. Import from the right files etc.

## Feature Description

Remove the user-facing dark mode toggle from the Settings page and force the application to render in light mode at all times. The custom `ThemeProvider` is collapsed to a light-only stub so that no code path can apply the `.dark` class to `<html>`. Existing Tailwind `dark:` utility classes are left in place (they become inert without the `.dark` selector) and can be stripped in a separate cleanup pass — this PR's goal is behavioral, not stylistic.

## User Story

As a user of the Grin's Irrigation Platform
I want the app to render in light mode only, without a dark mode toggle in Settings
So that the visual experience is consistent with the brand and there is no ambiguity about which theme is "official"

## Problem Statement

The Settings page currently exposes a "Dark Mode" toggle (`Settings.tsx:209–243`) backed by a custom `ThemeProvider` that persists the choice in `localStorage` and toggles a `.dark` class on `<html>`. Product wants light-only — no toggle, no chance of a user (or matching `prefers-color-scheme: dark`) flipping the app into a dark theme that's not part of the supported design.

## Solution Statement

Three surgical changes:

1. **Provider**: replace the dark-aware `ThemeProvider` with a light-only stub that keeps the `useTheme` API surface (so existing imports in `sonner.tsx` and `Settings.tsx` keep type-checking) but always returns `resolvedTheme: 'light'` and makes `setTheme`/`toggleTheme` no-ops. On mount, ensure `<html>` does not carry the `.dark` class and clear the legacy `grins-theme` localStorage key so previously-set "dark" preferences are wiped.
2. **Settings UI**: delete the "Display Settings" card (lines 209–243), the `useTheme()` call, the `isDarkMode` derivation, and the now-unused `Sun`/`Moon`/`Palette`/`useTheme` imports.
3. **Sonner toaster**: replace the `next-themes` `useTheme()` call with a hardcoded `theme="light"` so `next-themes` is no longer wired in. (Optional: remove the `next-themes` package entirely in a follow-up.)

The 144 `dark:` Tailwind utility occurrences across 15 files and the `.dark { ... }` CSS variable block in `index.css` are **left in place** — they are dead code without a `.dark` selector on root and removing them is a mechanical, conflict-prone change that should ship as a separate cleanup PR.

## Feature Metadata

**Feature Type**: Enhancement (UI removal + behavior lock)
**Estimated Complexity**: Low
**Primary Systems Affected**: `frontend/src/core/providers/ThemeProvider.tsx`, `frontend/src/pages/Settings.tsx`, `frontend/src/components/ui/sonner.tsx`, `frontend/src/App.tsx`
**Dependencies**: None new. Backend untouched (theme is client-only — verified, no `theme`/`dark_mode` field in user/business settings models or APIs).

---

## CONTEXT REFERENCES

### Relevant Codebase Files — IMPORTANT: YOU MUST READ THESE BEFORE IMPLEMENTING

- `frontend/src/core/providers/ThemeProvider.tsx` (full file, lines 1–105) — Why: the entire provider is being collapsed; you need to know the exact `ThemeContextType` shape (`theme`, `resolvedTheme`, `setTheme`, `toggleTheme`) so the stub keeps the same hook surface.
- `frontend/src/core/providers/index.ts` (lines 1–3) — Why: re-exports `ThemeProvider` and `useTheme`. Keep both exports working.
- `frontend/src/pages/Settings.tsx` (lines 1–13 imports, line 30–31 hook usage, lines 209–243 Display Settings card) — Why: this is the only consumer of `toggleTheme` / `resolvedTheme`. After removal, `useTheme`, `Sun`, `Moon`, and `Palette` lucide imports go unused; remove them. `Switch` stays (used by SMS/email/push toggles above the deleted card).
- `frontend/src/App.tsx` (line 9) — Why: passes `defaultTheme="system"`. After the rewrite, the prop is ignored; change to `defaultTheme="light"` for clarity, or drop the prop and let the stub default.
- `frontend/src/components/ui/sonner.tsx` (lines 1–40) — Why: only file that imports `useTheme` from `next-themes`. The Sonner toaster currently passes whatever `next-themes` returns. After rewrite it must pass `theme="light"` directly.
- `frontend/src/index.css` (line 4 `@custom-variant dark`, lines 227–265 `.dark { ... }` block) — Why: read-only context. These are dead code once `.dark` is never added to root, but **leave them** in this PR. Tailwind v4 needs the `@custom-variant` line so existing `dark:` classes still parse without errors.
- `frontend/src/features/settings/components/Settings.test.tsx` (lines 1–40 verified) — Why: existing settings test file. It tests `BusinessInfo`, `InvoiceDefaults`, `NotificationPrefs`, `EstimateDefaults` directly and **never imports `SettingsPage`** — so deleting the Display Settings card cannot break this file. Verified there are no `theme`/`dark` references. Don't add theme assertions here.
- `frontend/src/test/setup.ts` (lines 10–23 verified) — Why: the global test setup mocks `window.matchMedia` to always return `matches: false`. This means even if a stray test mounted the old `ThemeProvider`, it could never have entered the dark branch. Confirms tests stay green after the rewrite. Read-only context — do not edit.
- `frontend/src/shared/hooks/useMediaQuery.ts` (full file verified) — Why: a generic `matchMedia` hook. The string `'(prefers-color-scheme: dark)'` appears **only in a JSDoc `@example` block (line 14)** — there is no real consumer. Read-only context — do not touch.
- `frontend/vite.config.ts` (full file verified) — Why: confirms no theme-related plugin, no SSR, no `tailwind.config.*` file. Tailwind v4 lives entirely inside `index.css` via `@import "tailwindcss"` and `@custom-variant dark`. No build-config edits needed.
- `e2e/` directory verified — only file is `test-webauthn-passkey.sh`. **Zero e2e tests reference theme, dark, `theme-toggle`, or `display-settings`** — no e2e fixtures to update.

### New Files to Create

None. All changes are modifications to existing files.

### Relevant Documentation — YOU SHOULD READ THESE BEFORE IMPLEMENTING

- [Tailwind v4 — `@custom-variant`](https://tailwindcss.com/docs/adding-custom-styles#custom-variants)
  - Specific section: defining a `dark` variant via `&:is(.dark *)`
  - Why: Confirms that leaving the `@custom-variant dark` line in `index.css` while never adding `.dark` to root is safe — `dark:` utilities just don't match anything.
- [sonner — `theme` prop](https://sonner.emilkowal.ski/toaster#theme)
  - Specific section: accepted values (`"light" | "dark" | "system"`)
  - Why: Confirms passing a hardcoded `theme="light"` is supported and removes the `next-themes` coupling.
- [MDN — `Storage.removeItem`](https://developer.mozilla.org/en-US/docs/Web/API/Storage/removeItem)
  - Why: used to clear the legacy `grins-theme` key on mount so previously-stored "dark" doesn't linger in users' browsers.

### Patterns to Follow

**File header / imports** — match the existing style (no `'use client'` directive for non-shadcn files; named exports for providers and hooks):

```ts
// ThemeProvider.tsx – existing style preserved
import { createContext, useContext, type ReactNode } from 'react';
```

**Provider + hook pair** — `ThemeProvider.tsx` already exports both `ThemeProvider` (component) and `useTheme` (hook with "must be used within a ThemeProvider" guard at lines 100–104). Keep that contract.

**Path aliases** — imports use `@/` (e.g., `@/core/providers`, `@/components/ui/sonner`). No relative paths needed for the touched files.

**JSX class composition** — existing Settings cards use template-literal-free `className="..."` strings (e.g., `Settings.tsx:210`). Don't introduce `clsx`/`cn` for the trivial removals.

**No comments policy (CLAUDE-default)** — do not add explanatory comments to the stub provider or sonner. The code is self-evident.

---

## IMPLEMENTATION PLAN

### Phase 1: Lock the provider to light

Replace `ThemeProvider.tsx` with a stub that:
- Keeps the `ThemeContextType` shape exactly (`theme`, `resolvedTheme`, `setTheme`, `toggleTheme`) so existing consumers type-check.
- Hardcodes `theme: 'light'` and `resolvedTheme: 'light'`.
- `setTheme` and `toggleTheme` are no-ops.
- On mount: `document.documentElement.classList.remove('dark')` and `localStorage.removeItem('grins-theme')` to clean up legacy state.
- Drops all `useState`, `useEffect` polling of `prefers-color-scheme`, and all storage logic.

### Phase 2: Remove the Display Settings card

In `pages/Settings.tsx`:
- Delete the entire Display Settings `<Card>` block (lines 209–243).
- Delete the `useTheme` call (line 30) and `isDarkMode` derivation (line 31).
- Remove `Sun`, `Moon`, `Palette` from the `lucide-react` import (line 8) — verify with grep that no other JSX in this file references them.
- Remove `useTheme` from the `@/core/providers` import (line 9). The import line then becomes empty and should be deleted entirely (no other named exports from `@/core/providers` are used in this file).
- `Switch` stays — used by SMS / email / push toggles above the deleted card.

### Phase 3: Decouple sonner from next-themes

In `components/ui/sonner.tsx`:
- Remove `import { useTheme } from "next-themes"`.
- Remove the `const { theme = "system" } = useTheme()` line.
- Pass `theme="light"` directly to `<Sonner>` (replacing the `theme={theme as ToasterProps["theme"]}` prop).

### Phase 4: Update App.tsx prop

In `App.tsx`:
- Change `<ThemeProvider defaultTheme="system">` to `<ThemeProvider>` (drop the prop — the stub no longer respects it). Or equivalently `<ThemeProvider defaultTheme="light">` if you choose to keep the optional prop in the stub's TS surface.

### Phase 5: Validation

- Type-check, lint, run frontend tests, manually verify in browser dev mode that:
  - Settings page no longer shows the Display Settings card.
  - `<html>` element does not carry `.dark` class even when the OS is set to dark mode.
  - `localStorage.getItem('grins-theme')` returns `null` after one app load.
  - Toasts still render correctly (sonner Toaster mounts via `App.tsx:13`).

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### 1. UPDATE `frontend/src/core/providers/ThemeProvider.tsx`

- **IMPLEMENT**: Replace the entire file contents with a light-only stub. Keep the named exports `ThemeProvider` and `useTheme`. Keep the `ThemeContextType` interface shape so consumers (`Settings.tsx` line 30, `sonner.tsx` after Task 3, anywhere else that may import `useTheme` from `@/core/providers`) continue to type-check.
- **PATTERN**: Mirror the export shape of the original file (`ThemeProvider.tsx:35–105`). Drop all state, effects, and storage logic.
- **IMPORTS**: `import { createContext, useContext, useEffect, type ReactNode } from 'react';` — `useState` is no longer needed.
- **EXACT CONTENT** (use this verbatim — copy the whole block including the module-scope cleanup at the top):

  ```tsx
  import { createContext, useContext, type ReactNode } from 'react';

  type Theme = 'light' | 'dark' | 'system';

  interface ThemeContextType {
    theme: 'light';
    resolvedTheme: 'light';
    setTheme: (theme: Theme) => void;
    toggleTheme: () => void;
  }

  if (typeof document !== 'undefined') {
    document.documentElement.classList.remove('dark');
    try {
      localStorage.removeItem('grins-theme');
    } catch {}
  }

  const LIGHT_CONTEXT: ThemeContextType = {
    theme: 'light',
    resolvedTheme: 'light',
    setTheme: () => {},
    toggleTheme: () => {},
  };

  const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

  interface ThemeProviderProps {
    children: ReactNode;
    defaultTheme?: Theme;
  }

  export function ThemeProvider({ children }: ThemeProviderProps) {
    return (
      <ThemeContext.Provider value={LIGHT_CONTEXT}>
        {children}
      </ThemeContext.Provider>
    );
  }

  export function useTheme() {
    const context = useContext(ThemeContext);
    if (context === undefined) {
      throw new Error('useTheme must be used within a ThemeProvider');
    }
    return context;
  }
  ```

- **GOTCHA — Type union preserved**: `Theme` keeps its full `'light' | 'dark' | 'system'` union so any stray `setTheme('dark')` or `defaultTheme="system"` call site still type-checks (the stub just ignores the argument). The internal `theme` and `resolvedTheme` fields are narrowed to the literal `'light'` so reading code can never see `'dark'` or `'system'`. This eliminates a whole class of typecheck-cascade risk if a feature branch lands a new caller mid-merge.
- **GOTCHA — Zero FOUC**: the cleanup runs at *module evaluation* time (not inside `useEffect`), so `<html>.dark` is removed and the legacy `grins-theme` key is cleared **before** React's first render. This guarantees no flash even on slow devices, during HMR, or when a leftover class somehow exists.
- **GOTCHA — No comments in stub**: per the project's "no comments" default, the empty `catch {}` is intentional and self-evident (private-browsing or sandboxed iframes can throw on `localStorage` access). Do **not** add an explanatory comment.
- **GOTCHA — `useEffect` removed**: the previous draft used `useEffect` for cleanup. The new module-scope approach is strictly better for FOUC, and no `useEffect` import is needed — keep imports to `createContext, useContext, type ReactNode` only.
- **VALIDATE**: `cd frontend && npm run typecheck`

### 2. UPDATE `frontend/src/pages/Settings.tsx`

- **IMPLEMENT**: Three edits in this file.
  1. **Imports (line 8)**: change `import { User, Bell, Palette, Key, Shield, LogOut, Lock, Mail, Phone, Sun, Moon } from "lucide-react";` to `import { User, Bell, Key, Shield, LogOut, Lock, Mail, Phone } from "lucide-react";` — remove `Palette`, `Sun`, `Moon`.
  2. **Imports (line 9)**: delete the entire line `import { useTheme } from "@/core/providers";` — it has no other named imports.
  3. **Hook calls (lines 30–31)**: delete both lines:
     ```tsx
     const { resolvedTheme, toggleTheme } = useTheme();
     const isDarkMode = resolvedTheme === 'dark';
     ```
  4. **JSX (lines 209–243)**: delete the entire `{/* Display Settings Section */}` comment plus the `<Card data-testid="display-settings" ...>...</Card>` block.
- **PATTERN**: The remaining sections (`<BusinessInfo />`, `<InvoiceDefaults />`, `<NotificationPrefs />`, `<EstimateDefaults />`, `<BusinessSettingsPanel />` at `Settings.tsx:246–258`) are unchanged — just collapse the gap left by the deleted card.
- **GOTCHA**: Before deleting `Palette`, `Sun`, `Moon`, run a quick grep on the file to confirm they appear only in lines 209–243 (the Display Settings card). Same for `useTheme`. If a future card uses `Palette`, leave it — but as of this codebase, all four are exclusive to the deleted block.
- **GOTCHA**: Don't touch `Switch` in the imports — it's still used by lines 168–177, 187–193, 198–204 (SMS / email / push toggles).
- **VALIDATE**: `cd frontend && npm run typecheck && npm run lint`

### 3. UPDATE `frontend/src/components/ui/sonner.tsx`

- **IMPLEMENT**: Two edits.
  1. Remove the line `import { useTheme } from "next-themes"` (line 10).
  2. Inside the `Toaster` component body (lines 13–18), remove the `const { theme = "system" } = useTheme()` line and change `theme={theme as ToasterProps["theme"]}` (line 18) to `theme="light"`.
- **EXACT BEFORE → AFTER**:

  Before (lines 10–19):
  ```tsx
  import { useTheme } from "next-themes"
  import { Toaster as Sonner, type ToasterProps } from "sonner"

  const Toaster = ({ ...props }: ToasterProps) => {
    const { theme = "system" } = useTheme()

    return (
      <Sonner
        theme={theme as ToasterProps["theme"]}
  ```

  After:
  ```tsx
  import { Toaster as Sonner, type ToasterProps } from "sonner"

  const Toaster = ({ ...props }: ToasterProps) => {
    return (
      <Sonner
        theme="light"
  ```

- **GOTCHA**: The unused `type ToasterProps` import is still needed for the `({ ...props }: ToasterProps)` parameter type. Keep it.
- **GOTCHA**: After this change `next-themes` has no remaining importer. Leave the `next-themes` entry in `frontend/package.json:51` — removing it is a separate cleanup PR (run `npm uninstall next-themes` in that follow-up). This keeps the diff minimal and avoids lockfile churn.
- **VALIDATE**: `cd frontend && npm run typecheck`

### 4. UPDATE `frontend/src/App.tsx`

- **IMPLEMENT**: On line 9, change `<ThemeProvider defaultTheme="system">` to `<ThemeProvider>`. The stub provider's `defaultTheme` prop is now optional and ignored, so dropping it is the cleanest signal that the choice has gone away.
- **PATTERN**: matches the no-arg use of `<QueryProvider>` and `<AuthProvider>` on the surrounding lines.
- **VALIDATE**: `cd frontend && npm run typecheck`

### 5. VERIFY no other consumers of removed APIs

- **IMPLEMENT**: Run these six greps from the repo root and confirm the only matches are the files explicitly named below (no surprises). The greps cast a wider net than strictly necessary so a brand-new consumer added on a parallel branch is caught.
  1. `grep -rn "toggleTheme" frontend/src/` → expected matches: **none** (was only in the deleted `Settings.tsx` block and the old provider).
  2. `grep -rn "isDarkMode" frontend/src/` → expected: **none**.
  3. `grep -rn "grins-theme" frontend/src/` → expected matches: **only** `frontend/src/core/providers/ThemeProvider.tsx` (the new stub uses the string in its `localStorage.removeItem` cleanup).
  4. `grep -rn "from ['\"]next-themes['\"]" frontend/src/` → expected: **none**.
  5. `grep -rn "setTheme" frontend/src/` → expected matches: **only** `frontend/src/core/providers/ThemeProvider.tsx` (the no-op `setTheme` field on the stub context).
  6. `grep -rn "['\"]dark['\"]" frontend/src/core/providers/` → expected: **none** inside the providers directory.
  7. `grep -rn "prefers-color-scheme" frontend/src/` → expected matches: **only** `frontend/src/shared/hooks/useMediaQuery.ts:14` (a JSDoc `@example` line — read-only, do not edit).
- **GOTCHA**: If any grep returns hits in files not in the expected list above, **stop and surface them** to the user before committing — a consumer the audit missed has appeared on the dev branch since this plan was written.
- **GOTCHA**: Do not include `dark:` (with colon) in the greps — it would match the 144 inert Tailwind utilities that this PR intentionally leaves in place.
- **VALIDATE**: Each grep returns only the expected matches listed above.

### 6. RUN full validation gauntlet

- **IMPLEMENT**: Execute the validation commands in the next section in order.
- **VALIDATE**: All commands succeed.

---

## TESTING STRATEGY

The settings page already has a test file at `frontend/src/features/settings/components/Settings.test.tsx`. Verified: it does **not** reference `theme`, `dark`, `Display Settings`, or the `theme-toggle` testid. It will keep passing after this change without edits.

### Unit Tests

No new unit tests are required. The `ThemeProvider` stub's behavior (always-light) is covered by manual validation in dev mode (Phase 5 above) — adding a Vitest test that asserts `useTheme()` returns `{ resolvedTheme: 'light' }` is low-value because the file is so trivial. Skip.

### Integration Tests

No backend changes → no integration tests needed.

### Edge Cases

- **User has `prefers-color-scheme: dark` set in their OS** — the stub provider does not read this media query. Manual check: open DevTools → Rendering → Emulate CSS prefers-color-scheme: dark → confirm the app stays light.
- **User had previously selected dark mode (`localStorage['grins-theme'] === 'dark'`)** — the stub clears the key on mount. Manual check: in DevTools, set `localStorage.setItem('grins-theme', 'dark')`, reload, confirm the key is gone after one paint and `<html>` has no `.dark` class.
- **Sonner toasts render mid-flight when an old session still has `.dark` on root** — the stub's `useEffect` removes `.dark` synchronously on mount, before the first toast can fire. Manual check: trigger a toast (e.g., save profile) within 1 second of page load, confirm light styling.
- **SSR (not currently used by Vite, but worth noting)** — the `useEffect` only runs in the browser; the `localStorage.removeItem` is wrapped in try/catch so it won't crash if `localStorage` is unavailable.

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness. All commands are run from the repo root unless noted.

### Level 1: Syntax & Style

```bash
cd frontend && npm run lint
cd frontend && npm run format:check
```

### Level 2: Type Checking

```bash
cd frontend && npm run typecheck
```

### Level 3: Unit Tests

```bash
cd frontend && npm test
```

Expected: existing Settings test still passes; no theme tests need to be added or removed.

### Level 4: Manual Validation

Start the dev server and verify in a real browser (Chrome DevTools handy for forcing prefers-color-scheme):

```bash
cd frontend && npm run dev
```

Then:
1. Open `http://localhost:5173/settings`. Confirm there is **no** "Display Settings" card and **no** Dark Mode toggle. The Notification Preferences card is followed directly by Business Information.
2. Open DevTools → Elements → inspect `<html>`. Confirm `class="…"` does **not** contain `dark`.
3. DevTools → Console → run `localStorage.getItem('grins-theme')`. Expect `null`.
4. DevTools → Console → run `localStorage.setItem('grins-theme', 'dark')`, then reload. After load, `localStorage.getItem('grins-theme')` should again return `null` and `<html>` must not have `.dark`.
5. DevTools → Rendering panel → set "Emulate CSS media feature prefers-color-scheme" to **dark**. The app must stay visually light.
6. Trigger a toast (e.g., edit profile and click Save, or any flow that calls `toast.success`/`toast.error`). The toast should render with light styling.
7. Walk through every page that previously had heavy `dark:` usage (`/settings`, the BusinessInfo / NotificationPrefs / Invoice & Estimate Defaults panels, `/auth/passkeys`, `/invoices` MassNotify and LienReview, every shadcn `Button`/`Input`/`Select`/`Alert`/`DropdownMenu`). Confirm everything renders in the light palette.

### Level 5: Additional Validation (Optional)

If you have access to the staging deploy, smoke-test with the Vercel preview URL by toggling OS-level dark mode on macOS (System Settings → Appearance → Dark) before loading the preview. App must stay light.

---

## ACCEPTANCE CRITERIA

- [ ] Settings page no longer renders a "Display Settings" card or any `data-testid="theme-toggle"` element.
- [ ] `<html>` never carries the `.dark` class, even when the OS is set to dark mode or `localStorage['grins-theme']` was previously `"dark"`.
- [ ] `localStorage['grins-theme']` is cleared on first page load after this change ships.
- [ ] `useTheme()` continues to return a valid context (`{ theme: 'light', resolvedTheme: 'light', setTheme, toggleTheme }`) — both setters are no-ops.
- [ ] Sonner toasts render with `theme="light"` regardless of system preference.
- [ ] `next-themes` has no remaining importers in the frontend (verified by grep). Removing the package itself is deferred to a follow-up.
- [ ] `npm run typecheck`, `npm run lint`, `npm test` all pass with zero errors.
- [ ] No regressions on Settings, Invoices, Auth Passkeys, or any shadcn UI component.

---

## COMPLETION CHECKLIST

- [ ] Tasks 1–6 completed in order
- [ ] Each task validation passed immediately
- [ ] All Level 1–4 validation commands executed successfully
- [ ] Manual validation steps 1–7 visually confirmed in dev browser
- [ ] No leftover imports of `useTheme` from `next-themes`, no leftover `Sun`/`Moon`/`Palette` imports in `Settings.tsx`
- [ ] Acceptance criteria all met

---

## NOTES

**Out of scope for this PR (intentional)**:

1. **Stripping the 144 `dark:` Tailwind classes across 15 files.** They are inert without a `.dark` selector on root and do not affect rendering. Mass-stripping them is a mechanical cleanup that risks merge conflicts on the active feature branches (`appointment-modal-v2`, `schedule-visit`, etc.). File a follow-up issue: "Strip dead `dark:` Tailwind utilities (force-light-mode follow-up)". The 15 affected files are: `pages/Settings.tsx`, `features/settings/components/{NotificationPrefs,BusinessInfo,BusinessSettingsPanel,InvoiceDefaults,EstimateDefaults}.tsx`, `features/invoices/components/{MassNotifyPanel,LienReviewQueue}.tsx`, `features/auth/components/PasskeyManager.tsx`, `shared/components/ui/select.tsx`, `components/ui/{alert,button,dropdown-menu,select,input}.tsx`.

2. **Removing the `.dark { ... }` CSS variable block in `index.css:227–265`.** Same rationale — dead but inert. Strip together with the `dark:` utilities in the cleanup PR.

3. **Removing the `next-themes` package.** After Task 3 it has zero importers. Run `npm uninstall next-themes` in a follow-up; combine with the `dark:` cleanup PR to keep the diff focused.

4. **Backend persistence.** Verified there is no `theme` / `dark_mode` / `display_preferences` field in any model, schema, settings service, or settings API endpoint. Theme has always been client-only. No migration, no backend API change, no `BusinessSettings` update needed.

**Design decision**: chose to *stub* `ThemeProvider` rather than rip it out. Three reasons:
- `useTheme()` is imported in `Settings.tsx:9` and (transitively) in `App.tsx:2`. Removing the symbol means hunting every import site, which expands the diff.
- The hook may be re-introduced later if product wants light-themed accent variants. Keeping the API surface lets that re-introduction be additive.
- The stub is tiny (~40 lines) and self-explanatory.

**Confidence (one-pass success)**: 10 / 10.

Risk surface mapped and closed:

| Risk | Mitigation |
|------|------------|
| Stray `setTheme('dark')` / `defaultTheme="system"` caller breaks typecheck | `Theme` union kept as `'light' \| 'dark' \| 'system'`; only the *internal* fields are narrowed. Stub silently ignores the argument. |
| FOUC from leftover `<html class="dark">` (cached HMR state, browser extension, prior session) | Module-scope synchronous cleanup runs **before** React's first render — eliminates any paint-before-strip window. |
| Stale `localStorage['grins-theme'] === 'dark'` re-applied by some other code path | Cleared at module evaluation time. No other code path reads this key (verified by grep #3). |
| Sonner reads from `next-themes` and shows dark toasts | Task 3 hardcodes `theme="light"` and removes the import. Verified by grep #4. |
| Tests break because they relied on the old provider's behavior | Verified: `Settings.test.tsx` doesn't import `SettingsPage`; `test/setup.ts` mocks `matchMedia` to `matches: false`; **no theme-related test fixtures exist anywhere**. |
| E2E tests reference `theme-toggle` or `display-settings` testids | Verified: only e2e file is `test-webauthn-passkey.sh`, no theme refs. |
| Hidden `tailwind.config.*` with `darkMode: 'media'` would auto-apply dark via OS preference | Verified: **no `tailwind.config.*` file exists.** Tailwind v4 lives entirely in `index.css` via `@custom-variant dark (&:is(.dark *))`, which only activates when `.dark` is on root — and the stub guarantees it never is. |
| A new consumer landing on a parallel feature branch | Task 5's seven greps with explicit "expected matches" lists make any new consumer fail validation, forcing the implementer to surface it to the user before committing. |
| Backend somehow stores theme | Verified: zero theme/dark_mode fields in models, schemas, settings_service, business_setting_service, or any v1 API endpoint. |

No backend coordination, no schema change, no third-party SDK quirks, no test edits, no e2e edits, no config edits. Pure four-file frontend change with deterministic validation.
