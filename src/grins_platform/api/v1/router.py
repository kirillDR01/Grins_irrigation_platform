"""
API v1 router configuration.

This module sets up the main API v1 router and includes all sub-routers.

Validates: Requirement 10.5-10.7
"""

from fastapi import APIRouter

from grins_platform.api.v1.accounting import router as accounting_router
from grins_platform.api.v1.agreements import (
    compliance_router,
    dashboard_ext_router,
    router as agreements_router,
    tier_router as agreement_tiers_router,
)
from grins_platform.api.v1.ai import router as ai_router
from grins_platform.api.v1.ai_scheduling import router as ai_scheduling_router
from grins_platform.api.v1.alerts import router as alerts_router
from grins_platform.api.v1.analytics import router as analytics_router
from grins_platform.api.v1.appointment_attachments import (
    router as appointment_attachments_router,
)
from grins_platform.api.v1.appointments import router as appointments_router
from grins_platform.api.v1.audit import router as audit_router
from grins_platform.api.v1.auth import router as auth_router
from grins_platform.api.v1.callrail_webhooks import router as callrail_webhooks_router
from grins_platform.api.v1.campaign_responses import router as campaign_responses_router
from grins_platform.api.v1.campaigns import router as campaigns_router
from grins_platform.api.v1.chat import router as chat_router
from grins_platform.api.v1.checkout import router as checkout_router
from grins_platform.api.v1.communications import router as communications_v2_router
from grins_platform.api.v1.conflict_resolution import router as conflict_router
from grins_platform.api.v1.contract_renewals import (
    router as contract_renewals_router,
)
from grins_platform.api.v1.customers import router as customers_router
from grins_platform.api.v1.dashboard import router as dashboard_router
from grins_platform.api.v1.email import router as email_router
from grins_platform.api.v1.estimates import router as estimates_router
from grins_platform.api.v1.expenses import router as expenses_router
from grins_platform.api.v1.inbox import router as inbox_router
from grins_platform.api.v1.invoices import router as invoices_router
from grins_platform.api.v1.jobs import router as jobs_router
from grins_platform.api.v1.leads import router as leads_router
from grins_platform.api.v1.marketing import router as marketing_router
from grins_platform.api.v1.media import router as media_router
from grins_platform.api.v1.notifications import router as notifications_router
from grins_platform.api.v1.onboarding import router as onboarding_router
from grins_platform.api.v1.portal import router as portal_router
from grins_platform.api.v1.properties import router as properties_router
from grins_platform.api.v1.reschedule_requests import (
    router as reschedule_requests_router,
)
from grins_platform.api.v1.resend_webhooks import router as resend_webhooks_router
from grins_platform.api.v1.sales import router as sales_router
from grins_platform.api.v1.sales_pipeline import router as sales_pipeline_router
from grins_platform.api.v1.schedule import router as schedule_router
from grins_platform.api.v1.schedule_clear import router as schedule_clear_router
from grins_platform.api.v1.scheduling_alerts import (
    router as scheduling_alerts_router,
)
from grins_platform.api.v1.sent_messages import router as sent_messages_router
from grins_platform.api.v1.services import router as services_router
from grins_platform.api.v1.settings import router as settings_router
from grins_platform.api.v1.sheet_submissions import router as sheet_submissions_router
from grins_platform.api.v1.signwell_webhooks import router as signwell_webhooks_router
from grins_platform.api.v1.sms import (
    communications_router,
    router as sms_router,
)
from grins_platform.api.v1.staff import router as staff_router
from grins_platform.api.v1.staff_availability import router as staff_availability_router
from grins_platform.api.v1.staff_reassignment import router as reassignment_router
from grins_platform.api.v1.stripe_terminal import router as stripe_terminal_router
from grins_platform.api.v1.templates import router as templates_router
from grins_platform.api.v1.voice import router as voice_router
from grins_platform.api.v1.webauthn import router as webauthn_router
from grins_platform.api.v1.webhooks import router as webhooks_router

api_router = APIRouter(prefix="/api/v1")

# Mount the WebAuthn sub-router on the auth router *before* including auth in
# the api router — FastAPI snapshots routes at include-time.
auth_router.include_router(webauthn_router)

