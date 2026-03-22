from flask import Flask, request, jsonify
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from datetime import datetime

app = Flask(__name__)

# ── CONFIG ──────────────────────────────────────────────
SENDER_EMAIL    = os.environ.get("SENDER_EMAIL", "pillarmonitor@gmail.com")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD", "fslbudrttegqceph")
RECIPIENT_EMAIL = os.environ.get("RECIPIENT_EMAIL", "pillarmonitor@gmail.com")
# Secret token so only your ESP can hit this endpoint
API_TOKEN       = os.environ.get("API_TOKEN", "esp8266secret123")
# ────────────────────────────────────────────────────────

def send_email(alert_type, crack_length, vibration, stability):
    try:
        msg = MIMEMultipart("alternative")
        msg["From"]    = f"Pillar Monitor <{SENDER_EMAIL}>"
        msg["To"]      = RECIPIENT_EMAIL
        msg["Subject"] = f"🚨 ALERT: {alert_type}!"

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Format crack_length nicely — avoid scientific notation
        crack_str = f"{crack_length:.4f} cm"

        body = f"""
====================================
  STRUCTURAL MONITORING ALERT
====================================

ALERT TYPE   : {alert_type}
TIMESTAMP    : {now}

------------------------------------
SENSOR READINGS AT TIME OF ALERT
------------------------------------
Crack Length : {crack_str}
Vibration    : {vibration:.4f}
Stability    : {"STABLE" if stability else "UNSTABLE"}
------------------------------------

Please inspect the structure immediately.
The crack or instability may be developing further.

- ESP8266 Structure Monitor
====================================
"""
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, msg.as_string())

        print(f"[EMAIL SENT] {alert_type} at {now}")
        return True

    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
        return False


@app.route("/alert", methods=["POST"])
def alert():
    # Simple token auth
    token = request.headers.get("X-Token", "")
    if token != API_TOKEN:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"error": "No JSON body"}), 400

    alert_type   = data.get("alert_type", "UNKNOWN")
    crack_length = float(data.get("crack_length", 0))
    vibration    = float(data.get("vibration", 0))
    stability    = bool(data.get("stability", True))

    print(f"[ALERT RECEIVED] type={alert_type} crack={crack_length:.4f} vib={vibration:.4f} stable={stability}")

    success = send_email(alert_type, crack_length, vibration, stability)

    if success:
        return jsonify({"status": "email sent"}), 200
    else:
        return jsonify({"status": "email failed"}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
