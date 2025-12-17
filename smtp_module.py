# smtp_module.py by Pahlavanian
import os
import smtplib
import logging
from email.message import EmailMessage
from email.utils import formatdate
from pathlib import Path
import base64
import mimetypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("smtp_module")

# Read config from environment variables
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "0") or 0)
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() in ("1", "true", "yes")

def _attach_file(msg: EmailMessage, filename: str, content_bytes: bytes):
    maintype, subtype = (mimetypes.guess_type(filename)[0] or "application/octet-stream").split("/", 1)
    msg.add_attachment(content_bytes, maintype=maintype, subtype=subtype, filename=Path(filename).name)

def send_email(  #imp
    subject: str,
    body: str,
    to_addrs,
    from_addr=None,
    attachment_filename: str | None = None,
    attachment_bytes: bytes | None = None,
) -> bool:
    """
    Send an email. Configuration via env vars:
      SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_USE_TLS

    If SMTP_HOST/PORT are not set, this attempts to use localhost:1025 (debug server).
    """
    if isinstance(to_addrs, str):
        to_addrs = [to_addrs]

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr or (SMTP_USER or "noreply@example.com")
    msg["To"] = ", ".join(to_addrs)
    msg["Date"] = formatdate(localtime=True)
    msg.set_content(body)

    if attachment_filename and attachment_bytes:
        try:
            _attach_file(msg, attachment_filename, attachment_bytes)
        except Exception as e:
            logger.exception("Failed to attach file: %s", e)

    # Decide SMTP target
    if SMTP_HOST and SMTP_PORT:
        host, port = SMTP_HOST, SMTP_PORT
        use_tls = SMTP_USE_TLS
        logger.info("Using configured SMTP host %s:%s (TLS=%s)", host, port, use_tls)
    else:
        # fallback to local debug server
        host, port = "localhost", 1025
        use_tls = False
        logger.info("No SMTP config found — falling back to local debug SMTP at %s:%s", host, port)

    try:
        if use_tls and port in (587, 25):
            # STARTTLS flow
            with smtplib.SMTP(host, port, timeout=10) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.ehlo()
                if SMTP_USER and SMTP_PASS:
                    smtp.login(SMTP_USER, SMTP_PASS)
                smtp.send_message(msg)
        elif use_tls and port == 465:
            # SSL
            with smtplib.SMTP_SSL(host, port, timeout=10) as smtp:
                if SMTP_USER and SMTP_PASS:
                    smtp.login(SMTP_USER, SMTP_PASS)
                smtp.send_message(msg)
        else:
            # Plain, usually local debug server
            with smtplib.SMTP(host, port, timeout=10) as smtp:
                if SMTP_USER and SMTP_PASS:
                    smtp.login(SMTP_USER, SMTP_PASS)
                smtp.send_message(msg)
        logger.info("Email sent to %s", to_addrs)
        return True
    except Exception as e:
        logger.exception("Failed to send email: %s", e)
        return False
