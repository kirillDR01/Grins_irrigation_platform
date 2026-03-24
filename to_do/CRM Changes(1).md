**Overall**:

* Removal all fake or test data   
* Remove all test/fake staff   
* Logs me out randomly even if I am using system 

**Dashboard**: general idea of how everything is looking 

* For the alert function, I want it to highlight what alert it is talking about. So when the alert says “One new job came in last night that needs something” and I click the alert and it takes me to the job section, it should highlight that job so I know which one it is talking about   
* Messages should only number any unread messages but I don’t want it to track if the messages were read, but if the messages have been addressed. So instead we can do something like “6 messages need to be addressed” or something like that.   
* Same thing with invoices, I don’t care how much have been completed, I just care how much pending invoices there are so just count how many invoices are pending.   
* For the new leads section, I also want it to highlight the leads that have been not contacted when I click that box   
* For job by status, let’s just track by the following. Same thing here, when I click these it should highlight those specific jobs so I know right away which jobs it is talking bout  
  * New Requests (Need to contact)  
  * Estimates   
  * Pending Approval  
  * To be scheduled   
  * In Progress  
  * Complete

**Customers**: Should be our one stop shop for all customer data 

* Add functionality to review and delete duplicates  
* Add ability to add custom notes for customer   
* Add ability to add custom photos for customer  
* Add ability to review invoice history   
* Add section for customer availability times 

**Leads**: This should be where all estimates live and stay before they turn into approved jobs. 

* Replace zip code with just their city (That’s all we really care about from high level) but make sure to collect their zip code and address to review when I click on their name. Essentially all their data that they input into the work request form on google forms or lead intake form needs to be collected and added within here. Review work request form for info on what needs to be collected   
* I want to have a functionality or tag that shows these items:  
  * If they need to be contacted   
  * If they need a estimate   
  * Estimate status (Pending approval or approved)   
  * Ability to reach out to all pending invoices to try to close   
  * Attachments under each customer of estimates provided and contracts to be signed. This is where I want to store all this data   
  * Ability for customer to review estimate and sign contract   
* Also, if a staff give a estimate to a client that needs approval, that customer should be added into the leads section until they approve the jobs  
* I want there to be estimate templates and contract templates within here that we  can shoot over to customer

**Work requests**:

* Honestly, I think we can remove this section as there are only two type of lead categories   
  * 1\. Request that need a estimates   
  * 2\. Requests that have been approved and turn into jobs 

**Jobs**: Should be all the jobs that are approved and need to be scheduled, should not have any jobs here that need to be scheduled. 

* There should be a notes under each job when you click in and also a field that summarizes the note. For example, if I have a repair job, I want to understand what the repair that I am doing is so I can estimate how much time I should need to complete it.   
* Should not have any status tags other then this:  
  * To be scheduled   
  * In progress  
  * Complete   
* Create filters so I can filter it based no what I want to see  
* Category column can probably be removed   
* Add customer name column   
* Add customer tag column   
* Replace created on column with something around the line of how long has It been by day since this job was added to the job list  
* Add column for by when it needs to be completed by:

**Schedule**: this is where the staff will be working in to start/complete jobs, send invoices, and send estimates   
	For creating as schedule: 

* Ability to reverse actions done when building schedule  (Incase someone accidentally clears a day)  
* Ability to drag and drop scheduled appointment when building schedule  
* Add a section that notes rough lead time for clients that ask   
* Hopefully ai will do this but if not for now, within the manually add job function I want to make sure I have these abilities to speed things Up:  
  * Pop up list of all jobs that I can filter based on Location and job type. Ability to pick a select amount of jobs at a time and put them on a specific date and staff.    
* I don’t like how when I click things like customer info it send me all the way to customer section in the crm and I need to go back to schedule after I review customer details.   
* Make it so on the calder slot it says: “Staff name \- Job Type”   
* Make sure property address Is auto uploaded based on customer information

	For staff: 

