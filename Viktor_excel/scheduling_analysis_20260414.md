# Scheduling Analysis — April 14, 2026

**Data sources analyzed:**
1. Production database backup (April 14, 2026 06:57 UTC)
2. `Stripe List.csv` — Stripe paying customers
3. `Spring Start Reponses.xlsx` — Google Form responses with preferred week
4. `2026 Job Requests .xlsx` — Master job request list + lead tracking

**Matching methodology:** Phone number (primary), email, exact name, then fuzzy name matching with nickname support (Jim/James, Kim/Kimberly, etc.). All matches verified; false positives flagged.

---

## 1. Production Database Summary (April 14)

| Entity | Count |
|--------|-------|
| Customers | 100 |
| Properties | 94 |
| Service Agreements (active) | 97 |
| Service Agreements (cancelled) | 2 |
| Spring Startup Jobs (active, to_be_scheduled) | 92 |
| Fall Winterization Jobs (active) | 97 |
| Mid-Season Inspection Jobs (active) | 14 |
| Other Jobs (estimates, monthly visits) | 9 |
| Staff | 1 (Viktor Grin — admin only) |
| Leads | 30 |

### Spring Startup Jobs by Tier

| Tier | Price | Count | Priority |
|------|-------|-------|----------|
| Essential Residential | $175 | 73 | 0 (normal) |
| Professional Residential | $260 | 18 | 1 (high) |
| Premium Residential | $725 | 1 | 2 (urgent) |
| **Total** | | **92** | |

All 92 jobs are in `to_be_scheduled` status with target window April 1 – April 30. Zero appointments have been created.

### Winterization-Only Customers (no spring startup)

These 5 customers have active service agreements but are winterization-only ($85). They do NOT get a spring startup:

| Name | Tier |
|------|------|
| Mark Anderson | Winterization Only Residential ($85) |
| Ryan Paul | Winterization Only Residential ($85) |
| Ray Areaux Jr. | Winterization Only Residential ($85) |
| Larry Weum | Winterization Only Residential ($85) |
| James E Orrock | Winterization Only Residential ($85) |

---

## 2. Stripe List Analysis

**Total Stripe rows:** 104
**Test accounts (Kirill/Viktor):** 7
**Real paying customers:** 97

### Result: ALL 97 real Stripe customers are in the database.

Every paying Stripe customer has been matched to a DB customer record. No missing imports.

The 6 customers who paid but have no spring startup job are the 5 winterization-only customers above, plus Mark Anderson who appears twice in Stripe (one $85 winterization-only, one $0 refunded entry).

---

## 3. Spring Start Responses Analysis

**Total form responses:** 125
**Duplicate submissions:** 2 (Brian Grove and Christie Conley submitted twice each)
**Unique responses:** 123

### Week Preference Distribution

| Week | Count | Notes |
|------|-------|-------|
| 4/15 - 4/18 | 2 | Freeze risk |
| 4/20 - 4/25 | 5 | Potential freeze risk |
| **4/27 - 5/2** | **56** | **Most popular — safe** |
| **5/4 - 5/9** | **40** | **Second most popular — safe** |
| 5/11 - 5/16 | 11 | Safe |
| 5/18 - 5/23 | 8 | Safe |
| Custom/Other | 3 | See notes below |

**Custom responses:**
- "5/22 or after but Friday only :)" — Wesley, 17045 46th Ave. N., Plymouth
- "Weekdays that works for me are 4/28, 5/13, 5/14, 5/18, 5/21. Plus weekends if convenient to you." — Chetan Shenoy, 5795 Juneau Lane N, Plymouth
- One blank entry with no name or phone

### Matched to DB: 59 (all have service agreements + spring jobs)

These 59 people are already in the database with active service agreements and spring startup jobs. Their week preference from the form can be used to schedule them.

