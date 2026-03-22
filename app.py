from flask import Flask, request, jsonify
import os
from datetime import datetime
import traceback
import resend

app = Flask(__name__)

# ── CONFIG ───────────────────────────────────────────────
API_TOKEN       = os.environ.get("API_TOKEN", "esp8266secret123")
RECIPIENT_EMAIL = os.environ.get("RECIPIENT_EMAIL", "pillarmonitor@gmail.com")

# Resend API KEY
resend.api_key = "re_bqQTtWqA_PqZnXs7zUwEwYrSqLtPbFDEy"
# ────────────────────────────────────────────────────────


# ✅ EMAIL FUNCTION (RESEND)
def send_email(alert_type, crack_length, vibration, stability):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[EMAIL] Sending via Resend: {alert_type} at {now}")

    try:
        html_body = f"""
        <h2>🚨 STRUCTURAL MONITORING ALERT</h2>
        <p><b>Alert Type:</b> {alert_type}</p>
        <p><b>Time:</b> {now}</p>

        <hr>

        <h3>Sensor Readings</h3>
        <p><b>Crack Length:</b> {crack_length:.4f} cm</p>
        <p><b>Vibration:</b> {vibration:.4f}</p>
        <p><b>Stability:</b> {"STABLE" if stability else "UNSTABLE"}</p>

        <hr>
        <p style="color:red;"><b>⚠️ Immediate inspection required</b></p>
        """

        response = resend.Emails.send({
            "from": "onboarding@resend.dev",
            "to": [RECIPIENT_EMAIL],
            "subject": f"🚨 ALERT: {alert_type}",
            "html": html_body
        })

        print("[EMAIL SUCCESS]:", response)
        return True

    except Exception as e:
        print("[EMAIL ERROR]:", e)
        traceback.print_exc()
        return False


# ✅ ALERT ENDPOINT (ESP8266 CALLS THIS)
@app.route("/alert", methods=["POST"])
def alert():
    print(f"\n[POST /alert] from {request.remote_addr}")

    token = request.headers.get("X-Token", "")
    if token != API_TOKEN:
        print(f"[UNAUTHORIZED] token='{token}'")
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(force=True, silent=True)
    print(f"[DATA] {data}")

    if not data:
        return jsonify({"error": "No JSON body"}), 400

    alert_type   = data.get("alert_type", "UNKNOWN")
    crack_length = float(data.get("crack_length", 0))
    vibration    = float(data.get("vibration", 0))
    stability    = bool(data.get("stability", True))

    success = send_email(alert_type, crack_length, vibration, stability)

    return jsonify({
        "status": "email sent" if success else "email failed"
    }), (200 if success else 500)


# ✅ HEALTH CHECK
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


# ✅ TEST EMAIL (OPEN IN BROWSER)
@app.route("/test", methods=["GET"])
def test_email():
    print("[TEST] Manual test triggered")

    success = send_email("TEST ALERT", 0.1234, 0.5678, False)

    if success:
        return f"<h2 style='color:green'>✅ Email sent to {RECIPIENT_EMAIL}</h2>", 200
    else:
        return "<h2 style='color:red'>❌ Email FAILED</h2>", 500


# ✅ RUN SERVER
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
