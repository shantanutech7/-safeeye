# alerter.py
import os
import csv
from datetime import datetime

LOG_FILE = "logs/violation_log.csv"

def log_violation(screenshot_path, timestamp):
    """Save violation to CSV log"""
    os.makedirs("logs", exist_ok=True)
    file_exists = os.path.isfile(LOG_FILE)

    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Timestamp", "Screenshot", "Status"])
        writer.writerow([timestamp, screenshot_path or "No screenshot", "VIOLATION"])

    print(f"[SafeEye] Violation logged: {timestamp}")

def send_sms(timestamp):
    """SMS placeholder — add Twilio/MSG91 in production"""
    print(f"[SafeEye] SMS ALERT (demo): Violation at {timestamp}")

def send_email(screenshot_path, timestamp):
    """Email placeholder — add SMTP in production"""
    print(f"[SafeEye] EMAIL ALERT (demo): Violation at {timestamp} | Screenshot: {screenshot_path}")

def send_alert(screenshot_path, timestamp):
    print(f"[SafeEye] Triggering alerts for violation at {timestamp}...")
    send_sms(timestamp)
    send_email(screenshot_path, timestamp)
    log_violation(screenshot_path, timestamp)
    print(f"[SafeEye] All alerts triggered successfully.")

if __name__ == "__main__":
    print("[SafeEye] Testing alert system...")
    send_alert(screenshot_path=None, timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))