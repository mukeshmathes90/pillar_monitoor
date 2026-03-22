from flask import Flask, request, jsonify
import os
import json
import urllib.request
import urllib.error
from datetime import datetime
import traceback

app = Flask(__name__)

# ── CONFIG ───────────────────────────────────────────────
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "")
SENDER_EMAIL     = os.environ.get("SENDER_EMAIL", "pillarmonitor@gmail.com")
RECIPIENT_EMAIL  = os.environ.get("RECIPIENT_EMAIL", "pillarmonitor@gmail.com")
API_TOKEN        = os.environ.get("API_TOKEN", "esp8266secret123")
# ────────────────────────────────────────────────────────


def send_email(alert_type, crack_length, vibration, stability):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[EMAIL] Sending: {alert_type} at {now}")

    if not SENDGRID_API_KEY:
        print("[EMAIL] ❌ ERROR: SENDGRID_API_KEY not set")
        return False

    # 🔥 TEXT VERSION
    body_text = f"""
STRUCTURAL MONITORING ALERT

ALERT TYPE : {alert_type}
TIME       : {now}

Crack Length : {crack_length:.4f} cm
Vibration    : {vibration:.4f}
Stability    : {"STABLE" if stability else "UNSTABLE"}

Please inspect immediately.
"""

    # 🔥 HTML VERSION (Better looking email)
    body_html = f"""
    <h2>🚨 STRUCTURAL ALERT</h2>
    <p><b>Alert:</b> {alert_type}</p>
    <p><b>Time:</b> {now}</p>
    <hr>
    <p><b>Crack Length:</b> {crack_length:.4f} cm</p>
    <p><b>Vibration:</b> {vibration:.4f}</p>
    <p><b>Status:</b> {"🟢 STABLE" if stability else "🔴 UNSTABLE"}</p>
    <hr>
    <p><b>Action:</b> Inspect immediately!</p>
    """

    payload = {
        "personalizations": [{
            "to": [{"email": RECIPIENT_EMAIL}]
        }],
        "from": {
            "email": SENDER_EMAIL,
            "name": "Pillar Monitor"
        },
        "subject": f"🚨 ALERT: {alert_type}",
        "content": [
            {"type": "text/plain", "value": body_text},
            {"type": "text/html", "value": body_html}
        ]
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
        print("[EMAIL] Sending request to SendGrid...")

        with urllib.request.urlopen(req, timeout=15) as resp:
            status = resp.status
            print(f"[EMAIL] Response Code: {status}")

            if status == 202:
                print("[EMAIL] ✅ SUCCESS - Email sent!")
                return True
            else:
                print("[EMAIL] ❌ Unexpected response")
                return False

    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"[EMAIL] ❌ HTTP ERROR {e.code}")
        print(error_body)
        return False

    except Exception as e:
        print(f"[EMAIL] ❌ ERROR: {e}")
        traceback.print_exc()
        return False


# ───────────────── API ROUTES ─────────────────

@app.route("/alert", methods=["POST"])
def alert():
    print(f"\n[POST /alert] from {request.remote_addr}")

    token = request.headers.get("X-Token", "")
    if token != API_TOKEN:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"error": "No JSON"}), 400

    try:
        alert_type   = data.get("alert_type", "UNKNOWN")
        crack_length = float(data.get("crack_length", 0))
        vibration    = float(data.get("vibration", 0))
        stability    = bool(data.get("stability", True))

        success = send_email(alert_type, crack_length, vibration, stability)

        return jsonify({
            "status": "email sent" if success else "email failed"
        }), (200 if success else 500)

    except Exception as e:
        print("[API ERROR]", e)
        traceback.print_exc()
        return jsonify({"error": "Server error"}), 500


@app.route("/test", methods=["GET"])
def test_email():
    print("[TEST] Manual test triggered")

    success = send_email("TEST ALERT", 0.1234, 0.5678, False)

    if success:
        return f"<h2 style='color:green'>✅ Email sent to {RECIPIENT_EMAIL}</h2>"
    else:
        return "<h2 style='color:red'>❌ Email FAILED — check logs</h2>", 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "sendgrid": "SET" if SENDGRID_API_KEY else "NOT SET"
    })


# ───────────────── RUN ─────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