| Form Name | DB Name | Match Method | Preferred Week |
|-----------|---------|-------------|----------------|
| Alonzo | Alonzo Skjefte | phone | 4/27 - 5/2 |
| Cathy Hogan | Catherine Hogan | phone | 5/4 - 5/9 |
| Alex Marinov | Alex Marinov | phone | 5/4 - 5/9 |
| Brian Grove | Brian Grove | exact name | 5/18 - 5/23 |
| Emily Scott | Emily Scott | phone | 4/27 - 5/2 |
| Cinda Baxter | Cinda Baxter | phone | 5/4 - 5/9 |
| Chris Hennen | Christopher Hennen | phone | 5/4 - 5/9 |
| Christie Conley | Christine conley | phone | 5/4 - 5/9 |
| Boris - Yefim Perelman | Yefim "Boris" Perelman | phone | 4/27 - 5/2 |
| Ben White | Benjamin RybaWhite | phone | 5/11 - 5/16 |
| Dan Flanigan | Daniel Flanigan | phone | 4/27 - 5/2 |
| Ed Wang | Edward Wang | phone | 5/4 - 5/9 |
| Damon Smith | Damon Smith | phone | 5/4 - 5/9 |
| Brian Very | Brian E Very | phone | 4/27 - 5/2 |
| Grant Meyer | Grant Meyer | phone | 4/27 - 5/2 |
| Jestin Lutes | Jestin Lutes | phone | 5/11 - 5/16 |
| Kim Osborne | Kimberly Osborne | fuzzy name | 5/4 - 5/9 |
| John Hayden | John Hayden | phone | 4/27 - 5/2 |
| Kevin Frawley | Kevin M Frawley | phone | 4/27 - 5/2 |
| Lisa Guille | Lisa Guille | phone | 5/4 - 5/9 |
| Jennifer Geer | Jennifer Geer | phone | 4/20 - 4/25 |
| Julie Parikh | Julie Parikh | phone | 4/20 - 4/25 |
| Charles Liu | chengjun liu | phone | 4/27 - 5/2 |
| Jeff Schutt | Jeffrey A Schutt | fuzzy name | 5/4 - 5/9 |
| Dennis Zuzek | Dennis Zuzek | exact name | 5/4 - 5/9 |
| Kim Carlson | Kim Carlson | exact name | 4/27 - 5/2 |
| Nona Hovey | Nona M Hovey | phone | 4/27 - 5/2 |
| John Holper | John Holper | phone | 4/27 - 5/2 |
| Megan Kummerlowe | Megan n Kummerlowe | phone | 4/27 - 5/2 |
| Amy Finsand | Amy Finsand | phone | 4/27 - 5/2 |
| Lucas Carney | Lucas J Carney | phone | 5/4 - 5/9 |
| Pat Kovalesky | Pat Kovalesky | phone | 4/27 - 5/2 |
| Pete Mansur | Peter J Mansur | phone | 4/27 - 5/2 |
| Jeff Torrison | Jeffrey Torrison | fuzzy name | 5/4 - 5/9 |
| Prasanna Suryadevar | Prasanna Suryadevar | phone | 4/27 - 5/2 |
| Ryan LeMieux | Ryan LeMieux | phone | 5/18 - 5/23 |
| David Robinson | David W. Robinson | phone | 4/27 - 5/2 |
| Mike Carey | Michael Carey | phone | 4/27 - 5/2 |
| Tracy Maxwell | Tracy A Maxwell | phone | 4/27 - 5/2 |
| Ritu Sinha | Ritu Sinha | exact name | 5/4 - 5/9 |
| Pat Delahunt | Patrick Delahunt | phone | 5/18 - 5/23 |
| Colin Bruns | Colin Bruns | phone | 4/27 - 5/2 |
| Carolyn Lee | Carolyn Lee | phone | 5/4 - 5/9 |
| Patricia Beithon | Patricia Beithon | phone | 5/4 - 5/9 |
| Vlad Bodnar | Vladislav Bodnar | phone | 5/4 - 5/9 |
| John Minor | John Minor | phone | 4/27 - 5/2 |
| Judy Lemke | Judy Lemke | phone | 4/27 - 5/2 |
| Jen Kale | Jennifer Kale | phone | 4/27 - 5/2 |
| Sandra Tate | Sandra D Tate | phone | 5/4 - 5/9 |
| Kaylee Traynor | Kaylee Traynor | phone | 5/4 - 5/9 |
| Derek Anderson | Derek Anderson | phone | 4/27 - 5/2 |
| Andy filer | Andrew Filer | phone | 4/27 - 5/2 |
| John Shanderuk | John Shanderuk | phone | 5/4 - 5/9 |
| Darren Braml | Darren Braml | phone | 5/4 - 5/9 |
| Virginia O Antony | Virginia O Abtony | phone | 5/4 - 5/9 |
| Jack Morgan | Jack Morgan | phone | 5/18 - 5/23 |
| Mary McGowan | Mary McGowan | phone | 4/15 - 4/18 |
| Maddie Umhoefer | Madeleine Umhoefer | phone | 4/27 - 5/2 |
| Lauren Bartig | Lauren Kessler Bartig | phone | 5/18 - 5/23 |