# Include authentication endpoints
api_router.include_router(auth_router)

# Include customer endpoints
api_router.include_router(
    customers_router,
    prefix="/customers",
    tags=["customers"],
)

# Include property endpoints (note: some routes are under /customers/{id}/properties)
api_router.include_router(
    properties_router,
    tags=["properties"],
)

# Include service offering endpoints
api_router.include_router(
    services_router,
    prefix="/services",
    tags=["services"],
)

# Include staff endpoints
api_router.include_router(
    staff_router,
    prefix="/staff",
    tags=["staff"],
)

# Include staff availability endpoints
api_router.include_router(
    staff_availability_router,
    prefix="/staff",
    tags=["staff-availability"],
)

# Include job endpoints
api_router.include_router(
    jobs_router,
    prefix="/jobs",
    tags=["jobs"],
)

# Include lead endpoints
api_router.include_router(
    leads_router,
    prefix="/leads",
    tags=["leads"],
)

# Include estimate endpoints (Req 48)
api_router.include_router(
    estimates_router,
    prefix="/estimates",
    tags=["estimates"],
)

# Include template endpoints (Req 17)
api_router.include_router(
    templates_router,
    prefix="/templates",
    tags=["templates"],
)

# Include appointment endpoints
api_router.include_router(
    appointments_router,
    prefix="/appointments",
    tags=["appointments"],
)

# Include dashboard endpoints
api_router.include_router(
    dashboard_router,
    prefix="/dashboard",
    tags=["dashboard"],
)

# Include schedule generation endpoints
api_router.include_router(
    schedule_router,
    tags=["schedule"],
)

# Include schedule clear endpoints
api_router.include_router(
    schedule_clear_router,
    tags=["schedule-clear"],
)

# Include reschedule requests endpoints (CRM Changes Update 2 Req 25)
api_router.include_router(
    reschedule_requests_router,
    tags=["reschedule-requests"],
)

# Include invoice endpoints
api_router.include_router(
    invoices_router,
    tags=["invoices"],
)

# Include conflict resolution endpoints
api_router.include_router(
    conflict_router,
    tags=["conflict-resolution"],
)

# Include staff reassignment endpoints
api_router.include_router(
    reassignment_router,
    tags=["staff-reassignment"],
)

# Include AI assistant endpoints
api_router.include_router(
    ai_router,
    tags=["ai-assistant"],
)

# Include SMS endpoints
api_router.include_router(
    sms_router,
    tags=["sms"],
)

# Include Communications endpoints
api_router.include_router(
    communications_router,
    tags=["communications"],
)

# Include Sheet Submissions endpoints
api_router.include_router(
    sheet_submissions_router,
    prefix="/sheet-submissions",
    tags=["sheet-submissions"],
)

# Include Stripe Webhook endpoints (excluded from CSRF)
api_router.include_router(
    webhooks_router,
    tags=["webhooks"],
)

# Include CallRail Webhook endpoints (excluded from CSRF)
api_router.include_router(
    callrail_webhooks_router,
    tags=["callrail-webhooks"],
)

# Include SignWell Webhook endpoints (excluded from CSRF)
api_router.include_router(
    signwell_webhooks_router,
    tags=["signwell-webhooks"],
)

# Include Resend Webhook endpoints (excluded from CSRF)
api_router.include_router(
    resend_webhooks_router,
    tags=["resend-webhooks"],
)

# Include Onboarding endpoints (public pre-checkout consent)
api_router.include_router(
    onboarding_router,
    tags=["onboarding"],
)

# Include Checkout endpoints (public Stripe session creation)
api_router.include_router(
    checkout_router,
    tags=["checkout"],
)

# Include Email endpoints (public unsubscribe)
api_router.include_router(
    email_router,
    tags=["email"],
)

# Include Portal endpoints (public, no auth — Req 16, 78)
api_router.include_router(
    portal_router,
    tags=["Portal"],
)

# Include Agreement endpoints (authenticated)
api_router.include_router(
    agreements_router,
    tags=["agreements"],
)

