# Requirements Document

## Introduction

This document specifies the requirements for the **Combined Appointment Modal** — a complete redesign of the `AppointmentDetail` component that opens when staff tap an appointment in the scheduling calendar. The new modal consolidates the entire on-site workflow into a single, high-fidelity interface: a 4-step visual timeline, large action-track cards for status progression, customer tags management, a maps-app picker for directions, payment collection, estimate creation, and all existing appointment operations (edit, cancel, no-show, communication timeline, reschedule handling). The redesign replaces the existing `AppointmentDetail.tsx` while preserving every piece of existing functionality.

## Glossary

- **Modal**: The `AppointmentDetail` dialog component rendered when a user clicks an appointment in the scheduling calendar.
- **Timeline_Strip**: A horizontal 4-dot connected visual indicator showing the appointment's progression through Booked → En route → On site → Done.
- **Action_Track**: A row of three large visual cards ("On my way", "Job started", "Job complete") that drive appointment status transitions.
- **Tag**: A customer-scoped label with schema `{ id, label, tone, source }` where tone is one of `neutral | blue | green | amber | violet` and source is `manual | system`.
- **Tag_Editor**: A bottom-sheet overlay for adding, removing, and managing customer tags.
- **Maps_Picker**: A popover anchored above the "Get directions" button offering Apple Maps and Google Maps as navigation options.
- **Sheet**: A bottom-sheet overlay (560 px wide, 20 px top radius, grab handle) used for the Tag_Editor, Payment flow, and Estimate flow.
- **Customer_Hero**: The card section displaying customer avatar, name, history summary, tags row, phone, and email.
- **Step**: An integer 0–3 representing the appointment's position in the workflow: 0 = Booked, 1 = En route, 2 = On site, 3 = Done.
- **Tone**: A visual category for Tag chips — `neutral`, `blue`, `green`, `amber`, or `violet` — each mapping to specific text, background, and border colors per the design token palette.
- **System_Tag**: A Tag with `source: "system"` that is auto-applied by the platform (e.g., "Overdue balance") and cannot be removed by staff via the Tag_Editor.
- **Link_Button**: A 44 px min-height button with 12 px radius, 1.5 px border, used for secondary actions (Add photo, Notes, Review, Edit tags, footer actions).
- **Design_Tokens**: The authoritative color, typography, spacing, and radius values defined in the design handoff spec §4.

## Requirements

### Requirement 1: Modal Container and Layout

**User Story:** As a staff member, I want the appointment modal to match the high-fidelity design spec, so that the interface is visually consistent and professional.

#### Acceptance Criteria

1. THE Modal SHALL render at a fixed width of 560 px, centered on desktop viewports (≥ 640 px), with an 18 px border-radius, 1 px `#E5E7EB` border, white background, and the design-spec modal shadow.
2. WHEN the viewport width is less than 640 px, THE Modal SHALL present as a full-width bottom sheet with 20 px top-corner radius, a 44×5 px grab handle, and internal scroll up to 92 vh.
3. THE Modal SHALL use the Inter font family for UI text and JetBrains Mono for timestamps, with weights 400, 500, 600, 700, and 800 loaded.
4. THE Modal SHALL apply all Design_Tokens (colors, typography sizes, spacing, radii) exactly as specified in the design handoff §4.
5. WHEN the Modal opens, THE Modal SHALL set `role="dialog"`, `aria-modal="true"`, label itself by the job title, and place initial focus on the close button.
6. THE Modal SHALL trap keyboard focus while open and return focus to the triggering calendar chip on close.
7. WHEN the user clicks the close button, clicks the backdrop, or presses `Escape`, THE Modal SHALL dismiss with the appropriate animation (fade+scale on desktop, slide-down on mobile).
8. THE Modal SHALL render a backdrop of `rgba(11,18,32,0.4)` with `backdrop-filter: blur(4px)` when supported.

### Requirement 2: Header Block

