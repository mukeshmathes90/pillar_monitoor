# Pillar Monitor — Full Deployment Guide

## Architecture
```
ESP8266 ──(HTTP POST)──▶ Python/Flask on Render ──(SMTP SSL)──▶ Gmail
    │
    └──(ArduinoCloud)──▶ IoT Dashboard
```

The ESP no longer handles SSL email itself — that was causing the freeze.
All email logic lives in the Python server on Render.

---

## PART 1: Deploy Python Server to Render.com

### Step 1 — Push code to GitHub
1. Create a new GitHub repo (e.g. `pillar-monitor-server`)
2. Add these files to it:
   - `app.py`
   - `requirements.txt`
   - `Procfile`
3. Push to GitHub

### Step 2 — Create Render Web Service
1. Go to https://render.com → Sign up free (Google login works)
2. Click **New → Web Service**
3. Connect your GitHub repo
4. Fill in:
   | Field | Value |
   |-------|-------|
   | Name | `pillar-monitor` (or anything) |
   | Runtime | **Python 3** |
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `gunicorn app:app` |
   | Instance Type | **Free** |

### Step 3 — Set Environment Variables
In Render dashboard → Environment tab, add:

| Key | Value |
|-----|-------|
| `SENDER_EMAIL` | `pillarmonitor@gmail.com` |
| `SENDER_PASSWORD` | `fslbudrttegqceph` |
| `RECIPIENT_EMAIL` | `pillarmonitor@gmail.com` |
| `API_TOKEN` | `esp8266secret123` |

### Step 4 — Get your URL
After deploy (2–3 min), Render gives you a URL like:
```
https://pillar-monitor.onrender.com
```
Your alert endpoint will be:
```
https://pillar-monitor.onrender.com/alert
```

> ⚠️ **Free tier note**: Render free services spin down after 15 min of inactivity.
> First request after sleep takes ~30 s to wake up. For a sensor monitor this is fine
> since the ESP retries on the next alert trigger.
> If you want always-on, use Render Starter ($7/mo) or use a free uptime pinger
> like https://uptimerobot.com (ping /health every 10 min).

---

## PART 2: Update ESP8266 Code

In `pillar_monitor.ino`, change line:
```cpp
#define PYTHON_SERVER_URL  "https://YOUR-APP-NAME.onrender.com/alert"
```
to your actual Render URL, e.g.:
```cpp
#define PYTHON_SERVER_URL  "https://pillar-monitor.onrender.com/alert"
```

Upload via Arduino IDE as normal.

---

## PART 3: Gmail App Password Setup

If email sending fails, your Gmail may need an App Password:
1. Go to https://myaccount.google.com/security
2. Enable **2-Step Verification** if not already
3. Go to **App Passwords** (search for it)
4. Create one for "Mail" → "Other device"
5. Use that 16-char password as `SENDER_PASSWORD`

---

## Thresholds (easy to tune)

In `pillar_monitor.ino`:
```cpp
#define CRACK_THRESHOLD     0.05f   // cm — lower = more sensitive
#define CRACK_CLEAR         0.03f
#define VIBRATION_THRESHOLD 0.4f   // lower = more sensitive  
#define VIBRATION_CLEAR     0.25f
#define ALERT_COOLDOWN_MS  30000UL  // ms between repeated alerts
```

---

## Testing the Server

Test your Python server without the ESP:
```bash
curl -X POST https://pillar-monitor.onrender.com/alert \
  -H "Content-Type: application/json" \
  -H "X-Token: esp8266secret123" \
  -d '{"alert_type":"TEST","crack_length":0.12,"vibration":0.5,"stability":false}'
```
You should get an email within seconds.

---

## What Was Fixed

| Issue | Fix |
|-------|-----|
| ESP8266 freezes | Removed heavy SSL email from ESP; now just sends a quick HTTP POST |
| `3.214e-4` scientific notation | Used `dtostrf()` on ESP, `:.4f` format in Python email |
| Not reacting to small changes | Lowered crack threshold to 0.05 cm, vibration to 0.4 |
| Crack reading noise | Better smoothing with 0.8/0.2 EMA filter + `pulseIn` timeout |
