"""Email utilities for sending feedback reports."""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from src.config import EmailConfig


def send_feedback_email(config: EmailConfig, recipient: str, subject: str,
                        body: str, markdown_attachment: str = None,
                        attachment_filename: str = None) -> bool:
    """Send a feedback email via Gmail SMTP.

    Args:
        config: Email configuration.
        recipient: Recipient email address.
        subject: Email subject.
        body: Email body text.
        markdown_attachment: Optional Markdown report to attach.
        attachment_filename: Filename for the Markdown attachment.

    Returns:
        True if email sent successfully, False otherwise.
    """
    if not config.enabled or not recipient:
        return False

    try:
        msg = MIMEMultipart()
        msg["From"] = config.sender_email
        msg["To"] = recipient
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "plain", "utf-8"))

        if markdown_attachment and attachment_filename:
            attach = MIMEText(markdown_attachment, "plain", "utf-8")
            attach.add_header("Content-Disposition", "attachment",
                            filename=attachment_filename)
            msg.attach(attach)

        context = ssl.create_default_context()
        with smtplib.SMTP(config.smtp_server, config.smtp_port) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(config.sender_email, config.sender_password)
            server.sendmail(config.sender_email, recipient, msg.as_string())

        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False
