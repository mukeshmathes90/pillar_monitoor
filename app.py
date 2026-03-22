from flask import Flask, request, jsonify
import os
import json
import urllib.request
import urllib.error
from datetime import datetime
import traceback

app = Flask(__name__)

# ── CONFIG ───────────────────────────────────────────────
# We use SendGrid HTTP API (port 443) because Render free tier
# blocks outbound SMTP (port 465/587). SendGrid free = 100 emails/day
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "")
SENDER_EMAIL     = os.environ.get("SENDER_EMAIL",     "pillarmonitor@gmail.com")
RECIPIENT_EMAIL  = os.environ.get("RECIPIENT_EMAIL",  "pillarmonitor@gmail.com")
API_TOKEN        = os.environ.get("API_TOKEN",        "esp8266secret123")
# ────────────────────────────────────────────────────────

def send_email(alert_type, crack_length, vibration, stability):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[EMAIL] Sending: {alert_type} at {now}")

    if not SENDGRID_API_KEY:
        print("[EMAIL] ERROR: SENDGRID_API_KEY env variable is not set!")
        return False

    body_text = f"""
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

    payload = {
        "personalizations": [{
            "to": [{"email": RECIPIENT_EMAIL}]
        }],
        "from": {"email": SENDER_EMAIL, "name": "Pillar Monitor"},
        "subject": f"ALERT: {alert_type}!",
        "content": [{"type": "text/plain", "value": body_text}]
    }

    data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        "https://api.sendgrid.com/v3/mail/send",
        data=data,
        headers={
            "Authorization": f"Bearer {SENDGRID_API_KEY}",
            "Content-Type": "application/json"
        },
        method="POST"
    )

    try:
        print("[EMAIL] POSTing to SendGrid API...")
        with urllib.request.urlopen(req, timeout=15) as resp:
            status = resp.status
            print(f"[EMAIL] SendGrid response: {status}")
            if status == 202:
                print("[EMAIL] SUCCESS - email queued by SendGrid")
                return True
            else:
                print(f"[EMAIL] Unexpected status: {status}")
                return False

    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"[EMAIL] HTTPError {e.code}: {body}")
        return False
    except Exception as e:
        print(f"[EMAIL] ERROR: {e}")
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
    key_set = "YES" if SENDGRID_API_KEY else "NO - SET IT IN RENDER ENV!"
    return jsonify({"status": "ok", "sendgrid_key_set": key_set}), 200


@app.route("/test", methods=["GET"])
def test_email():
    """Open /test in browser to send a real test email"""
    print("[TEST] Manual test triggered")
    success = send_email("TEST ALERT", 0.1234, 0.5678, False)
    if success:
        return f"<h2 style='color:green'>✅ Test email sent to {RECIPIENT_EMAIL} — check inbox (also spam)!</h2>", 200
    else:
        return "<h2 style='color:red'>❌ Email FAILED — check Render Logs tab</h2>", 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
