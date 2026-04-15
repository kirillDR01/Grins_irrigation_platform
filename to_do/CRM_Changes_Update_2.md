**Overall**:

* I randomly get logged out. I was looking at customers details, went to a different tab in safari for 20 seconds, came back and had to relogin  
* Fix the sign in window period and login credentials so it more secure  

**Dashboard**: general idea of how everything is looking 

* For the alert function, I want it to highlight what alert it is talking about. So when the alert says “One new job came in last night that needs something” and I click the alert and it takes me to the job section, it should highlight that job for a brief moment so I know which one it is talking about   
* For the estimates shown in the dashboard, when I click into these estimates I cannot tell which lead needs a estimate. What I want to do here is separate leads that need to be contacted from leads that need a estimate. I want to replace the work request tab with the Sales Tab. I will funnel all leads that need an estimate into the Sales Tab and I will use the leads tab to only track the people that have not been contacted.   
* Remove “New Leads” Section in dashboard, not needed as I already have a section that i track this via the “Leads awaiting contact”

**Customers**: Should be our one stop shop for all customer data 

* Add functionality to review and delete duplicates not under each customer, but under the customer overview   
* For the service preferences, please make it so I can pick not just time, but dates also. Also please make it so that I can add multiple dates and times here. For example, i can add a date and time for spring start up and date and time for winterization  
* Add Property type to tag as either Residential, Subbed to us, HOA, or Commercial 

**Leads**: This should be where all new requests live before I contact them 

* Make sure I can delete customers and it auto deletes them from leads once I move them from the leads section into the jobs or sales tab.   
* Remove all coloring for the lead source and move this column aside towards the back. What I would rather see where the source column is, is the job requested so I can quickly understand what they want and then contact them without needing to click in   
* Add a column next to job address noting the city they are in as it will allow scheduling to be easier and quicker   
* Remove the column “Intake”  
* For status, lets just include the following tags only:  
  * New   
  * Contacted (Awaiting Response)  
  * Add a column that notes the last contacted date (based on when I click contacted). Once the messaging is set up, I would want it to auto update this section based on the text between client and I   
* Add functionality within to move this lead into a different tab:  
  * If job is confirmed and ready to schedule, have a button to move to job tab and auto generate a new customer  
  * If jobs needs us to provide them an estimate, add button to move to sales tab 

**Work requests**:

* Remove this section completely and replace it with sales tab 

**Sales:** This is where all leads that need an estimate will live. Every time I click the button to send a lead into the sales tab, they will live here.  

* I like the 4 boxes up top, lets leave it like that   
* Add a list of all the customers that need an estimate similar to how the leads tab looks. Within, I want these columns:  
  * Customer name  
  * Customer Number   
  * Customer address   
  * Job Type   
  * Status (Schedule Estimate, Estimate Scheduled, Send Estimate, Pending Approval, Send Contract)   
  * Column that shows last contact date similar to the leads tab   
* Add a separate scheduling calendar for sales use. It does not need to be as in depth as the job calendar for now and can just be a manual schedule builder   
* Add button to convert lead into a job that needs to be scheduled once lead approves and signs estimate   
* Under each lead,   
  * I want to have a documents section which includes all the documents that I have provided the customer   
  * Ability to send customer estimate to their email through the crm (I will create contract in other location for now)  
  * Ability to send customer contract & Estimate to sign through crm (I will create contract in other location for now)  
* Remove Estimate builder, media library, diagrams, follow up que, and estimates tabs within. I think for now we will make it work with a list view like we have it in the leads tab. It will take some time to develop this stuff and I will see if I can find something else that we can build our own version of when I have the time.   
* If a staff give a estimate to a client that needs approval, that customer should be added into the leads section until they approve the jobs

**Jobs**: Should be all the jobs that are approved and need to be scheduled, should not have any jobs here that need to be estimated. 

* Add Property type to tag as either Residential, Subbed to us, HOA, or Commercial   
* Instead of due by, let's make this column allow us to select which week out of the year for the job. I want to be able to add within a week a client select or it autopopulates ideally when the customer fills out the form. For example, if a customer has a spring start up they want to get done, I select “Week of 4/20” so I know this job needs to be scheduled for this week and the week prior I can select a specific date and time. In addition, we can pull data from customer info on special date preferences like “customer xx is only available on MWF after 1:00 Pm

**Schedule**: PLEASE LOOK AT SCHEDULING TASK IN ASANA 

	For admin only: The one that creates the schedule : 

* Hopefully ai will do this through generate routes tab but if I manually add job, I want to make sure I have these abilities to speed things Up:  
  * A pop up list that looks exactly how the list within the jobs tab looks with the same filtering functions with search functionality  
  * Ability to pick a select multiple amount of jobs at a time and put them on a specific date and staff. Should also have ability to select x amount of time/staff globally for all jobs selected   
  * I can tell the difference of unconfirmed vs confirmed jobs   
  * Send push notification to all clients to confirm the jobs with reply “Y” for yes, “R” Request different time (system follows up asking for a few requested dates and times), “C” for cancel. If they approve then it changes job from unconfirmed to confirmed, if R then it would let them know we will follow up with a new time shortly and on my end it will let me know what date they requested and I can try to reschedule, if C it removes the job request   
  * Once job is complete, it changes the job status to complete 

	For staff and admin: 

* Staff should see everything about the job as the admin can see but cant delete/remove job   
* Give function for staff to collect payment on site and update the data within the appointment slot of them collecting the payment (if already not collected)(Auto updates in customer data in Customer tab within crm and invoicing section).  
* Give staff function to use a invoice template to create and send customer invoices on the spot with payment links (auto Updates this info in customer tab within crm and invoicing section within crm   
* Give functionality to staff to add Customer notes and photos (Auto update customer data in Customer tab within crm)  
* Ability for customer to send a push notification via text to collect a google review   
* Ability for staff to select “On my way”, “Job started”, “Job Complete”. Couple notes here:  
  * Staff can’t complete a job until payment is collected or invoice is sent.   
  * System track time between those three buttons per job type and staff to collect meta data for future scheduling improvement (and whatever else that may be good to collect) 

	Issues Noted so far:

* I cannot invoice the customer   
* Cant mark the job as complete 

**Invoice (COULD NOT TEST AS IT REQUIRES A COMPLETE JOB AND I COULD NOT GET A JOB INTO COMPLETE STATUS** : should be the place to review all pending, past do, and in complete invoices 

* Give functionality to filter invoices based on whatever I want   
* Track invoices per:  
  * Invoice number  
  * Customer name   
  * Job   
  * Cost   
  * Status (Complete, pending, past due)  
  * Days until due   
  * Days past due   
  * Payment type   
* Make sure complete is green, past due is red, and pending is yellow and it collets    
* Ability to mass notify customers that are past due, invoices that are about to be due, or lean notices   
* Make sure all invoicing data is updated to customer data tab within crm 

**Other:** 

* For the package onboarding, lets allow them to select a week based on the service and it auto populates within the job tab   
* For service contract, it auto populates jobs for following year after renewal date 

**Generate routes**:

* Waiting for you to finish to test 

**Messaging**:

* Waiting for you to finish to test 

**Marketing:** 

* Waiting for you to finish to test (NOT AS IMPORTANT AS GENERATE ROUTES & MESSAGING)

**Accounting:** 

* Waiting for you to finish to test (NOT AS IMPORTANT AS GENERATE ROUTES & MESSAGING)

  