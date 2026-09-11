import smtplib
import logging
from email.message import EmailMessage
from html import escape

from app.config import settings

logger = logging.getLogger(__name__)


def send_email_verification_email(recipient: str, verification_url: str, code: str) -> None:
    if not settings.smtp_host or not settings.smtp_username or not settings.smtp_password:
        raise RuntimeError("SMTP is not configured")

    message = EmailMessage()
    message["Subject"] = "Verify your Landwise AI email"
    message["From"] = settings.smtp_from_email or settings.smtp_username
    message["To"] = recipient
    message.set_content(
        "Welcome to Landwise AI.\n\n"
        f"Your verification code is: {code}\n\n"
        f"Open the verification screen here: {verification_url}\n\n"
        "This code expires in 15 minutes. If you did not create this account, you can ignore this email."
    )
    message.add_alternative(
        f"<p>Welcome to Landwise AI.</p><p>Your verification code is <strong>{escape(code)}</strong>.</p>"
        f'<p><a href="{escape(verification_url)}" style="background:#1f5d45;color:#fff;padding:12px 18px;text-decoration:none;border-radius:4px;display:inline-block">Verify email</a></p>'
        "<p>This code expires in 15 minutes. If you did not create this account, you can ignore this email.</p>",
        subtype="html",
    )

    smtp_class = smtplib.SMTP_SSL if settings.smtp_port == 465 else smtplib.SMTP
    with smtp_class(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
        if settings.smtp_port != 465:
            smtp.starttls()
        smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(message)


def send_password_reset_email(recipient: str, reset_url: str) -> None:
    if not settings.smtp_host or not settings.smtp_username or not settings.smtp_password:
        raise RuntimeError("SMTP is not configured")

    message = EmailMessage()
    message["Subject"] = "Reset your Landwise AI password"
    message["From"] = settings.smtp_from_email or settings.smtp_username
    message["To"] = recipient
    message.set_content(
        "We received a request to reset your Landwise AI password.\n\n"
        f"Reset your password here: {reset_url}\n\n"
        "This link expires in 60 minutes and can only be used once. "
        "If you did not request this, you can ignore this email."
    )

    smtp_class = smtplib.SMTP_SSL if settings.smtp_port == 465 else smtplib.SMTP
    with smtp_class(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
        if settings.smtp_port != 465:
            smtp.starttls()
        smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(message)