**User Story:** As a staff member, I want to see the appointment status, type, ID, title, and schedule at a glance, so that I can quickly orient myself.

#### Acceptance Criteria

1. THE Modal SHALL display a status badge pill using the design-spec color mapping: `confirmed`/`scheduled` → "Scheduled" (blue), `en_route` → "On the way" (blue), `in_progress` → "On site" (orange), `completed` → "Complete" (green).
2. THE Modal SHALL display a "Residential" (or appropriate property type) neutral pill and an appointment ID neutral pill in the meta-chips row.
3. THE Modal SHALL display the job title as an H1 element using 26 px / weight 800 / -0.8 letter-spacing / `#0B1220` color.
4. THE Modal SHALL display the appointment date and time range using 15 px / weight 600 / `#4B5563` color.
5. THE Modal SHALL render a 40×40 px close button with 12 px radius, 1.5 px `#E5E7EB` border, white background, and an 18 px X icon.
6. WHEN the appointment status is `pending` or `draft`, THE Modal SHALL hide the status badge from the meta-chips row and hide the Action_Track section entirely.

### Requirement 3: Timeline Strip

**User Story:** As a staff member, I want to see a visual timeline of the appointment's progression, so that I can understand the current stage and past timestamps at a glance.

#### Acceptance Criteria

1. THE Timeline_Strip SHALL display four evenly-distributed dots labeled "Booked", "En route", "On site", and "Done", connected by 2 px horizontal lines.
2. WHEN a step index is less than or equal to the current Step, THE Timeline_Strip SHALL fill that dot with `#0B1220` and a 2 px `#0B1220` border, and fill the connector line to its left with `#0B1220`.
3. WHEN a step index equals the current Step and the current Step is not the final step (3), THE Timeline_Strip SHALL render an outer ring (`box-shadow: 0 0 0 4px #DBEAFE`) and a blue 8 px inner dot (`#1D4ED8`) on that dot.
4. WHEN a step has been completed (index < current Step), THE Timeline_Strip SHALL render a white 12 px checkmark (stroke 3.2) inside that dot.
5. WHEN a step has not been reached, THE Timeline_Strip SHALL render that dot with white fill and 2 px `#E5E7EB` border, and the connector line in `#E5E7EB`.
6. THE Timeline_Strip SHALL display the timestamp in mono font (11.5 px / weight 600 / `#6B7280`) below each reached step's label, and "—" for steps not yet reached.
7. WHEN the viewport width is less than 360 px, THE Timeline_Strip SHALL reduce per-dot min-width to 60 px, drop the mono time to 11 px, and allow horizontal scrolling.

### Requirement 4: Action Track (Status Progression)

**User Story:** As a field technician, I want large, clear action cards to advance the appointment through its workflow stages, so that I can update status quickly on-site.

#### Acceptance Criteria

1. THE Action_Track SHALL display three side-by-side cards ("On my way", "Job started", "Job complete") with 8 px gap, each flex-1, min-height 104 px, 14 px border-radius, and the design-spec soft shadow.
2. WHEN a card is the current active action, THE Action_Track SHALL render it with its stage color fill (`#1D4ED8` for slot 1, `#C2410C` for slot 2, `#047857` for slot 3), white text, and a 36×36 icon bubble with `rgba(255,255,255,0.18)` background.
3. WHEN a card's prerequisite step has not been reached, THE Action_Track SHALL render it at `opacity: 0.4` with `cursor: not-allowed` and no shadow.
4. WHEN a card's action has been completed, THE Action_Track SHALL render it with white background, 2 px `#047857` border, green text, a green checkmark in the icon bubble, and the completion timestamp in mono font.
5. WHEN the user taps an active action card, THE Action_Track SHALL optimistically advance the appointment to the next Step, update the Timeline_Strip, and call the corresponding backend mutation (`PATCH /appointments/:id`).
6. IF the backend mutation fails after an optimistic update, THEN THE Action_Track SHALL revert to the previous state and display an error toast.
7. THE Action_Track SHALL use `<button>` elements with full accessible labels (e.g., "On my way, text customer") and announce stage completion via `aria-live="polite"`.
8. WHEN the appointment status is `pending` or `draft`, THE Action_Track SHALL not render.

