"""NotificationService for automated customer notifications.

Handles day-of reminders, on-my-way, arrival, delay, completion,
invoice reminders, lien notifications, and lead confirmation SMS.

All notifications are consent-gated: SMS requires sms_opt_in=True,
email is always sent as fallback.

Reads time windows and reminder times from business_settings (Req 87.8).
Includes portal invoice link in invoice notifications (Req 84.7).

Validates: CRM Gap Closure Req 39.1, 39.2, 39.3, 39.4, 39.5, 39.6, 39.7, 39.8,
           46.1, 46.2, 46.3, 54.1, 54.2, 54.3, 54.5, 55.1, 55.2, 55.3, 55.4, 55.5,
           84.7, 87.8
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import TYPE_CHECKING
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import and_, select
from sqlalchemy.orm import selectinload

from grins_platform.log_config import LoggerMixin
from grins_platform.models.appointment import Appointment
from grins_platform.models.customer import Customer
from grins_platform.models.enums import (
    AppointmentStatus,
    InvoiceStatus,
    NotificationType,
)
from grins_platform.models.invoice import Invoice
from grins_platform.models.lead import Lead
from grins_platform.models.sent_message import SentMessage
from grins_platform.schemas.ai import MessageType

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from grins_platform.services.admin_config import AdminNotificationSettings
    from grins_platform.services.email_service import EmailService
    from grins_platform.services.invoice_portal_service import InvoicePortalService
    from grins_platform.services.settings_service import SettingsService
    from grins_platform.services.sms_service import SMSService

# Central Time zone for time-window gating
CT_TZ = ZoneInfo("America/Chicago")

# Time window for lead confirmation SMS (8AM-9PM CT)
SMS_WINDOW_START = time(8, 0)
SMS_WINDOW_END = time(21, 0)

# Invoice reminder thresholds
PRE_DUE_DAYS = 3
PAST_DUE_INTERVAL_DAYS = 7
LIEN_THRESHOLD_DAYS = 30

# Delay threshold in minutes
DELAY_THRESHOLD_MINUTES = 15


@dataclass
class InvoiceReminderSummary:
    """Summary of invoice reminder batch results."""

    pre_due_sent: int = 0
    past_due_sent: int = 0
    lien_sent: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class NotificationResult:
    """Result of a single notification send attempt."""

    sms_sent: bool = False
    sms_deferred: bool = False
    email_sent: bool = False
    message_id: UUID | None = None
    error: str | None = None


class NotificationService(LoggerMixin):
    """Service for automated customer notifications.

    All notifications are consent-gated:
    - SMS: only sent if customer.sms_opt_in is True
    - Email: always sent as fallback

    Validates: CRM Gap Closure Req 39, 46, 54, 55
    """

    DOMAIN = "notification"

    def __init__(
        self,
        sms_service: SMSService | None = None,
        email_service: EmailService | None = None,
        google_review_url: str = "",
        settings_service: SettingsService | None = None,
        invoice_portal_service: InvoicePortalService | None = None,
        admin_settings: AdminNotificationSettings | None = None,
    ) -> None:
        """Initialize NotificationService.

        Args:
            sms_service: SMSService instance for sending SMS.
            email_service: EmailService instance for sending email.
            google_review_url: Google Business review URL for completion notifications.
            settings_service: SettingsService for reading time windows (Req 87.8).
            invoice_portal_service: InvoicePortalService for portal links (Req 84.7).
            admin_settings: AdminNotificationSettings for admin alert recipient
                (H-5). If omitted, reads ``ADMIN_NOTIFICATION_EMAIL`` from env.
        """
        super().__init__()
        self.sms_service = sms_service
        self.email_service = email_service
        self.google_review_url = google_review_url
        self.settings_service = settings_service
        self.invoice_portal_service = invoice_portal_service
        self.admin_settings = admin_settings

    # ------------------------------------------------------------------ #
    # Settings helpers (Req 87.8)
    # ------------------------------------------------------------------ #

    async def _get_notification_settings(
        self,
        db: AsyncSession,
    ) -> dict[str, int | str]:
        """Read notification time windows and reminder times from business_settings.

        Falls back to module-level constants if settings_service is unavailable
        or the setting key doesn't exist.

        Validates: Req 87.8

        Returns:
            Dict with sms_window_start, sms_window_end,
            pre_due_reminder_days, past_due_interval_days,
            lien_threshold_days.
        """
        defaults: dict[str, int | str] = {
            "sms_window_start": "08:00",
            "sms_window_end": "21:00",
            "pre_due_reminder_days": PRE_DUE_DAYS,
            "past_due_interval_days": PAST_DUE_INTERVAL_DAYS,
            "lien_threshold_days": LIEN_THRESHOLD_DAYS,
        }

        if self.settings_service is not None:
            try:
                prefs = await self.settings_service.get_notification_prefs(db)
                defaults.update(prefs)
            except Exception as exc:
                self.logger.warning(
                    "notification.settings.load_failed",
                    error=str(exc),
                )

        return defaults

    def _get_portal_invoice_link(
        self,
        invoice: Invoice,
    ) -> str | None:
        """Get portal invoice link for an invoice if token exists.

        Validates: Req 84.7

        Args:
            invoice: Invoice model instance.

        Returns:
            Portal URL string or None if no token.
        """
        if (
            self.invoice_portal_service is not None
            and invoice.invoice_token is not None
        ):
            return self.invoice_portal_service.get_portal_invoice_url(
                str(invoice.invoice_token),
            )
        return None

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    async def _send_notification(
        self,
        db: AsyncSession,
        *,
        customer: Customer,
        notification_type: NotificationType,
        message_type: MessageType,
        subject: str,
        sms_body: str,
        email_body: str,
        appointment_id: UUID | None = None,
        job_id: UUID | None = None,
        lead_id: UUID | None = None,
    ) -> NotificationResult:
        """Send a notification via SMS (if consented) and email (always).

        Creates a SentMessage record for tracking.

        Validates: Req 39.8 — all notifications consent-gated.
        """
        result = NotificationResult()

        # --- SMS (consent-gated) ---
        if customer.sms_opt_in and self.sms_service is not None:
            try:
                from grins_platform.services.sms.recipient import (  # noqa: PLC0415
                    Recipient,
                )

                recipient = Recipient.from_customer(customer)
                sms_result = await self.sms_service.send_message(
                    recipient=recipient,
                    message=sms_body,
                    message_type=message_type,
                    consent_type="transactional",
                    job_id=job_id,
                    appointment_id=appointment_id,
                )
                result.sms_sent = sms_result.get("success", False)
                if sms_result.get("message_id"):
                    result.message_id = UUID(sms_result["message_id"])
            except Exception as exc:
                self.log_failed(
                    "send_sms",
                    error=exc,
                    notification_type=notification_type.value,
                    customer_id=str(customer.id),
                )
                result.error = str(exc)
        else:
            self.log_rejected(
                "send_sms",
                reason="sms_not_consented",
                notification_type=notification_type.value,
                customer_id=str(customer.id),
            )

        # --- Email (always as fallback) ---
        if customer.email and self.email_service is not None:
            try:
                from grins_platform.models.enums import EmailType  # noqa: PLC0415

                email_sent: bool = self.email_service._send_email(  # noqa: SLF001
                    to_email=customer.email,
                    subject=subject,
                    html_body=email_body,
                    email_type=notification_type.value,
                    classification=EmailType.TRANSACTIONAL,
                )
                result.email_sent = email_sent
            except Exception as exc:
                self.log_failed(
                    "send_email",
                    error=exc,
                    notification_type=notification_type.value,
                    customer_id=str(customer.id),
                )
                if result.error is None:
                    result.error = str(exc)

        # --- Create SentMessage record if no SMS record was created ---
        if result.message_id is None:
            try:
                sent_msg = SentMessage(
                    customer_id=customer.id,
                    lead_id=lead_id,
                    job_id=job_id,
                    appointment_id=appointment_id,
                    message_type=message_type.value,
                    message_content=sms_body,
                    recipient_phone=customer.phone,
                    delivery_status="sent" if result.email_sent else "failed",
                )
                db.add(sent_msg)
                await db.flush()
                result.message_id = sent_msg.id
            except Exception as exc:
                self.log_failed("create_sent_message", error=exc)

        return result

    async def _get_appointment_with_relations(
        self,
        db: AsyncSession,
        appointment_id: UUID,
    ) -> Appointment | None:
        """Load an appointment with its job and customer eagerly."""
        stmt = (
            select(Appointment)
            .options(
                selectinload(Appointment.job),  # type: ignore[arg-type]
                selectinload(Appointment.staff),  # type: ignore[arg-type]
            )
            .where(Appointment.id == appointment_id)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_customer_for_appointment(
        self,
        db: AsyncSession,
        appointment: Appointment,
    ) -> Customer | None:
        """Resolve the customer for an appointment via its job."""
        from grins_platform.models.job import Job  # noqa: PLC0415

        stmt = (
            select(Customer)
            .join(Job, Job.customer_id == Customer.id)
            .where(Job.id == appointment.job_id)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------ #
    # Public API — Appointment Notifications (Req 39)
    # ------------------------------------------------------------------ #

    async def send_day_of_reminders(self, db: AsyncSession) -> int:
        """Send day-of reminders for today's appointments at 7AM CT.

        Queries all appointments for today with status in
        (scheduled, confirmed) and sends SMS (if consented) + email.

        Returns:
            Count of notifications sent.

        Validates: Req 39.1, 39.7, 39.8
        """
        self.log_started("send_day_of_reminders")

        today = date.today()
        stmt = (
            select(Appointment)
            .options(
                selectinload(Appointment.job),  # type: ignore[arg-type]
                selectinload(Appointment.staff),  # type: ignore[arg-type]
            )
            .where(
                and_(
                    Appointment.scheduled_date == today,
                    Appointment.status.in_(
                        [
                            AppointmentStatus.SCHEDULED.value,
                            AppointmentStatus.CONFIRMED.value,
                        ],
                    ),
                ),
            )
        )
        result = await db.execute(stmt)
        appointments = list(result.scalars().all())

        sent_count = 0
        for appt in appointments:
            customer = await self._get_customer_for_appointment(db, appt)
            if customer is None:
                self.log_rejected(
                    "send_day_of_reminders",
                    reason="customer_not_found",
                    appointment_id=str(appt.id),
                )
                continue

            staff_name = ""
            if appt.staff is not None:
                staff_name = getattr(appt.staff, "name", "your technician")

            from grins_platform.services.sms.formatters import (  # noqa: PLC0415
                format_sms_time_12h,
            )

            window_start = format_sms_time_12h(appt.time_window_start)
            window_end = format_sms_time_12h(appt.time_window_end)

            sms_body = (
                f"Reminder: You have an appointment today with "
                f"Grins Irrigation between {window_start} and "
                f"{window_end}. {staff_name} will be your technician."
            )
            email_body = (
                f"<p>This is a reminder that you have an appointment "
                f"scheduled today with Grins Irrigation.</p>"
                f"<p><strong>Time window:</strong> {window_start} - "
                f"{window_end}</p>"
                f"<p><strong>Technician:</strong> {staff_name}</p>"
            )

            notif_result = await self._send_notification(
                db,
                customer=customer,
                notification_type=NotificationType.DAY_OF_REMINDER,
                message_type=MessageType.APPOINTMENT_REMINDER,
                subject="Appointment Reminder — Grins Irrigation",
                sms_body=sms_body,
                email_body=email_body,
                appointment_id=appt.id,
                job_id=appt.job_id,
            )
            if notif_result.sms_sent or notif_result.email_sent:
                sent_count += 1

        self.log_completed(
            "send_day_of_reminders",
            sent_count=sent_count,
            total_appointments=len(appointments),
        )
        return sent_count

    async def send_on_my_way(
        self,
        db: AsyncSession,
        appointment_id: UUID,
        eta_minutes: int | None = None,
    ) -> NotificationResult:
        """Send 'on my way' notification with staff name and ETA.

        Args:
            db: Database session.
            appointment_id: The appointment ID.
            eta_minutes: Estimated travel time in minutes (from Google Maps).

        Returns:
            NotificationResult with send status.

        Validates: Req 39.2
        """
        self.log_started(
            "send_on_my_way",
            appointment_id=str(appointment_id),
        )

        appt = await self._get_appointment_with_relations(db, appointment_id)
        if appt is None:
            self.log_rejected(
                "send_on_my_way",
                reason="appointment_not_found",
                appointment_id=str(appointment_id),
            )
            return NotificationResult(error="Appointment not found")

        customer = await self._get_customer_for_appointment(db, appt)
        if customer is None:
            self.log_rejected(
                "send_on_my_way",
                reason="customer_not_found",
                appointment_id=str(appointment_id),
            )
            return NotificationResult(error="Customer not found")

        staff_name = ""
        if appt.staff is not None:
            staff_name = getattr(appt.staff, "name", "Your technician")

        eta_text = ""
        if eta_minutes is not None:
            eta_text = f" Estimated arrival in {eta_minutes} minutes."

        sms_body = (
            f"{staff_name} from Grins Irrigation is on the way to "
            f"your appointment!{eta_text}"
        )
        email_body = (
            f"<p><strong>{staff_name}</strong> from Grins Irrigation "
            f"is on the way to your appointment.</p>"
            f"<p>{eta_text.strip()}</p>"
        )

        result = await self._send_notification(
            db,
            customer=customer,
            notification_type=NotificationType.ON_MY_WAY,
            message_type=MessageType.ON_THE_WAY,
            subject="Your Technician Is On The Way — Grins Irrigation",
            sms_body=sms_body,
            email_body=email_body,
            appointment_id=appt.id,
            job_id=appt.job_id,
        )

        self.log_completed(
            "send_on_my_way",
            appointment_id=str(appointment_id),
            sms_sent=result.sms_sent,
            email_sent=result.email_sent,
        )
        return result

    async def send_arrival_notification(
        self,
        db: AsyncSession,
        appointment_id: UUID,
    ) -> NotificationResult:
        """Send notification confirming technician has arrived.

        Validates: Req 39.3
        """
        self.log_started(
            "send_arrival_notification",
            appointment_id=str(appointment_id),
        )

        appt = await self._get_appointment_with_relations(db, appointment_id)
        if appt is None:
            self.log_rejected(
                "send_arrival_notification",
                reason="appointment_not_found",
                appointment_id=str(appointment_id),
            )
            return NotificationResult(error="Appointment not found")

        customer = await self._get_customer_for_appointment(db, appt)
        if customer is None:
            return NotificationResult(error="Customer not found")

        staff_name = ""
        if appt.staff is not None:
            staff_name = getattr(appt.staff, "name", "Your technician")

        sms_body = (
            f"{staff_name} from Grins Irrigation has arrived for your appointment."
        )
        email_body = (
            f"<p><strong>{staff_name}</strong> from Grins Irrigation "
            f"has arrived for your scheduled appointment.</p>"
        )

        result = await self._send_notification(
            db,
            customer=customer,
            notification_type=NotificationType.ARRIVAL,
            message_type=MessageType.ARRIVAL,
            subject="Your Technician Has Arrived — Grins Irrigation",
            sms_body=sms_body,
            email_body=email_body,
            appointment_id=appt.id,
            job_id=appt.job_id,
        )

        self.log_completed(
            "send_arrival_notification",
            appointment_id=str(appointment_id),
        )
        return result

    async def send_delay_notification(
        self,
        db: AsyncSession,
        appointment_id: UUID,
        new_eta: datetime | None = None,
    ) -> NotificationResult:
        """Send delay notification when appointment runs >15min past end.

        Args:
            db: Database session.
            appointment_id: The appointment ID.
            new_eta: Updated estimated completion time.

        Validates: Req 39.4
        """
        self.log_started(
            "send_delay_notification",
            appointment_id=str(appointment_id),
        )

        appt = await self._get_appointment_with_relations(db, appointment_id)
        if appt is None:
            return NotificationResult(error="Appointment not found")

        customer = await self._get_customer_for_appointment(db, appt)
        if customer is None:
            return NotificationResult(error="Customer not found")

        eta_text = ""
        if new_eta is not None:
            from grins_platform.services.sms.formatters import (  # noqa: PLC0415
                format_sms_time_12h,
            )

            eta_text = (
                f" We now expect to finish around "
                f"{format_sms_time_12h(new_eta.time())}."
            )

        sms_body = (
            f"Your Grins Irrigation appointment is running a bit "
            f"longer than expected. We apologize for the delay.{eta_text}"
        )
        email_body = (
            f"<p>Your Grins Irrigation appointment is running longer "
            f"than expected. We apologize for the inconvenience.</p>"
            f"<p>{eta_text.strip()}</p>"
        )

        result = await self._send_notification(
            db,
            customer=customer,
            notification_type=NotificationType.DELAY,
            message_type=MessageType.CUSTOM,
            subject="Appointment Update — Grins Irrigation",
            sms_body=sms_body,
            email_body=email_body,
            appointment_id=appt.id,
            job_id=appt.job_id,
        )

        self.log_completed(
            "send_delay_notification",
            appointment_id=str(appointment_id),
        )
        return result

    async def send_completion_notification(
        self,
        db: AsyncSession,
        appointment_id: UUID,
        invoice_url: str | None = None,
    ) -> NotificationResult:
        """Send completion notification with job summary, invoice link, review link.

        Validates: Req 39.5
        """
        self.log_started(
            "send_completion_notification",
            appointment_id=str(appointment_id),
        )

        appt = await self._get_appointment_with_relations(db, appointment_id)
        if appt is None:
            return NotificationResult(error="Appointment not found")

        customer = await self._get_customer_for_appointment(db, appt)
        if customer is None:
            return NotificationResult(error="Customer not found")

        job_summary = ""
        if appt.job is not None:
            job_summary = getattr(appt.job, "summary", "") or ""

        invoice_text = ""
        if invoice_url:
            invoice_text = f" View your invoice: {invoice_url}"

        review_text = ""
        if self.google_review_url:
            review_text = f" We'd love your feedback: {self.google_review_url}"

        sms_body = (
            f"Your Grins Irrigation appointment is complete! "
            f"{job_summary}{invoice_text}{review_text}"
        ).strip()

        email_parts = [
            "<p>Your Grins Irrigation appointment has been completed.</p>",
        ]
        if job_summary:
            email_parts.append(f"<p>{job_summary}</p>")
        if invoice_url:
            email_parts.append(
                '<p><a href="' + invoice_url + '">View Invoice</a></p>',
            )
        if self.google_review_url:
            email_parts.append(
                '<p><a href="' + self.google_review_url + '">Leave a Review</a></p>',
            )
        email_body = "".join(email_parts)

        result = await self._send_notification(
            db,
            customer=customer,
            notification_type=NotificationType.COMPLETION,
            message_type=MessageType.COMPLETION,
            subject="Appointment Complete — Grins Irrigation",
            sms_body=sms_body,
            email_body=email_body,
            appointment_id=appt.id,
            job_id=appt.job_id,
        )

        self.log_completed(
            "send_completion_notification",
            appointment_id=str(appointment_id),
        )
        return result

    # ------------------------------------------------------------------ #
    # Invoice Reminders (Req 54, 55)
    # ------------------------------------------------------------------ #

    async def send_invoice_reminders(
        self,
        db: AsyncSession,
    ) -> InvoiceReminderSummary:
        """Daily job: send pre-due, past-due, and lien invoice reminders.

        Reads reminder thresholds from business_settings (Req 87.8).
        Includes portal invoice link in notifications (Req 84.7).

        - Pre-due: N days before due_date, if not already sent.
        - Past-due: weekly after due_date.
        - Lien: N days past due for lien-eligible invoices.

        Returns:
            InvoiceReminderSummary with counts.

        Validates: Req 54.1, 54.2, 54.3, 54.5, 55.1, 55.2, 55.3, 55.4, 55.5,
                   84.7, 87.8
        """
        self.log_started("send_invoice_reminders")
        summary = InvoiceReminderSummary()
        today = date.today()
        now = datetime.now(tz=CT_TZ)

        # Read configurable thresholds from business_settings (Req 87.8)
        notif_settings = await self._get_notification_settings(db)
        pre_due_days = int(notif_settings.get("pre_due_reminder_days", PRE_DUE_DAYS))
        past_due_interval = int(
            notif_settings.get("past_due_interval_days", PAST_DUE_INTERVAL_DAYS),
        )
        lien_threshold = int(
            notif_settings.get("lien_threshold_days", LIEN_THRESHOLD_DAYS),
        )

        # Query all unpaid invoices (sent, viewed, overdue, partial)
        unpaid_statuses = [
            InvoiceStatus.SENT.value,
            InvoiceStatus.VIEWED.value,
            InvoiceStatus.OVERDUE.value,
            InvoiceStatus.PARTIAL.value,
        ]
        stmt = (
            select(Invoice)
            .options(selectinload(Invoice.customer))  # type: ignore[arg-type]
            .where(Invoice.status.in_(unpaid_statuses))
        )
        result = await db.execute(stmt)
        invoices = list(result.scalars().all())

        for invoice in invoices:
            customer = invoice.customer
            if customer is None:
                summary.skipped += 1
                continue

            days_until_due = (invoice.due_date - today).days
            days_past_due = -days_until_due  # positive when past due

            try:
                # --- Pre-due reminder (configurable days before) ---
                if (
                    0 < days_until_due <= pre_due_days
                    and invoice.pre_due_reminder_sent_at is None
                ):
                    await self._send_pre_due_reminder(
                        db,
                        invoice,
                        customer,
                    )
                    invoice.pre_due_reminder_sent_at = now
                    summary.pre_due_sent += 1

                # --- Past-due weekly reminder ---
                elif days_past_due > 0 and days_past_due < lien_threshold:
                    should_send = self._should_send_past_due(
                        invoice,
                        today,
                        interval_days=past_due_interval,
                    )
                    if should_send:
                        await self._send_past_due_reminder(
                            db,
                            invoice,
                            customer,
                        )
                        invoice.last_past_due_reminder_at = now
                        summary.past_due_sent += 1

                # --- Lien warning (configurable days past due) ---
                elif (
                    days_past_due >= lien_threshold
                    and invoice.lien_eligible
                    and invoice.lien_warning_sent is None
                ):
                    await self._send_lien_notification(
                        db,
                        invoice,
                        customer,
                    )
                    invoice.lien_warning_sent = now
                    invoice.status = InvoiceStatus.LIEN_WARNING.value
                    summary.lien_sent += 1

                else:
                    summary.skipped += 1

            except Exception as exc:
                summary.failed += 1
                summary.errors.append(
                    f"Invoice {invoice.invoice_number}: {exc}",
                )
                self.log_failed(
                    "send_invoice_reminders",
                    error=exc,
                    invoice_id=str(invoice.id),
                )

        await db.flush()

        self.log_completed(
            "send_invoice_reminders",
            pre_due_sent=summary.pre_due_sent,
            past_due_sent=summary.past_due_sent,
            lien_sent=summary.lien_sent,
            skipped=summary.skipped,
            failed=summary.failed,
        )
        return summary

    def _should_send_past_due(
        self,
        invoice: Invoice,
        today: date,
        *,
        interval_days: int = PAST_DUE_INTERVAL_DAYS,
    ) -> bool:
        """Check if a past-due reminder should be sent (configurable interval)."""
        if invoice.last_past_due_reminder_at is None:
            return True
        last_sent_date = invoice.last_past_due_reminder_at.date()
        days_since_last = (today - last_sent_date).days
        return days_since_last >= interval_days

    async def _send_pre_due_reminder(
        self,
        db: AsyncSession,
        invoice: Invoice,
        customer: Customer,
    ) -> NotificationResult:
        """Send pre-due invoice reminder with portal link.

        Validates: Req 54.2, 84.7
        """
        portal_link = self._get_portal_invoice_link(invoice)
        portal_text = ""
        portal_html = ""
        if portal_link:
            portal_text = f" View your invoice: {portal_link}"
            portal_html = f'<p><a href="{portal_link}">View Invoice</a></p>'

        sms_body = (
            f"Your invoice {invoice.invoice_number} for "
            f"${invoice.total_amount} is due on "
            f"{invoice.due_date.strftime('%B %d, %Y')}.{portal_text}"
        )
        email_body = (
            f"<p>This is a friendly reminder that your invoice "
            f"<strong>{invoice.invoice_number}</strong> for "
            f"<strong>${invoice.total_amount}</strong> is due on "
            f"<strong>{invoice.due_date.strftime('%B %d, %Y')}</strong>.</p>"
            f"<p>Please arrange payment at your earliest convenience.</p>"
            f"{portal_html}"
        )

        self.logger.info(
            "notification.invoice.pre_due_sent",
            invoice_id=str(invoice.id),
            invoice_number=invoice.invoice_number,
            customer_id=str(customer.id),
        )

        return await self._send_notification(
            db,
            customer=customer,
            notification_type=NotificationType.INVOICE_PRE_DUE,
            message_type=MessageType.PAYMENT_REMINDER,
            subject=f"Invoice {invoice.invoice_number} Due Soon",
            sms_body=sms_body,
            email_body=email_body,
            job_id=invoice.job_id,
        )

    async def _send_past_due_reminder(
        self,
        db: AsyncSession,
        invoice: Invoice,
        customer: Customer,
    ) -> NotificationResult:
        """Send past-due invoice reminder with portal link.

        Validates: Req 54.3, 84.7
        """
        portal_link = self._get_portal_invoice_link(invoice)
        portal_text = ""
        portal_html = ""
        if portal_link:
            portal_text = f" View and pay: {portal_link}"
            portal_html = f'<p><a href="{portal_link}">View and Pay Invoice</a></p>'

        sms_body = (
            f"Your invoice {invoice.invoice_number} for "
            f"${invoice.total_amount} is past due. "
            f"Please pay at your earliest convenience.{portal_text}"
        )
        email_body = (
            f"<p>Your invoice <strong>{invoice.invoice_number}</strong> "
            f"for <strong>${invoice.total_amount}</strong> is past due.</p>"
            f"<p>Please arrange payment at your earliest convenience "
            f"to avoid additional fees.</p>"
            f"{portal_html}"
        )

        self.logger.info(
            "notification.invoice.past_due_sent",
            invoice_id=str(invoice.id),
            invoice_number=invoice.invoice_number,
            customer_id=str(customer.id),
        )

        return await self._send_notification(
            db,
            customer=customer,
            notification_type=NotificationType.INVOICE_PAST_DUE,
            message_type=MessageType.PAYMENT_REMINDER,
            subject=f"Invoice {invoice.invoice_number} Past Due",
            sms_body=sms_body,
            email_body=email_body,
            job_id=invoice.job_id,
        )

    async def _send_lien_notification(
        self,
        db: AsyncSession,
        invoice: Invoice,
        customer: Customer,
    ) -> NotificationResult:
        """Send formal lien notification at 30 days past due with portal link.

        Validates: Req 55.2, 55.3, 55.4, 55.5, 84.7
        """
        # Resolve property address from customer
        address = "the service property"
        if customer.properties:
            prop = customer.properties[0]
            prop_address = getattr(prop, "address", None)
            if prop_address:
                address = str(prop_address)

        lien_deadline = invoice.due_date + timedelta(days=90)

        portal_link = self._get_portal_invoice_link(invoice)
        portal_text = ""
        portal_html = ""
        if portal_link:
            portal_text = f" Pay now: {portal_link}"
            portal_html = f'<p><a href="{portal_link}">Pay Invoice Now</a></p>'

        sms_body = (
            f"IMPORTANT: Invoice {invoice.invoice_number} for "
            f"${invoice.total_amount} is 30+ days past due. "
            f"A lien may be filed against {address} if payment "
            f"is not received by {lien_deadline.strftime('%B %d, %Y')}."
            f"{portal_text}"
        )
        email_body = (
            f"<p><strong>Formal Lien Notice</strong></p>"
            f"<p>Invoice <strong>{invoice.invoice_number}</strong> for "
            f"<strong>${invoice.total_amount}</strong> is more than "
            f"30 days past due.</p>"
            f"<p><strong>Property:</strong> {address}</p>"
            f"<p><strong>Invoice Amount:</strong> ${invoice.total_amount}</p>"
            f"<p><strong>Lien Filing Deadline:</strong> "
            f"{lien_deadline.strftime('%B %d, %Y')}</p>"
            f"<p>Please arrange immediate payment to avoid a lien "
            f"being filed against the property.</p>"
            f"{portal_html}"
        )

        self.logger.info(
            "notification.invoice.lien_warning_sent",
            invoice_id=str(invoice.id),
            invoice_number=invoice.invoice_number,
            customer_id=str(customer.id),
            property_address=address,
        )

        return await self._send_notification(
            db,
            customer=customer,
            notification_type=NotificationType.INVOICE_LIEN,
            message_type=MessageType.PAYMENT_REMINDER,
            subject=f"Formal Lien Notice — Invoice {invoice.invoice_number}",
            sms_body=sms_body,
            email_body=email_body,
            job_id=invoice.job_id,
        )

    # ------------------------------------------------------------------ #
    # Lead Confirmation SMS (Req 46)
    # ------------------------------------------------------------------ #

    async def send_lead_confirmation_sms(
        self,
        db: AsyncSession,
        lead_id: UUID,
    ) -> bool:
        """Send SMS confirmation for new lead submissions.

        Gated on:
        1. sms_consent must be True on the lead.
        2. Time window from business_settings (Req 87.8), default 8AM-9PM CT.

        Returns:
            True if sent or deferred, False if skipped.

        Validates: Req 46.1, 46.2, 46.3, 87.8
        """
        self.log_started("send_lead_confirmation_sms", lead_id=str(lead_id))

        stmt = select(Lead).where(Lead.id == lead_id)
        result = await db.execute(stmt)
        lead = result.scalar_one_or_none()

        if lead is None:
            self.log_rejected(
                "send_lead_confirmation_sms",
                reason="lead_not_found",
                lead_id=str(lead_id),
            )
            return False

        # Gate 1: SMS consent
        if not lead.sms_consent:
            self.log_rejected(
                "send_lead_confirmation_sms",
                reason="sms_not_consented",
                lead_id=str(lead_id),
            )
            return False

        # Gate 2: Time window from business_settings (Req 87.8)
        notif_settings = await self._get_notification_settings(db)
        sms_start_str = str(notif_settings.get("sms_window_start", "08:00"))
        sms_end_str = str(notif_settings.get("sms_window_end", "21:00"))

        try:
            sms_start_parts = sms_start_str.split(":")
            sms_start = time(int(sms_start_parts[0]), int(sms_start_parts[1]))
        except (ValueError, IndexError):
            sms_start = SMS_WINDOW_START

        try:
            sms_end_parts = sms_end_str.split(":")
            sms_end = time(int(sms_end_parts[0]), int(sms_end_parts[1]))
        except (ValueError, IndexError):
            sms_end = SMS_WINDOW_END

        now_ct = datetime.now(CT_TZ)
        if not (sms_start <= now_ct.time() < sms_end):
            # Defer — compute next window start
            if now_ct.time() >= sms_end:
                next_day = now_ct.date() + timedelta(days=1)
            else:
                next_day = now_ct.date()
            scheduled_at = datetime.combine(
                next_day,
                sms_start,
                tzinfo=CT_TZ,
            )

            # Create a deferred SentMessage record
            sent_msg = SentMessage(
                lead_id=lead.id,
                message_type=MessageType.LEAD_CONFIRMATION.value,
                message_content=(
                    "Thanks for reaching out to Grins Irrigation! "
                    "We received your request and will be in touch soon."
                ),
                recipient_phone=lead.phone,
                delivery_status="scheduled",
                scheduled_for=scheduled_at,
            )
            db.add(sent_msg)
            await db.flush()

            self.logger.info(
                "notification.lead.confirmation_deferred",
                lead_id=str(lead_id),
                scheduled_for=scheduled_at.isoformat(),
            )
            return True

        # Send immediately
        sms_body = (
            "Thanks for reaching out to Grins Irrigation! "
            "We received your request and will be in touch soon."
        )

        if self.sms_service is not None:
            try:
                await self.sms_service.send_automated_message(
                    phone=lead.phone,
                    message=sms_body,
                    message_type="automated",
                )
            except Exception as exc:
                self.log_failed(
                    "send_lead_confirmation_sms",
                    error=exc,
                    lead_id=str(lead_id),
                )
                return False

        # Create SentMessage record for tracking
        sent_msg = SentMessage(
            lead_id=lead.id,
            message_type=MessageType.LEAD_CONFIRMATION.value,
            message_content=sms_body,
            recipient_phone=lead.phone,
            delivery_status="sent",
            sent_at=datetime.now(tz=CT_TZ),
        )
        db.add(sent_msg)
        await db.flush()

        self.logger.info(
            "notification.lead.confirmation_sent",
            lead_id=str(lead_id),
        )
        self.log_completed(
            "send_lead_confirmation_sms",
            lead_id=str(lead_id),
        )
        return True

    # ------------------------------------------------------------------ #
    # Admin Alerts (bughunt H-5)
    # ------------------------------------------------------------------ #

    async def send_admin_cancellation_alert(
        self,
        db: AsyncSession,
        *,
        appointment_id: UUID,
        customer_id: UUID,
        customer_name: str,
        scheduled_at: datetime,
        source: str = "customer_sms",
    ) -> None:
        """Notify admin that a customer cancelled an appointment via SMS.

        Dispatches an email to ``ADMIN_NOTIFICATION_EMAIL`` (via the
        existing :class:`EmailService`) **and** persists an :class:`Alert`
        row the dashboard surfaces via ``GET /api/v1/alerts``.

        Per D-4 (2026-04-16): *both* channels, because email can fail
        silently and the dashboard gives an always-visible fallback.

        Failures are logged and swallowed — admin notification must never
        block the customer-facing SMS reply.

        Args:
            db: Active database session (used to persist the Alert row).
            appointment_id: UUID of the cancelled appointment.
            customer_id: UUID of the cancelling customer.
            customer_name: Human-readable customer name for the message
                body.
            scheduled_at: Original scheduled start time.
            source: How the cancellation was received (default
                ``"customer_sms"``; callers may pass other tokens for
                forward compatibility).

        Validates: bughunt 2026-04-16 finding H-5
        """
        self.log_started(
            "send_admin_cancellation_alert",
            appointment_id=str(appointment_id),
            customer_id=str(customer_id),
            source=source,
        )

        message = (
            f"{customer_name} cancelled via {source} for "
            f"{scheduled_at:%Y-%m-%d %H:%M}"
        )

        # --- Email dispatch (uses existing EmailService._send_email) ---
        try:
            recipient = self._get_admin_notification_email()
            if recipient and self.email_service is not None:
                from grins_platform.models.enums import (  # noqa: PLC0415
                    EmailType,
                )

                subject = (
                    f"Customer cancelled appointment — {customer_name} "
                    f"({scheduled_at:%Y-%m-%d %H:%M})"
                )
                html_body = (
                    f"<p><strong>{customer_name}</strong> cancelled their "
                    f"appointment via {source}.</p>"
                    f"<p><strong>Scheduled for:</strong> "
                    f"{scheduled_at:%Y-%m-%d %H:%M}</p>"
                    f"<p><strong>Appointment ID:</strong> "
                    f"{appointment_id}</p>"
                    f"<p><strong>Customer ID:</strong> {customer_id}</p>"
                )
                self.email_service._send_email(  # noqa: SLF001
                    to_email=recipient,
                    subject=subject,
                    html_body=html_body,
                    email_type=NotificationType.CAMPAIGN.value,
                    classification=EmailType.TRANSACTIONAL,
                )
            elif not recipient:
                self.logger.warning(
                    "notification.admin_cancellation_alert.no_recipient",
                    appointment_id=str(appointment_id),
                    message=(
                        "ADMIN_NOTIFICATION_EMAIL not configured — "
                        "skipping email dispatch"
                    ),
                )
        except Exception as exc:
            # Per spec: never re-raise. Log and continue.
            self.log_failed(
                "send_admin_cancellation_alert.email",
                error=exc,
                appointment_id=str(appointment_id),
            )

        # --- Alert row persistence (dashboard surface) ---
        try:
            from grins_platform.models.alert import Alert  # noqa: PLC0415
            from grins_platform.models.enums import (  # noqa: PLC0415
                AlertSeverity,
                AlertType,
            )
            from grins_platform.repositories.alert_repository import (  # noqa: PLC0415
                AlertRepository,
            )

            alert_repo = AlertRepository(db)
            alert = Alert(
                type=AlertType.CUSTOMER_CANCELLED_APPOINTMENT.value,
                severity=AlertSeverity.WARNING.value,
                entity_type="appointment",
                entity_id=appointment_id,
                message=message,
            )
            await alert_repo.create(alert)
        except Exception as exc:
            # Per spec: never re-raise. Log and continue.
            self.log_failed(
                "send_admin_cancellation_alert.alert_row",
                error=exc,
                appointment_id=str(appointment_id),
            )
            return

        self.log_completed(
            "send_admin_cancellation_alert",
            appointment_id=str(appointment_id),
        )

    def _get_admin_notification_email(self) -> str:
        """Return the configured admin recipient, if any.

        Prefers the explicitly-injected :class:`AdminNotificationSettings`
        instance; falls back to reading the env var lazily so existing
        call sites that never pass the settings object still work.
        """
        if self.admin_settings is not None:
            return self.admin_settings.admin_notification_email
        # Lazy fallback — avoids a hard import of pydantic_settings for
        # callers that never use this path.
        from grins_platform.services.admin_config import (  # noqa: PLC0415
            AdminNotificationSettings,
        )

        return AdminNotificationSettings().admin_notification_email
