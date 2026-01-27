# AI Assistant User Guide for Viktor

## Welcome to Your AI Assistant!

This guide will help you use the AI features in Grin's Irrigation Platform to save time and make better decisions.

## What Can the AI Do?

Your AI assistant can help with:
1. **Answer business questions** - "How many jobs do we have this week?"
2. **Generate schedules** - Automatically batch jobs by location and type
3. **Categorize job requests** - Determine which jobs are ready to schedule
4. **Draft customer messages** - Create appointment confirmations and reminders
5. **Generate estimates** - Calculate pricing based on similar past jobs

**Important:** The AI recommends, but YOU always approve. Nothing happens automatically.

---

## 1. AI Chat - Ask Questions About Your Business

### Where to Find It
- Dashboard page, right side panel

### What You Can Ask
- "How many jobs do we have scheduled for tomorrow?"
- "Which customers haven't paid their invoices?"
- "Show me all spring startup jobs in Eden Prairie"
- "What's our revenue this month?"

### How to Use It
1. Type your question in the chat box
2. Press Enter or click Send
3. AI responds in real-time (you'll see it typing)
4. Ask follow-up questions - it remembers the conversation
5. Click "Clear Chat" to start fresh

### Tips
- Be specific: "jobs tomorrow" is better than "jobs"
- Use customer names: "John Doe's last appointment"
- The AI can see your data but won't make changes

---

## 2. AI Schedule Generation

### Where to Find It
- Schedule → Generate Schedule → "AI-Powered" tab

### What It Does
- Batches jobs by city (Eden Prairie, Plymouth, etc.)
- Groups similar job types together
- Assigns staff based on availability and skills
- Warns about equipment conflicts
- Estimates drive time between jobs

### How to Use It
1. Select date range (usually 1 week)
2. Choose which staff to include
3. Click "Generate Schedule"
4. Review the AI's proposed schedule
5. Check warnings (equipment conflicts, time issues)
6. **Choose an action:**
   - **Accept Schedule** - Apply it to your calendar
   - **Modify** - Make changes before accepting
   - **Regenerate** - Try again with different parameters

### What to Look For
- **Location batching:** Jobs in same city grouped together
- **Time windows:** 2-hour windows as you prefer
- **Equipment warnings:** Compressor needed for multiple jobs
- **Staff workload:** Balanced across team members

### Example
```
Monday, Feb 1
├─ Vas (Eden Prairie)
│  ├─ 9-11am: Spring Startup - John Doe (6 zones)
│  ├─ 11am-1pm: Spring Startup - Jane Smith (8 zones)
│  └─ 1-3pm: Tune-up - Bob Johnson (4 zones)
└─ Dad (Plymouth)
   ├─ 9-11am: Winterization - Alice Brown (5 zones)
   └─ 11am-1pm: Repair - Charlie Davis (broken head)

⚠️ Warning: Compressor needed for 2 jobs at 9am
```

---

## 3. AI Job Categorization

### Where to Find It
- Jobs page → "AI Categorize" button

### What It Does
- Looks at job description and customer history
- Determines if job is ready to schedule or needs estimate
- Suggests pricing based on similar past jobs
- Flags complex jobs that need site visits

### How to Use It
1. Go to Jobs page
2. Click "AI Categorize" button
3. AI analyzes all uncategorized jobs
4. Review results grouped by category:
   - **Ready to Schedule** (confidence >= 85%)
   - **Requires Estimate** (confidence < 85%)
5. **Choose an action:**
   - **Approve All Ready** - Move to scheduling
   - **Review Individually** - Check each one
   - **Bulk Actions** - Approve multiple at once

### Confidence Scores
- **90-100%:** Very confident, safe to approve
- **85-89%:** Confident, quick review recommended
- **70-84%:** Uncertain, manual review needed
- **Below 70%:** Complex job, definitely needs estimate

### Example
```
Ready to Schedule (2 jobs)
├─ Spring Startup - John Doe
│  Confidence: 95%
│  Suggested Price: $180 (6 zones × $30)
│  AI Note: "Standard system, straightforward startup"
└─ Winterization - Jane Smith
   Confidence: 88%
   Suggested Price: $150 (5 zones × $30)
   AI Note: "Regular customer, same service as last year"

Requires Estimate (1 job)
└─ New Installation - Bob Johnson
   Confidence: 45%
   AI Note: "Complex installation, needs site visit for accurate quote"
```

---

## 4. AI Communication Drafts

### Where to Find It
- Customer detail page → "Draft Message" button
- Job detail page → "Draft Message" button

### What It Does
- Creates professional SMS messages
- Uses customer's name and appointment details
- Adjusts tone for slow payers
- Keeps messages under 160 characters (1 SMS)

### Message Types
- **Appointment Confirmation:** "Hi John, your spring startup is scheduled..."
- **Appointment Reminder:** "Reminder: We'll be there tomorrow..."
- **Payment Reminder:** "Your invoice for $180 is now due..."
- **Follow-up:** "How did everything go with your service?"

### How to Use It
1. Open customer or job detail page
2. Click "Draft Message"
3. AI generates message based on context
4. Review the draft
5. **Choose an action:**
   - **Send Now** - Send immediately
   - **Edit** - Modify before sending
   - **Schedule for Later** - Set send time

### Special Features
- **Slow Payer Warning:** AI flags customers with payment history
- **Opt-in Check:** Won't send if customer hasn't opted in
- **Duplicate Prevention:** Won't send same message twice

### Example
```
Draft Message: Appointment Confirmation

To: John Doe (612-555-1234)
Message: "Hi John, your spring startup is scheduled for 
Saturday 2/1 between 9-11am. Reply YES to confirm."

AI Note: Customer is opted in for SMS
```

---

## 5. AI Estimate Generation

### Where to Find It
- Job detail page → "Generate Estimate" button (for jobs needing estimates)

### What It Does
- Analyzes property details (zone count, size, terrain)
- Finds similar completed jobs for reference
- Breaks down costs (materials, labor, equipment, margin)
- Recommends site visit if needed

### How to Use It
1. Open job detail page
2. Click "Generate Estimate"
3. AI calculates estimate based on:
   - Zone count
   - System type (standard/lake pump)
   - Property size
   - Similar past jobs
4. Review breakdown and similar jobs
5. **Choose an action:**
   - **Generate PDF** - Create formal estimate
   - **Schedule Site Visit** - If AI recommends it
   - **Adjust Quote** - Modify pricing

### What's Included
- **Materials:** Sprinkler heads, pipes, valves, etc.
- **Labor:** Installation time based on zone count
- **Equipment:** Pipe puller, skid steer if needed
- **Margin:** Your standard profit margin

### Example
```
AI-Generated Estimate

Property: 8 zones, 15,000 sq ft, standard system
Total Estimate: $5,600

Breakdown:
├─ Materials: $2,800
├─ Labor: $2,000 (16 hours × $125/hr)
├─ Equipment: $400 (pipe puller rental)
└─ Margin: $400 (7%)

Similar Jobs:
├─ Jane Smith - 8 zones - $5,400 (May 2024)
└─ Bob Johnson - 7 zones - $4,900 (June 2024)

AI Recommendation: "Recommend site visit due to complex terrain"
Confidence: 78%
```

---

## 6. Communications Queue

### Where to Find It
- Dashboard page, below Morning Briefing

### What It Shows
- **Pending:** Messages ready to send
- **Scheduled:** Messages scheduled for later
- **Sent Today:** Messages already sent
- **Failed:** Messages that didn't go through

### How to Use It
1. Review pending messages
2. **Bulk Actions:**
   - **Send All** - Send all pending at once
   - **Review** - Check each one individually
3. **Scheduled Messages:**
   - **Pause All** - Stop scheduled sends
   - Edit individual send times
4. **Failed Messages:**
   - **Retry** - Try sending again
   - Check error reason (not opted in, invalid phone, etc.)

### Filters
- Filter by message type (confirmation, reminder, payment)
- Search by customer name or phone number

---

## 7. Morning Briefing

### Where to Find It
- Dashboard page, top section

### What It Shows
- **Personalized greeting** based on time of day
- **Overnight requests:** New jobs that came in
- **Today's schedule:** Summary by staff member
- **Unconfirmed appointments:** Need customer confirmation
- **Pending communications:** Messages waiting to send
- **Outstanding invoices:** By aging (0-30, 31-60, 61-90, 90+ days)

### Quick Actions
- View all requests
- Generate schedule
- Send pending messages
- Review invoices

---

## 8. Usage and Costs

### Daily Limit
- **100 AI requests per day** per user
- Resets at midnight
- Check remaining requests in top right corner

### What Counts as a Request
- Each chat message
- Each schedule generation
- Each job categorization batch
- Each communication draft
- Each estimate generation

### Costs
- Estimated cost shown in Usage page
- Typical: $0.01-0.05 per request
- Monthly cost: ~$10-30 depending on usage

### Where to Check
- Dashboard → Usage tab
- Shows today's usage and monthly total

---

## Tips for Getting the Most Out of AI

### Do's
✅ Review AI recommendations before approving
✅ Use confidence scores to decide when to trust AI
✅ Check warnings on generated schedules
✅ Verify customer opt-in before sending messages
✅ Compare AI estimates with your experience

### Don'ts
❌ Don't blindly approve without reviewing
❌ Don't ignore low confidence scores
❌ Don't send messages to customers who haven't opted in
❌ Don't skip site visits when AI recommends them
❌ Don't rely on AI for complex custom jobs

---

## Troubleshooting

### "Rate limit exceeded"
- You've used 100 requests today
- Wait until midnight for reset
- Or prioritize most important tasks

### "AI service unavailable"
- Temporary issue with AI provider
- Try again in a few minutes
- System will work normally without AI

### "Customer not opted in"
- Customer hasn't agreed to receive SMS
- Call them instead
- Or ask them to opt in

### "Low confidence score"
- AI isn't sure about this job
- Review manually
- Consider site visit or more information

---

## Getting Help

### In-App Help
- Hover over ℹ️ icons for tooltips
- Click "?" button for context help

### Support
- Email: support@grinsirrigations.com
- Phone: (612) 555-0100
- Hours: Mon-Fri 8am-6pm

---

## Privacy and Security

- AI only sees your business data (customers, jobs, schedules)
- No data is shared with other companies
- All recommendations are logged for audit
- You can review AI decisions in Audit Logs page

---

**Remember:** The AI is your assistant, not your replacement. It helps you work faster and smarter, but you're always in control!