### Requirement 5: Secondary Actions Strip

**User Story:** As a staff member, I want quick access to add photos, notes, reviews, and edit tags from the appointment modal, so that I can perform common tasks without navigating away.

#### Acceptance Criteria

1. THE Modal SHALL display a row of four Link_Buttons below the Action_Track: "Add photo", "Notes", "Review", and "Edit tags", each with its respective icon.
2. WHEN the user taps "Edit tags", THE Modal SHALL open the Tag_Editor Sheet and set the "Edit tags" button to its active state (bg `#EDE9FE`, border `#6D28D9`, text `#6D28D9`).
3. WHEN the Tag_Editor Sheet closes, THE Modal SHALL return the "Edit tags" button to its default state.
4. THE Modal SHALL NOT display an "AI draft" button — the former violet AI draft button is removed from this design.
5. Each Link_Button SHALL meet the 44 px minimum hit target and use 14 px / weight 700 text with a 16 px icon.

### Requirement 6: Payment and Estimate CTAs

**User Story:** As a staff member, I want prominent buttons to collect payment or send an estimate directly from the appointment modal, so that I can handle financial actions on-site.

#### Acceptance Criteria

1. THE Modal SHALL display two stacked full-width outline buttons: "Collect payment" (teal: border + text `#0F766E`, credit card icon) and "Send estimate" (violet: border + text `#6D28D9`, document icon), each min-height 60 px, 14 px radius, 2 px border.
2. WHEN the user taps "Collect payment", THE Modal SHALL open the Payment Sheet as a bottom-sheet overlay, reusing the existing `useCollectPayment()` hook and payment flow logic.
3. WHEN the user taps "Send estimate", THE Modal SHALL open the Estimate Sheet as a bottom-sheet overlay, reusing the existing `useCreateEstimateFromAppointment()` hook and estimate flow logic.
4. THE Modal SHALL enforce single-sheet exclusivity: opening any Sheet (Payment, Estimate, or Tag_Editor) SHALL close any other currently open Sheet.
5. WHEN a payment is successfully collected, THE Modal SHALL replace the "Collect payment" button with a green "Paid — $NNN · method" confirmation card.
6. WHEN an estimate is sent, THE Modal SHALL display an estimate status banner (e.g., "Estimate #EST-0142 sent · awaiting reply") in the modal.

### Requirement 7: Customer Hero Card

**User Story:** As a staff member, I want to see the customer's identity, contact info, history, and tags in a prominent card, so that I have full context for the appointment.

#### Acceptance Criteria

1. THE Customer_Hero SHALL display a teal-tinted header strip (`#CCFBF1` background) with a 44×44 avatar circle (white, 2 px teal border, initials in `#0F766E`), the customer's full name (18 px / weight 800), and a history summary line (12.5 px / weight 600 / `#4B5563`).
2. THE Customer_Hero SHALL display a tags row below the header with a "TAGS" caps label and the customer's current tags rendered as Tag chips per the Tone palette.
3. WHEN the customer has zero tags, THE Customer_Hero SHALL hide the tags row entirely.
4. THE Customer_Hero SHALL display a phone row with a blue icon badge, "PHONE" caps label, the phone number in mono font (17 px / weight 800), and a right-aligned "Call" chip (`#1D4ED8` background, white text) that links to `tel:`.
5. THE Customer_Hero SHALL display an email row with a soft-bg icon badge and the email address as a `mailto:` link.
6. THE Customer_Hero SHALL never truncate the avatar or customer name; the history line SHALL use `text-overflow: ellipsis` on overflow.

### Requirement 8: Property and Directions Card

**User Story:** As a field technician, I want to see the property address and get directions via my preferred maps app, so that I can navigate to the job site efficiently.

