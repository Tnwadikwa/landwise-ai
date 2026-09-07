import smtplib
from email.message import EmailMessage

from app.config import settings


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

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
        smtp.starttls()
        smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(message)