* Give function for staff to collect payment on site and update the data within the appointment slot of them collecting the payment (if already not collected)(Auto updats in customer data in Customer section within crm and invoicing section).  
* Give staff function to use a invoice template to create and send customer invoices on the spot with payment links (auto Updates this info in customer data within crm and invoicing section within crm   
* Give function for staff to be able to write up and provide a estimate via a template on the spot which gets updated to the lead section for us if customer does not approve it within 4 hours and make sure customer can get a push notification of estimate right away (Auto updated customer data in Customer section within crm and lead section in crm if needed )  
* Give functionality to staff to add Customer notes and photos (Auto update customer data in Customer section within crm)  
* Remove all customer tags here   
* Ability for customer to send a push notification via text to collect a google review   
* Ability for staff to select “On my way”, “Job started”, “Job Complete”. Couple notes here:  
  * Staff can’t complete a job until payment s collected or invoice is sent.   
  * System track time between those three buttons per job type and staff to collect meta data for future scheduling improvement (and whatever else that may be good to collect)   
* Remove “Mark as scheduled” from the action and release it with the bottoms and functionality mentioned above. 

**Generate routes**:

* May be better to have the functionality of this section within the schedule section but don’t give staff ability to generate routes?

**Invoice**: should be the place to review all pending, past do, and in complete invoices 

* Give functionality to filter invoices based on whatever I want   
* Track invoices per:  
  * Invoice number  
  * Cusomter name   
  * Job   
  * Cost   
  * Status (Complete, pending, past due)  
  * Days until due   
  * Days past due   
* Make sure complete is green, past due is red, and pending is yellow   
* Ability to mass notify customers that are past due, invoices that are about to be due, or lean notices   
* Make sure all invoicing data is updated to customer data within crm

---

## DATABASE / DATA MODEL GAPS IDENTIFIED (2026-03-23)

The following schema gaps must be resolved before the CRM changes above can be fully implemented.

### Overall
- Demo seed data migrations (`20250626_100000_seed_demo_data.py`, `20250627_100000_seed_staff_availability.py`) need to be rolled back or removed to clear fake data and staff.

### Dashboard
- No `messages` or `communications_tracking` table exists. The "Messages" widget currently shows customer counts, not message data. A communications table with an `is_addressed` (Boolean) field would be needed to track addressed vs. unaddressed messages.
- Invoice dashboard metric queries pull from job statuses instead of the actual `invoices` table. No schema change needed — just query fix.
- Job status navigation from dashboard requires frontend URL param handling, not a schema change.

### Customers
- `internal_notes` field EXISTS in the `customers` DB table but is NOT exposed in the `CustomerResponse`, `CustomerUpdate`, or `CustomerCreate` Pydantic schemas. Must be added to all three schemas so the API can read/write notes.
- `preferred_service_times` field EXISTS in DB and is returned in `CustomerResponse`, but is NOT in `CustomerUpdate` or `CustomerCreate` schemas. Must be added so staff can edit availability.
- No `photo_url` column on `customers` table. Need to add `photo_url` (String(500), nullable) AND set up an object storage service (S3 or similar) and a `documents`/`attachments` table for polymorphic file storage.
- `stripe_payment_method_id` column does not exist on `customers` table. Needed if "credit on file" charging is required.
- No dedicated duplicate review/merge admin panel — duplicate prevention (unique phone) exists but no merge capability. May need a `customer_merge_log` table.
- Invoice history is accessible via FK relationship but not displayed on the customer detail page — this is a frontend/query gap, not a schema gap.

### Leads
- `city` column DOES NOT EXIST on `leads` table. Only `zip_code` exists. Need to add `city` (String(100), nullable), `address` (String(255), nullable), and `state` (String(50), nullable, default 'MN') columns.
- `estimate_status` column DOES NOT EXIST on `leads` table. Need to add `estimate_status` (String(50), nullable) with values: needs_estimate, estimate_sent, pending_approval, approved, rejected.
- No `estimates` table exists anywhere in the database. Must create a full `estimates` table with lifecycle tracking (draft → sent → viewed → approved → rejected), line items, amounts, approval tokens, and document URLs. See gap_analysis.md for full schema.
- No `estimate_templates` table exists. Must create for reusable estimate templates with default line items.
- No `contract_templates` table exists. Must create for reusable contract templates.
- No `contracts` table exists. Must create for tracking contract signing lifecycle with customer-facing signing tokens.
- No `documents`/`attachments` table exists. Must create a polymorphic file storage table for attaching estimates, contracts, and other files to leads.
- `SentMessage.customer_id` is NOT NULL, which prevents sending any SMS (e.g., estimate notifications) to leads who haven't been converted to customers. Must make `customer_id` nullable and add `lead_id` (UUID FK→leads.id, nullable) column to `sent_messages` table. Also must update the CHECK constraint on `message_type` to include `lead_confirmation`.

### Work Requests
- Work Requests (`google_sheet_submissions` table) still exists as a separate entity. Consolidation with Leads is a design/routing decision — the schema can support it since submissions already promote to leads via `promoted_to_lead_id`.

### Jobs
- No `general_notes` (Text) column on `jobs` table. `description` exists but is used for the job type description. A separate persistent notes field is needed for staff to add ongoing summaries (e.g., "what the repair is").
- No `material_cost` or `labor_cost` (Numeric) columns on `jobs` table. Only `quoted_amount` and `final_amount` exist (revenue only). Needed for profit calculations.
- Job statuses currently include 7 values (requested, approved, scheduled, in_progress, completed, cancelled, closed). Requirement asks for only 3 (To be scheduled, In Progress, Complete). This is a design decision on whether to reduce the enum or relabel/remap existing statuses.
- Customer name, customer tag, and "days since added" columns are frontend display concerns — the FK relationships exist (`customer_id`), just need query joins and computed fields.

### Schedule
- `en_route_at` (DateTime) column DOES NOT EXIST on `appointments` table. Only `arrived_at` and `completed_at` exist. Must add `en_route_at` to support 3-phase time tracking for "On my way" → "Job started" → "Job Complete" buttons.
- `AppointmentStatus` backend enum is MISSING `en_route`, `no_show`, and `pending` values that the frontend uses. The DB CHECK constraint will reject these values. **`no_show` is a live bug** — the frontend `markNoShow()` function sends this status to the backend which will fail. Must add all three values to the Python enum AND create a migration to update the DB CHECK constraint.
- `payment_status` column DOES NOT EXIST on `appointments` table. Must add (values: pending, collected, invoiced, waived) to enforce "can't complete until payment collected or invoice sent."
- `invoice_id` FK DOES NOT EXIST on `appointments` table. Must add to link invoices created on-site to the specific appointment.
- No `documents`/`attachments` table for staff photo uploads during appointments. Must create.
- No `google_review_requests` table for tracking review solicitation via text. Must create.
- No `notification_schedules` table for automated notifications (estimate follow-ups, arrival ETAs, etc.). Must create.

### Invoices
- No `document_url` column on `invoices` table. Invoices are data-only DB records with no PDF generation or storage. Must add `document_url` (String(500), nullable) and implement PDF generation (WeasyPrint or similar).
- No `notification_schedules` table for automated recurring reminders (3 days before due, weekly after past due, lien warnings). Currently all reminders are manual one-off actions.
- No bulk/mass notification infrastructure. Individual invoice reminder endpoints exist but no batch operation endpoint.