# Include Agreement Tier endpoints (authenticated)
api_router.include_router(
    agreement_tiers_router,
    tags=["agreement-tiers"],
)

# Include Compliance endpoints (authenticated)
api_router.include_router(
    compliance_router,
    tags=["compliance"],
)

# Include Dashboard extension endpoints (authenticated)
api_router.include_router(
    dashboard_ext_router,
    tags=["dashboard"],
)

# Include Sales endpoints (Req 47)
api_router.include_router(
    sales_router,
    prefix="/sales",
    tags=["sales"],
)

# Include Contract Renewals endpoints (CRM Changes Update 2 Req 31)
api_router.include_router(
    contract_renewals_router,
    tags=["contract-renewals"],
)

# Include Sales Pipeline endpoints (CRM Changes Update 2)
api_router.include_router(
    sales_pipeline_router,
    prefix="/sales",
    tags=["sales-pipeline"],
)

# Include Accounting endpoints (Req 52, 59, 61, 62)
api_router.include_router(
    accounting_router,
    prefix="/accounting",
    tags=["accounting"],
)

# Include Expense endpoints (Req 53, 60)
api_router.include_router(
    expenses_router,
    prefix="/expenses",
    tags=["expenses"],
)

# Include Campaign endpoints (Req 45)
api_router.include_router(
    campaigns_router,
    prefix="/campaigns",
    tags=["campaigns"],
)

# Include Campaign Response endpoints (Scheduling Poll Req 9, 10, 11)
api_router.include_router(
    campaign_responses_router,
    prefix="/campaigns",
    tags=["campaign-responses"],
)

# Include Marketing endpoints (Req 58, 63, 64, 65)
api_router.include_router(
    marketing_router,
    prefix="/marketing",
    tags=["marketing"],
)

# Include Communications v2 endpoints (Req 4)
api_router.include_router(
    communications_v2_router,
    prefix="/communications",
    tags=["communications-v2"],
)

# Include Chat endpoints (public, Req 43)
api_router.include_router(
    chat_router,
    prefix="/chat",
    tags=["chat"],
)

# Include Voice endpoints (public, Req 44)
api_router.include_router(
    voice_router,
    prefix="/voice",
    tags=["voice"],
)

# Include Media Library endpoints (Req 49)
api_router.include_router(
    media_router,
    prefix="/media",
    tags=["media"],
)

# Include Audit Log endpoints (Req 74)
api_router.include_router(
    audit_router,
    prefix="/audit-log",
    tags=["audit"],
)

# Include Sent Messages endpoints (Req 82)
api_router.include_router(
    sent_messages_router,
    prefix="/sent-messages",
    tags=["sent-messages"],
)

# Include Settings endpoints (Req 87)
api_router.include_router(
    settings_router,
    prefix="/settings",
    tags=["settings"],
)

# Include Analytics endpoints (Req 37)
api_router.include_router(
    analytics_router,
    prefix="/analytics",
    tags=["analytics"],
)

# Include Notifications endpoints (Req 39)
api_router.include_router(
    notifications_router,
    prefix="/notifications",
    tags=["notifications"],
)

# Include Stripe Terminal endpoints (Req 16)
api_router.include_router(
    stripe_terminal_router,
    tags=["stripe-terminal"],
)

# Include Alerts endpoints (bughunt H-5 — admin cancellation alert)
api_router.include_router(
    alerts_router,
    tags=["alerts"],
)

# Include unified Inbox endpoints (scheduling-gaps gap-16 v0)
api_router.include_router(
    inbox_router,
    tags=["inbox"],
)

# Include Appointment Attachments endpoints (april-16th-fixes-enhancements Req 10.5)
api_router.include_router(
    appointment_attachments_router,
    tags=["appointment-attachments"],
)

# Include AI Scheduling endpoints (ai-scheduling-system spec)
api_router.include_router(
    ai_scheduling_router,
    tags=["ai-scheduling"],
)

# Include Scheduling Alerts endpoints (ai-scheduling-system spec)
# Note: generic alerts_router is at /alerts; this is at /scheduling-alerts
api_router.include_router(
    scheduling_alerts_router,
    tags=["scheduling-alerts"],
)

__all__ = ["api_router"]