#### Acceptance Criteria

1. THE Modal SHALL display a property card with a "PROPERTY" caps label, the street address (19 px / weight 800), and the city/state/zip (15 px / weight 600).
2. THE Modal SHALL display a full-width "Get directions" button (`#1D4ED8` background, white text, nav icon) at the bottom of the property card.
3. WHEN the user taps "Get directions" for the first time (no remembered choice), THE Modal SHALL open the Maps_Picker popover anchored above the button, rather than navigating directly.
4. THE Maps_Picker SHALL render as a popover with 14 px radius, white background, 1.5 px border, and the design-spec popover shadow, containing an "OPEN IN" header and two rows: "Apple Maps" (teal icon badge) and "Google Maps" (blue icon badge).
5. THE Maps_Picker SHALL use `role="menu"` with `role="menuitem"` rows, close on `Escape` or outside click, and manage focus (first item on open, return to trigger on close).
6. WHEN the user selects Apple Maps, THE Modal SHALL open `maps://?daddr=<encoded address>` (falling back to `https://maps.apple.com/?daddr=<encoded address>`).
7. WHEN the user selects Google Maps, THE Modal SHALL open `https://www.google.com/maps/dir/?api=1&destination=<encoded address>`, preferring lat/lng coordinates when available.
8. THE Maps_Picker SHALL include a "Remember my choice" button. For this release, the "Remember my choice" feature is DEFERRED — the picker SHALL appear on every tap.

### Requirement 9: Scope and Materials Card

**User Story:** As a staff member, I want to see the job scope, duration, staff count, priority, and materials list, so that I am prepared for the work.

#### Acceptance Criteria

1. THE Modal SHALL display a scope card with a "SCOPE" caps label and the job scope description in body-strong style (17 px / weight 800).
2. THE Modal SHALL display neutral pills for estimated duration (e.g., "~90 min"), staff count (e.g., "1 staff"), and an amber pill for priority level (e.g., "Normal").
3. THE Modal SHALL display a "MATERIALS" section with a wrap row of material tags, each with `padding 8px 12px`, 10 px radius, `#F9FAFB` background, 1.5 px `#E5E7EB` border, and 13.5 px / weight 700 text.

### Requirement 10: Assigned Tech Card

**User Story:** As an admin, I want to see the assigned technician and reassign if needed, so that I can manage staffing on the fly.

#### Acceptance Criteria

1. THE Modal SHALL display an assigned tech card with a user icon, "ASSIGNED TECH" caps label, the tech name and route number, and a "Reassign" Link_Button.
2. WHEN the current user has the tech role (not admin), THE Modal SHALL hide the "Reassign" button.

### Requirement 11: Footer Actions

**User Story:** As a staff member, I want Edit, No show, and Cancel actions in the modal footer, so that I can manage the appointment lifecycle.

#### Acceptance Criteria

1. THE Modal SHALL display a footer bar (bg `#F9FAFB`, 1 px top border) with three Link_Buttons: "Edit" (pencil icon, neutral), "No show" (alert icon, neutral), and "Cancel" (X icon, destructive: text `#B91C1C`, border `#FCA5A5`).
2. WHEN the user taps "Edit", THE Modal SHALL invoke the existing edit flow (opening the `AppointmentForm`).
3. WHEN the user taps "No show", THE Modal SHALL invoke the existing no-show mutation.
4. WHEN the user taps "Cancel", THE Modal SHALL open the existing `CancelAppointmentDialog` with notification logic preserved.
5. WHEN the appointment is in a terminal state (`completed`, `cancelled`, `no_show`), THE Modal SHALL hide the footer actions.

### Requirement 12: Customer Tags Data Model (Backend)

**User Story:** As a developer, I want a normalized customer tags data model, so that tags are stored efficiently and can be queried, filtered, and managed independently.

#### Acceptance Criteria

