# server.py by Pahlavanian
import socket
import threading
import json #imp
import logging
from datetime import datetime
from smtp_module import send_email 
import base64
from pathlib import Path
import os
import tempfile

HOST = "0.0.0.0"
PORT = 5000
BUFFER = 4096
ALERT_RECIPIENT = os.getenv("ALERT_RECIPIENT", "")  # e.g. email address

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dvr-server")

def handle_client(conn, addr):
    logger.info("Connected by %s", addr)
    # Use file-like interface to read newline-delimited JSON
    try:
        with conn.makefile("rwb") as fh:
            while True:
                line = fh.readline()
                if not line:
                    break
                try:
                    text = line.decode("utf-8").strip()
                    if not text:
                        continue
                    data = json.loads(text)
                except Exception as e:
                    logger.warning("Invalid JSON from %s: %s", addr, e)
                    continue

                logger.info("Received event from %s: %s", addr, data.get("event"))
                # Build email
                event = data.get("event", "UNKNOWN")
                camera = data.get("camera", "camera")
                ts = data.get("timestamp", datetime.utcnow().isoformat())
                body_lines = [f"Event: {event}", f"Camera: {camera}", f"Timestamp: {ts}"]
                # Optional metadata
                if "meta" in data:
                    body_lines.append(f"Meta: {json.dumps(data['meta'])}")

                # Handle optional image payload: base64 bytes + filename
                attachment_path = None
                attachment_bytes = None
                attachment_name = None
                if data.get("image_b64"):
                    try:
                        attachment_name = data.get("image_filename", f"{camera}_{ts}.jpg")
                        img_bytes = base64.b64decode(data["image_b64"])
                        # Save to temp file for demonstration (optional)
                        tmpdir = tempfile.gettempdir()
                        save_path = Path(tmpdir) / attachment_name
                        with open(save_path, "wb") as f:
                            f.write(img_bytes)
                        logger.info("Saved image to %s", save_path)
                        attachment_path = str(save_path)
                        attachment_bytes = img_bytes
                        body_lines.append(f"Image attached: {attachment_name}")
                    except Exception as e:
                        logger.exception("Failed to decode/save image: %s", e)

                body = "\n".join(body_lines)
                subject = f"DVR ALERT: {event} - {camera}"

                # If no ALERT_RECIPIENT env var, log only and skip real send
                recipients = [ALERT_RECIPIENT] if ALERT_RECIPIENT else []

                # Send email in a separate thread to avoid blocking connection reading
                threading.Thread(
                    target=_send_alert_async,
                    args=(subject, body, recipients, attachment_name, attachment_bytes),
                    daemon=True,
                ).start()
    except Exception:
        logger.exception("Error handling client %s", addr)
    finally:
        conn.close()
        logger.info("Connection closed %s", addr)

def _send_alert_async(subject, body, recipients, attachment_name, attachment_bytes):
    if not recipients:
        # No real recipient configured: just log
        logger.info("No ALERT_RECIPIENT configured. Would send email:\nSubject: %s\nBody:\n%s", subject, body)
        return
    ok = send_email(
        subject=subject,
        body=body,
        to_addrs=recipients,
        attachment_filename=attachment_name,
        attachment_bytes=attachment_bytes,
    )
    if ok:
        logger.info("Alert email sent successfully.")
    else:
        logger.error("Alert email failed.")

def start_server(host=HOST, port=PORT):
    logger.info("Starting DVR alert server on %s:%s", host, port)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, port))
        s.listen(5)
        logger.info("Listening for connections...")  #imp
        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()  #imp

if __name__ == "__main__":
    start_server()
