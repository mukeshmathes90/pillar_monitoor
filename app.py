from flask import Flask, request, jsonify
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from datetime import datetime
import traceback

app = Flask(__name__)

# ── CONFIG ───────────────────────────────────────────────
SENDER_EMAIL    = os.environ.get("SENDER_EMAIL",    "pillarmonitor@gmail.com")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD", "zpyuxgwycshbdxng")
RECIPIENT_EMAIL = os.environ.get("RECIPIENT_EMAIL", "pillarmonitor@gmail.com")
API_TOKEN       = os.environ.get("API_TOKEN",       "esp8266secret123")
# ────────────────────────────────────────────────────────

def send_email(alert_type, crack_length, vibration, stability):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[EMAIL] Attempting: {alert_type} at {now}")
    print(f"[EMAIL] From={SENDER_EMAIL}  To={RECIPIENT_EMAIL}  PassLen={len(SENDER_PASSWORD)}")

    try:
        msg = MIMEMultipart("alternative")
        msg["From"]    = f"Pillar Monitor <{SENDER_EMAIL}>"
        msg["To"]      = RECIPIENT_EMAIL
        msg["Subject"] = f"ALERT: {alert_type}!"

        body = f"""
====================================
  STRUCTURAL MONITORING ALERT
====================================

ALERT TYPE   : {alert_type}
TIMESTAMP    : {now}

------------------------------------
SENSOR READINGS
------------------------------------
Crack Length : {crack_length:.4f} cm
Vibration    : {vibration:.4f}
Stability    : {"STABLE" if stability else "UNSTABLE"}
------------------------------------

Please inspect the structure immediately.

- ESP8266 Structure Monitor
====================================
"""
        msg.attach(MIMEText(body, "plain"))

        print("[EMAIL] Connecting smtp.gmail.com:465 ...")
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as smtp:
            print("[EMAIL] Connected. Logging in...")
            smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
            print("[EMAIL] Login OK. Sending message...")
            smtp.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, msg.as_string())

        print(f"[EMAIL] SUCCESS sent at {now}")
        return True

    except smtplib.SMTPAuthenticationError as e:
        print(f"[EMAIL] AUTH FAILED: {e}")
        print("[EMAIL] Fix: Go to Google Account > Security > App Passwords > create new one")
        return False
    except smtplib.SMTPException as e:
        print(f"[EMAIL] SMTP ERROR: {e}")
        return False
    except Exception as e:
        print(f"[EMAIL] UNEXPECTED ERROR: {e}")
        traceback.print_exc()
        return False


@app.route("/alert", methods=["POST"])
def alert():
    print(f"\n[POST /alert] from {request.remote_addr}")

    token = request.headers.get("X-Token", "")
    if token != API_TOKEN:
        print(f"[POST /alert] UNAUTHORIZED token='{token}'")
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(force=True, silent=True)
    print(f"[POST /alert] data={data}")
    if not data:
        return jsonify({"error": "No JSON body"}), 400

    alert_type   = data.get("alert_type", "UNKNOWN")
    crack_length = float(data.get("crack_length", 0))
    vibration    = float(data.get("vibration", 0))
    stability    = bool(data.get("stability", True))

    success = send_email(alert_type, crack_length, vibration, stability)
    return jsonify({"status": "email sent" if success else "email failed"}), (200 if success else 500)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/test", methods=["GET"])
def test_email():
    """
    Open https://pillar-monitoor.onrender.com/test in browser
    to send a real test email without needing the ESP
    """
    print("[TEST] Manual test triggered from browser")
    success = send_email("TEST ALERT", 0.1234, 0.5678, False)
    if success:
        return f"<h2 style='color:green'>✅ Test email sent to {RECIPIENT_EMAIL} — check inbox!</h2>", 200
    else:
        return "<h2 style='color:red'>❌ Email FAILED — check Render Logs tab for error details</h2>", 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)