1. THE Backend SHALL create a `customer_tags` table with columns: `id` (UUID, PK), `customer_id` (UUID, FK to `customers.id`, NOT NULL), `label` (VARCHAR(32), NOT NULL), `tone` (VARCHAR(10), NOT NULL, one of `neutral`, `blue`, `green`, `amber`, `violet`), `source` (VARCHAR(10), NOT NULL, one of `manual`, `system`), `created_at` (TIMESTAMPTZ, NOT NULL).
2. THE Backend SHALL enforce a unique constraint on `(customer_id, label)` to prevent duplicate tag labels per customer.
3. THE Backend SHALL cascade-delete tags when a customer is deleted.
4. THE Backend SHALL expose a `GET /api/v1/customers/{id}/tags` endpoint returning the customer's tags as a list of Tag objects.
5. THE Backend SHALL expose a `PUT /api/v1/customers/{id}/tags` endpoint accepting a full replacement list of tags (label + tone pairs), performing a diff against existing tags, inserting new ones, and deleting removed ones in a single transaction.
6. THE Backend SHALL NOT allow deletion of tags where `source = "system"` via the PUT endpoint — system tags SHALL be preserved and returned in the response with an indicator.
7. THE Backend SHALL validate that `label` is between 1 and 32 characters and `tone` is one of the five allowed values.

### Requirement 13: Tag Editor Sheet

**User Story:** As a staff member, I want to add, remove, and manage customer tags from a dedicated editor, so that I can keep customer profiles accurate and useful.

#### Acceptance Criteria

1. WHEN the Tag_Editor opens, THE Tag_Editor SHALL display the sheet title "Edit tags" and a subtitle "Tags apply to [Customer Name] across every job — past and future".
2. THE Tag_Editor SHALL display a "CURRENT TAGS" section showing all current tags as removable Tag chips inside a container with 12 px padding, 12 px radius, `#F9FAFB` background, and an "Add custom" dashed-border button at the end.
3. WHEN the user taps the remove-X on a Tag chip, THE Tag_Editor SHALL remove that tag from the draft list (local state only, not yet saved).
4. WHEN a Tag has `source: "system"`, THE Tag_Editor SHALL render the remove-X as disabled with a tooltip explaining that system tags cannot be removed.
5. THE Tag_Editor SHALL display a "SUGGESTED" section with predefined tag suggestions (e.g., "Repeat customer", "Commercial", "Difficult access", "Dog on property", "Prefers text", "Gate code needed", "Corner lot"), filtering out any tags already applied.
6. WHEN the user taps a suggested tag, THE Tag_Editor SHALL add it to the draft list with the appropriate Tone assignment.
7. WHEN the user taps "Add custom", THE Tag_Editor SHALL allow text input for a custom tag label, capped at 32 characters.
8. THE Tag_Editor SHALL display an info banner (blue, `#DBEAFE` background) explaining that changes save to the customer profile and auto-inherit to future jobs.
9. WHEN the user taps "Save tags · applies everywhere", THE Tag_Editor SHALL call `PUT /api/v1/customers/{id}/tags` with the draft tag list, optimistically update the tags row in the Customer_Hero, and close the sheet on success.
10. IF the save request fails, THEN THE Tag_Editor SHALL display a toast "Couldn't save tags — try again" and restore the previous tag state.
11. WHEN tags are saved successfully, THE Tag_Editor SHALL emit a customer-updated event so that other open views (customer tab, future jobs list) refresh their tag data.
12. Each removable Tag chip's remove-X SHALL have an accessible label (e.g., `aria-label="Remove tag: Repeat customer"`).

### Requirement 14: Sheet Container Component

**User Story:** As a developer, I want a reusable sheet container that matches the design spec, so that the Tag Editor, Payment flow, and Estimate flow share a consistent overlay pattern.

#### Acceptance Criteria

