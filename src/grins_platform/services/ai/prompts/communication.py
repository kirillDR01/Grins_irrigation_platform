"""Communication prompts and templates for AI assistant.

Validates: AI Assistant Requirements 6.1
"""

COMMUNICATION_PROMPT = """Draft a customer communication message.

MESSAGE TYPES:
1. **appointment_confirmation** - Confirm scheduled appointment
2. **appointment_reminder** - Day-before reminder
3. **on_the_way** - Technician en route notification
4. **completion_summary** - Job completed summary
5. **follow_up** - Post-service follow-up
6. **estimate_ready** - Estimate is ready for review
7. **payment_reminder** - Invoice payment reminder

TONE GUIDELINES:
- Professional but friendly
- Concise (SMS-friendly length)
- Include essential details only
- Use customer's first name when available

REQUIRED ELEMENTS BY TYPE:
- Confirmation: Date, time window, service type
- Reminder: Date, time window, address confirmation
- On the way: ETA, technician name
- Completion: Work done, amount charged, payment status
- Follow-up: Thank you, review request, future service mention
"""

# Message templates with placeholders
TEMPLATES = {
    "appointment_confirmation": (
        "Hi {customer_name}! Your {service_type} appointment is confirmed for "
        "{date} between {time_window}. Reply YES to confirm or call us to reschedule."
    ),
    "appointment_reminder": (
        "Reminder: Your {service_type} appointment is tomorrow, {date}, "
        "between {time_window}. We'll text when our tech is on the way!"
    ),
    "on_the_way": (
        "Your technician {tech_name} is on the way! "
        "Expected arrival in approximately {eta} minutes."
    ),
    "completion_summary": (
        "Your {service_type} is complete! {work_summary} "
        "Total: ${amount}. Thank you for choosing Grin's Irrigation!"
    ),
    "follow_up": (
        "Hi {customer_name}! Thanks for choosing Grin's Irrigation. "
        "How was your service? We'd love a review: {review_link}"
    ),
    "estimate_ready": (
        "Hi {customer_name}! Your estimate for {service_type} is ready. "
        "Total: ${amount}. Reply YES to approve or call to discuss."
    ),
    "payment_reminder": (
        "Hi {customer_name}, this is a friendly reminder that invoice #{invoice_id} "
        "for ${amount} is due. Pay online: {payment_link}"
    ),
}