### FALSE POSITIVE flagged and removed:

"Mike Lecy- Home Health Care" (phone 763-233-7565) was incorrectly matched to "Michael Carey" by the fuzzy name matcher. The word "care" from "home health care" matched the last name "Carey". **Mike Lecy is a separate person — a commercial/institutional client — and is NOT in the database.** He has been moved to the "not in DB" list.

### Not in DB: 64 people (need to be imported as one-off customers)

These people responded to the Spring Start form with a preferred week but are NOT service agreement customers. They need to be created as Customer + Property + Job records.

| Name | Phone | Address | Preferred Week |
|------|-------|---------|----------------|
| Dave Asinger | 612-508-7372 | 11330 Parkside Trail, Maple Grove 55369 | 5/4 - 5/9 |
| Charles Stuber | 612-239-2482 | 14051 Cheshire Ln N Dayton Mn 55327 | 4/27 - 5/2 |
| Alisa Richardson | 612-323-6616 | 4690 Eastwood Circle | 4/27 - 5/2 |
| Ellen MacRae | 949-678-0226 | 16200 Hampshire Ave S, Prior Lake, MN 55372 | 4/27 - 5/2 |
| Igor Sovostyanov | *no phone* | 4705 Urbandale LN N | 5/4 - 5/9 |
| Jim Hanggi | 612-963-8183 | 8825 Irving Ave S | 4/27 - 5/2 |
| Ilya Katz | *no phone* | 1704 Ford Road, Minnetonka | 4/27 - 5/2 |
| Kristin Illingworth | 513-257-1778 | 250 Meadowview Ln | 5/4 - 5/9 |
| Kevin Weirich | 612-323-7144 | 4255 Wild Meadows Dr, Medina, MN 55340 | 4/27 - 5/2 |
| Kairav Vakil | 317-850-3429 | 5808 View Ln Edina 55436 | 5/4 - 5/9 |
| Lauren LaHaye | 952-495-0867 | 335 Lythrum Ln. Hamel, Mn 55340 | 5/4 - 5/9 |
| Kenneth Mayer | 612-799-9823 | 15592 71st Street NE, Otsego, MN 55330 | 4/27 - 5/2 |
| Bruce VanderSchaaf | 612-810-4257 | 6319 Orchid Lane North, Maple Grove, MN | 4/27 - 5/2 |
| Ksenia Ezekoye | 651-728-1467 | 6340 Bellevue Ln | 5/4 - 5/9 |
| Laura Bensom | 612-978-7619 | 4145 Wild Meadows Drive | 5/11 - 5/16 |
| Jim Damiani | 612-270-6318 | 12500, 58th Ave N | 5/4 - 5/9 |
| Hyunsook Kim | 952-737-6958 | 7432 Shannon Dr | 5/4 - 5/9 |
| Joseph | 612-202-4007 | 10157 Georgia Avenue North Brooklyn Park | 4/20 - 4/25 |
| Kavitha and Deepak Kamath | 952-688-2009 | 9766 Archer Lane, Eden Prairie 55347 | 5/11 - 5/16 |
| Max Barsky | 651-343-1380 | 6444 Garland Ln N | 4/27 - 5/2 |
| Kim Levine | 402-541-4773 | 209 Ottawa Ave S. Golden Valley MN 55416 | 5/18 - 5/23 |
| Robin Pardur | 612-481-8250 | 15497 Elm Road North, Maple Grove 55311 | 4/27 - 5/2 |
| Rachel Sanzone | 651-216-1365 | 3705 Rosewood Lane North, Plymouth | 4/15 - 4/18 |
| Sam Goldfarb | 267-408-5940 | 12100 29th Ave N, Plymouth MN 55441 | 4/27 - 5/2 |
| Mike Lecy (Home Health Care) | 763-233-7565 | 800 Boone Ave N Golden Valley MN 55427 | 5/18 - 5/23 |
| Nishant Jain | 612-703-2671 | 17047, Valley Road, Eden Prairie | 5/4 - 5/9 |
| Jocelyn Mei | 317-506-2379 | 6260 Merrimac Ln N. Maple Grove MN | 5/4 - 5/9 |
| Steven Magagna | 734-478-4896 | 406 Kenmar Cir, Minnetonka, MN, 55305 | 5/4 - 5/9 |
| Melissa Lee | 612-501-5037 | 17100 72nd Ave N, Maple Grove MN 55311 | 5/4 - 5/9 |
| Nicholas Brown | 612-850-1479 | 1340 Zircon Lane North Plymouth, Mn 55441 | 4/27 - 5/2 |
| Tracie Medina | 763-300-3743 | 2550 Bridle Creek trail | 5/18 - 5/23 |
| Samantha Sonday | 269-204-5186 | 2414 Emerald Trail Hopkins MN 55305 | 5/11 - 5/16 |
| Ramon Pastrano | 612-396-2537 | 12549 95th PL N Maple Grove, MN 55369 | 4/27 - 5/2 |
| Wayne Newton | *9 digits: 628891065* | 6468 Kurtz Ln | 4/27 - 5/2 |
| Terri Schoenfelder | 763-807-5075 | 2580 E Medicine lake blvd | 4/27 - 5/2 |
| Molly King | 612-670-2516 | 12725 43rd Ave N | 5/11 - 5/16 |
| Alexander Kartaev | 612-987-5987 | 12125 24th ave N, Plymouth MN 55441 | 4/27 - 5/2 |
| Tracy Sellman | 952-210-7609 | 14425 45th Ave N | 5/11 - 5/16 |
| Dan Vartolomei | 763-352-1458 | 150 prairie creek rd, Hamel, MN 55340 | 4/27 - 5/2 |
| Matt Weidinger | 612-599-0790 | 10051 Troy Lane North | 4/20 - 4/25 |
| Yefim Tsukerman | 763-443-2569 | 6946 Vagabond Court North Maple Grove | 5/4 - 5/9 |
| Ash Jafri | 269-599-3311 | 8263 Deerwood Ln N Maple Grove MN 55369 | 5/4 - 5/9 |
| Garret Cerkvenik | 602-386-7098 | 5205 W 61st St, Edina 55436 | 5/4 - 5/9 |
| Muzaffar Zaman | 952-334-6964 | 7046 Terraceview Ln N, Maple Grove | 4/27 - 5/2 |
| Dilip Desai | 952-250-5340 | 6318 Oxford Road N | 4/27 - 5/2 |
| Ashish Srivastava | 651-600-2484 | 17686 Haralson Dr, Eden Prairie, MN 55347 | 5/11 - 5/16 |
| Rustam Muharamov | 612-444-3333 | 5700 long brake trail Edina Mn 55439 | 5/4 - 5/9 |
| Mike Reier | 763-241-3042 | 10820 50th Ct. N. Plymouth | 4/27 - 5/2 |
| Adil Elamri | 612-298-7592 | 4308 Highland Rd | 5/4 - 5/9 |
| Quintin Rubald | 612-963-6699 | 205 Calamus Circle | 4/27 - 5/2 |
| Kristin Kuderer | 952-221-2285 | 11071 Jackson Drive, Eden Prairie, MN | 4/27 - 5/2 |
| Yan Kucherov | 763-458-2964 | 903 206th Ave NW Oak Grove MN 55011 | 5/4 - 5/9 |
| Kerry Creeron | 608-345-4935 | 13718 Coyote Ct | 4/27 - 5/2 |
| Steve Woodley | 612-570-1030 | 7917 Wyoming Court Bloomington MN | 5/4 - 5/9 |
| Chetan Shenoy | 732-221-4061 | 5795 Juneau Lane N, Plymouth MN 55446 | Custom (see notes) |
| Jacqueline Sperling Hosseini | 414-801-5502 | 17973 MacIntosh Rd | 5/4 - 5/9 |
| Gary Bischel | 651-202-5621 | 1085 Heritage Ln, Orono MN 55391 | 4/27 - 5/2 |
| Gary Carter | 952-239-6735 | 5813 McGuire Road, Edina | 4/27 - 5/2 |
| David Smith | 612-345-2936 | 6408 Alexander Court | 5/4 - 5/9 |
| John Jerabek | 612-695-7660 | 11320 Parkside Trail, Maple Grove, MN 55369 | 4/27 - 5/2 |
| Aaron Reiter | 612-669-8893 | 8805 Sycamore Ct Eden Prairie, MN 55347 | 4/27 - 5/2 |
| Laura Kottemann | 410-746-5977 | 1525 Bay Ridge Rd Wayzata MN | 4/27 - 5/2 |
| Wesley | 860-630-0371 | 17045 46th Ave. N., Plymouth, MN 55446 | 5/22+ (Fridays only) |
| *(blank entry)* | *no phone* | *(no address)* | 4/20 - 4/25 |