1. THE Sheet component SHALL render at 560 px width (matching the Modal), with white background, 20 px top-corner radius, 1 px `#E5E7EB` border, and the modal shadow.
2. THE Sheet component SHALL display a 44×5 px grab handle (3 px radius, `#E5E7EB` background) centered at the top.
3. THE Sheet component SHALL support an optional back button (44×44, 1.5 px border, 12 px radius, back-arrow icon) and a close button in the header row.
4. THE Sheet component SHALL render a header with title (22 px / weight 800 / -0.5 letter-spacing) and optional subtitle (13.5 px / weight 600 / `#4B5563`).
5. THE Sheet component SHALL render a scrollable body area (`overflow: auto`, `flex: 1`) and a sticky footer (bg `#F9FAFB`, 1 px top border).

### Requirement 15: Preserve Existing Functionality

**User Story:** As a staff member, I want all existing appointment modal features to continue working in the redesigned modal, so that no functionality is lost.

#### Acceptance Criteria

1. THE Modal SHALL continue to display the communication timeline (`AppointmentCommunicationTimeline`) for the appointment.
2. THE Modal SHALL continue to display the reschedule request banner when a pending reschedule exists, with "Reschedule to Alternative" and "Resolve without reschedule" actions.
3. THE Modal SHALL continue to display the no-reply review banner when `needs_review_reason` is `no_confirmation_response`, with "Call Customer", "Send Reminder", and "Mark Contacted" actions.
4. THE Modal SHALL continue to display the `OptOutBadge` when the customer has opted out of SMS.
5. THE Modal SHALL continue to support the `SendConfirmationButton` for draft appointments.
6. THE Modal SHALL continue to display duration metrics (travel time, job duration, total time) for completed appointments.
7. THE Modal SHALL continue to support the existing cancel dialog with customer notification logic.
8. THE Modal SHALL continue to support the existing edit flow via `AppointmentForm`.

### Requirement 16: Status Mapping and State Machine

**User Story:** As a developer, I want a clear mapping between backend appointment statuses and the modal's visual states, so that the UI is always consistent with the data.

#### Acceptance Criteria

1. THE Modal SHALL map `confirmed` and `scheduled` statuses to Step 0 ("Booked"), `en_route` to Step 1 ("En route"), `in_progress` to Step 2 ("On site"), and `completed` to Step 3 ("Done").
2. WHEN the appointment status is `pending` or `draft`, THE Modal SHALL not display the Timeline_Strip or Action_Track.
3. THE Modal SHALL enforce linear progression: Step transitions SHALL only advance forward (0→1→2→3), never skip or reverse.
4. WHEN the user advances a step, THE Modal SHALL call the corresponding existing mutation: `useMarkAppointmentEnRoute` (step 0→1), `useMarkAppointmentArrived` (step 1→2), `useMarkAppointmentCompleted` (step 2→3).

### Requirement 17: Tag Chip Component

**User Story:** As a developer, I want a reusable Tag chip component that renders consistently across the modal, tag editor, and future customer profile views.

#### Acceptance Criteria

1. THE Tag chip SHALL render as an inline-flex pill with 999 px radius, padding `5px 10px` (static) or `5px 6px 5px 10px` (removable), and 12.5 px / weight 800 / -0.1 letter-spacing text.
2. THE Tag chip SHALL apply text, background, and border colors based on the Tag's Tone value per the design token palette.
3. WHEN the Tag chip is removable, THE Tag chip SHALL display an 18×18 remove-X circle with `rgba(0,0,0,0.08)` background and an 11 px X icon (stroke 3).
4. THE Tag chip SHALL enforce `white-space: nowrap` — tag labels SHALL NOT wrap inside a chip.
5. FOR ALL valid Tone values (neutral, blue, green, amber, violet), THE Tag chip SHALL render the correct color combination as specified in the design handoff §7.1.

### Requirement 18: Accessibility

**User Story:** As a user with assistive technology, I want the appointment modal to be fully accessible, so that I can use all features with a keyboard and screen reader.

#### Acceptance Criteria

1. THE Modal SHALL include `aria-label="Status: [status text]"` on all status badge pills so screen readers convey the status semantics.
2. THE Action_Track buttons SHALL NOT be toggles — they SHALL be `<button>` elements with full labels and announce results via `aria-live="polite"`.
3. THE Maps_Picker SHALL render with `role="menu"` and `role="menuitem"` rows, with `Escape` closing the popover and focus managed (first item on open, return to trigger on close).
4. THE Tag chip remove-X buttons SHALL include `aria-label="Remove tag: [tag label]"` for screen reader identification.
5. THE Modal SHALL ensure all interactive elements meet the 44×44 px minimum hit target on all viewport sizes.
6. THE Modal SHALL ensure color alone never encodes meaning: tag tones are paired with distinct labels, and status is always paired with text.

### Requirement 19: Responsive Behavior

**User Story:** As a staff member using a mobile device, I want the appointment modal to adapt to my screen size, so that I can use it comfortably on any device.

#### Acceptance Criteria

1. WHEN the viewport width is 640 px or greater, THE Modal SHALL render as a centered dialog at 560 px width with 24 px gutter.
2. WHEN the viewport width is less than 640 px, THE Modal SHALL render as a bottom sheet at full viewport width with 20 px top radius, a visible drag handle, and content filling up to 92 vh with internal scroll and a sticky header.
3. WHEN the viewport width is less than 360 px, THE Timeline_Strip SHALL reduce per-dot min-width to 60 px, reduce the mono time font to 11 px, and enable horizontal scrolling.
4. THE Payment and Estimate CTA buttons SHALL remain full-width on all breakpoints.
5. THE Customer_Hero avatar and name SHALL never truncate; the history line SHALL use `text-overflow: ellipsis` on overflow.

### Requirement 20: End-to-End Testing and Deployment Validation

**User Story:** As a developer, I want the combined appointment modal to be validated end-to-end on a deployed environment, so that I have confidence the feature works correctly in production conditions.

#### Acceptance Criteria

1. THE implementation SHALL include unit tests (Vitest) for all new frontend components: the modal container, Timeline_Strip, Action_Track, Tag chip, Tag_Editor, Maps_Picker, Sheet container, Customer_Hero, and all card sections.
2. THE implementation SHALL include backend unit tests (pytest, `@pytest.mark.unit`) for the `customer_tags` table model, tag CRUD service, and tag API endpoints.
3. THE implementation SHALL include backend functional tests (`@pytest.mark.functional`) verifying the full tag lifecycle: create tags, read tags, update tags, delete tags, system tag protection, and unique constraint enforcement.
4. THE implementation SHALL include backend integration tests (`@pytest.mark.integration`) verifying that tag changes propagate correctly when fetching appointment details with customer data.
5. THE implementation SHALL include property-based tests (Hypothesis) verifying correctness properties: tag label uniqueness per customer, tone value validity, system tag immutability, and step progression linearity.
6. AFTER all code changes are complete, THE implementation SHALL deploy the frontend to Vercel and wait for a successful build.
7. AFTER a successful Vercel deployment, THE implementation SHALL use agent-browser to validate the deployed appointment modal by: navigating to the schedule page, opening an appointment, verifying the modal renders with the correct layout (header, timeline, action track, customer hero, property card, scope card, footer), and capturing screenshots to `e2e-screenshots/appointment-modal/`.
8. THE agent-browser validation SHALL test the tag editor flow: opening the Edit tags sheet, adding a suggested tag, removing a tag, and verifying the save behavior.
9. THE agent-browser validation SHALL test the maps picker: tapping "Get directions" and verifying the popover renders with Apple Maps and Google Maps options.
10. THE agent-browser validation SHALL test responsive behavior by setting the viewport to mobile (375×812) and verifying the modal renders as a bottom sheet.
11. THE agent-browser validation SHALL check for JavaScript console errors and uncaught exceptions during all interactions.
12. ALL tests (unit, functional, integration, property-based, and E2E) SHALL pass with zero failures before the feature is considered complete.