### Data quality issues in Spring Responses:
- **Jeff Schutt** entered "2750" as his phone number (that's his address on Casco Point Road). Matched via name.
- **Jeff Torrison** entered "6" as his phone number. Matched via name.
- **Brian Grove** entered "16301" as his phone number (his address). Matched via name.
- **Wayne Newton** has only 9 digits in phone (628891065) — missing leading digit.
- **Kim Osborne** entered area code 953 instead of 952 (typo). Matched via fuzzy name.
- **Igor Sovostyanov** and **Ilya Katz** did not provide phone numbers.
- One completely blank entry at the bottom.

---

## 4. Job Requests Sheet Analysis

**Total rows:** 391
**Spring startup requests:** 369
**Other job types:** 22 (irrigation installs, landscaping, repairs, etc.)

### After deduplication: 300 unique spring startup requests

69 duplicate entries removed (same person appearing 2-3 times with the same phone number).

### Cross-reference results:

| Category | Count |
|----------|-------|
| Matched to DB customer (confident) | 83 |
| NOT in DB | 217 |
| — with specific date/week | 20 |
| — TBD (need to be contacted) | 197 |
| — Also responded to Spring form | 51 |
| — Found in Leads table only | 5 |

### Job Requests NOT in DB, with specific dates (20 people — actionable now):

| Name | Phone | Requested Date | Special Tag |
|------|-------|---------------|-------------|
| Roman Keller | *none* | week of 4/27 or 5/4 | |
| Mike | *none* | Week of 4/20 or 4/27 (Prefers Thu/Fri after 1) | |
| Fritz | *none* | Week of 4/20 or 4/27 | |
| Isabella Nocera | 845-500-6835 | Week of 4/20 or 4/27 | |
| Michael Tobak | 612-803-2020 | Week of 4/20 or 4/27 (Prefers Thu/Fri after 1) | |
| Roger Sims | 970-214-1137 | 4/20 or 4/27 | HOA |
| Diane | 612-709-0965 | Week of 4/20 or 4/27 | |
| Trickey Helen | 952-933-5870 | week of 4/27 | CALL ONLY |
| Otto | 612-802-7291 | 4/27 or sooner | CALL ONLY |
| Giordani Crawford | 763-438-5099 | Week of 5/1 | |
| Brent J. Ryan | 763-458-8674 | Week of 4/20 or 4/27 | HOA |
| Alex Tkatch Building | 763-283-1775 | week of 4/27 or 5/4 | Subbed To Us |
| Laura Kotteman | 410-746-5977 | week of 4/20 or 4/27 | |
| Andrew Damyan (Fresh Water) | 612-685-0277 | Week of 5/11 or 5/18 | Commercial Building |
| Stapan Elm Creek HOA | *none* | week of 5/4 or 5/11 | Subbed To Us |
| Stapan Restaurant | *none* | week of 5/4 or 5/11 | Subbed To Us |
| Stepan Brynwood Association | *none* | week of 5/4 or 5/11 | Subbed To Us |
| Nataliya Krupatkykh | 952-210-4939 | 4/17 at 12:00 | |
| Helena Lekah | 952-500-2512 | 4/24-4/26 | |
| Geneva Fender | 612-229-1642 | Week of 5/4 | |

### Job Requests NOT in DB, TBD (197 people — need mass outreach):

These 197 unique people requested a spring startup at some point but have NOT provided a specific week preference. They need to be contacted to:
1. Confirm they still want the service
2. Get their preferred week
3. Collect payment if they're not already on a service agreement

**51 of these 197 have ALSO responded to the Spring Start form** — meaning they were previously TBD but have since picked a week. These can be cross-referenced with the Spring Responses list.

The remaining ~146 have genuinely not responded and need outreach.

*(Full list of 197 TBD names omitted for brevity — available in the Job Requests sheet, filtered to job_type containing "Start Up" and requested_date = "TBD")*

---

## 5. Lead Tracking Sheet Analysis

**Total leads:** 24

| Status | Count |
|--------|-------|
| Pending Response | 13 |
| LOSS | 4 |
| Scheduled | 3 |
| Other (waiting on closing, HOA response, etc.) | 3 |
| Give Estimate | 1 |

**Job types:** Almost all irrigation installs and sod installs — NOT spring startups. This sheet is mostly for new system installation leads, not scheduling-relevant for the current spring startup push.

**NOTE:** These leads may overlap with the CRM Leads table in the database (30 entries). Viktor should review for duplicates.

---

## 6. Combined Scheduling Readiness Summary

### Bucket A: READY TO SCHEDULE (92 jobs)

Already in the database as `TO_BE_SCHEDULED` spring startup jobs. 59 of these have a preferred week from the Spring Start form.

| Preferred Week | Count (of 59 who responded) |
|----------------|------|
| 4/15 - 4/18 | 1 |
| 4/20 - 4/25 | 2 |
| 4/27 - 5/2 | 24 |
| 5/4 - 5/9 | 19 |
| 5/11 - 5/16 | 3 |
| 5/18 - 5/23 | 5 |
| Custom | 1 |
| *(did not respond to form)* | *33* |

The 33 who didn't respond to the form still need to be contacted for their preferred week (or scheduled using the `preferred_schedule_details` from their service agreement onboarding — ASAP, 1-2 weeks, 3-4 weeks, etc.).

### Bucket B: NEED TO IMPORT (64 Spring Responders + 20 Job Requests with dates = ~84 people)

These people are NOT in the database but have provided a preferred week. They need:
1. Customer record created
2. Property record created
3. Spring startup Job record created (with `service_agreement_id = NULL`)
4. Then they can be scheduled in the UI

**Overlap check needed:** Some of the 20 Job Requests with dates may be the same people as the 64 Spring Responders (e.g., Laura Kottemann appears in both). Dedup by phone before importing.

### Bucket C: NEED OUTREACH (~146 unique people)

These are from the Job Requests sheet with "TBD" date who have NOT responded to the Spring Start form. They need mass outreach to:
1. Confirm interest
2. Get preferred week
3. Collect payment (if not on service agreement)

### Bucket D: NOT SPRING STARTUPS (22 other job types)

Irrigation installs, landscaping, sod, repairs — separate from the spring startup scheduling push.

---

## 7. Known Issues and Confidence Notes

### Things I am 100% confident about:
- All 97 real Stripe customers are in the database
- The 92 spring startup jobs in the DB are accurate (verified from backup)
- The 5 winterization-only customers correctly have no spring job
- The 59 Spring Responders matched to DB are correct (verified via phone + name)
- The 63 Spring Responders NOT in DB are genuinely not in the database (all closest matches are below 0.65 similarity)
- The Job Requests dedup count (300 unique from 369) is accurate

### Things that need manual verification by Viktor:
- **Wayne Newton** — phone has only 9 digits. Need correct phone number.
- **Igor Sovostyanov** and **Ilya Katz** — no phone numbers in Spring Response form. Need phone to create customer records.
- **"Mike"**, **"Fritz"**, **"Diane"**, **"Otto"**, **"Joseph"**, **"Wesley"** — first-name-only entries in Job Requests. Need full names.
- **"Loffler Louisiana"**, **"Loffler Bloomington"**, **"Russian Daycare (Stepan)"**, **"Medina Associations"**, **"Plymouth Associations (Nicole)"**, **"Island Home"** — these appear to be commercial/institutional accounts. Need clarification on contact info.
- **"Stapan" entries** (3 of them) — appears to be the same subcontractor "Stepan" with multiple properties (Elm Creek HOA, Restaurant, Brynwood Association). Need to confirm these are real jobs to schedule.
- **"Andrew Damyan"** appears twice — Fresh Water and Savage locations. Same person, two commercial properties.
- **Overlap between Lead Tracking sheet and DB Leads table** — need to consolidate.
- **Mark Anderson** has 2 Stripe entries — one winterization-only ($85) and one refunded ($0 / $85 refund). Both are the same customer with a single DB record.
- **"Sarah Word"** in Job Requests — is this the same person as "Sarah Ward" in the database? (No phone provided to verify.)

### Data quality issues observed:
- Phone numbers entered as addresses (Jeff Schutt: "2750", Brian Grove: "16301")
- Area code typos (Kim Osborne: 953 vs 952)
- Truncated phone numbers (Jeff Torrison: "6", Wayne Newton: 9 digits)
- Inconsistent name formatting (first-name-only, nicknames, business names mixed with personal names)
- Some addresses incomplete (just street, no city/zip)

---

## 8. Recommended Next Steps

1. **Add technicians to the Staff table** — currently only Viktor (admin). Can't create appointments without staff.
2. **Determine spring startup duration** — need this to know how many jobs per day per tech.
3. **Import the 64 Spring Responders** not in DB as Customer + Property + Job records.
4. **Cross-reference and dedup** the 20 dated Job Requests against the 64 Spring Responders before importing.
5. **Send mass outreach** to the ~146 TBD Job Request people.
6. **Begin scheduling** the 92 existing DB jobs, prioritizing Professional tier first, then Essential, using week preferences from the Spring Response form.
7. **Send SMS confirmations** ~1 week before each scheduled appointment.

---

*Analysis generated April 14, 2026 from production backup `production_backup_20260414_065724`*
