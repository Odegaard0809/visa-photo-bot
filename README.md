# Visa Photo Slack Bot — Setup Guide

A Slack bot that instantly checks visa photos against international standards
using Claude Vision, eliminating the back-and-forth between customer support and ops.

---

## What the bot checks

| Criterion | What it looks for |
|---|---|
| Face centered | Subject fills 70–80% of frame |
| Face visibility | No obstructions, mask, hand, etc. |
| White background | Clean plain white or off-white only |
| Even lighting | No harsh shadows or overexposure |
| No shadows | Especially on the face or background |
| Eyes open & visible | Both eyes clearly visible, looking forward |
| Neutral expression | Mouth closed, no smile |
| No glasses | Including sunglasses and tinted lenses |
| Head uncovered | No hats, caps (religious coverings are allowed) |
| Photo in focus | Sharp, not blurry |
| No border or frame | Plain photo only |
| Colour photo | Not black-and-white or filtered |

---

## Prerequisites

- Python 3.11+
- A public HTTPS URL for your server (use [ngrok](https://ngrok.com) for local dev)
- A Slack workspace where you are an admin
- An Anthropic API key — get one at https://console.anthropic.com/

---

## Step 1 — Create the Slack App

1. Go to https://api.slack.com/apps → **Create New App** → **From scratch**
2. Give it a name like `Visa Photo Bot` and pick your workspace
3. On the left sidebar, go to **OAuth & Permissions**
4. Under **Bot Token Scopes**, add these scopes:
   - `chat:write` — post messages
   - `files:read` — download uploaded photos
   - `users:read` — get uploader's name
   - `channels:history` — read message events
   - `groups:history` — read private channel events (if needed)
5. Click **Install to Workspace** → copy the **Bot User OAuth Token** (`xoxb-...`)
6. Go to **Basic Information** → copy the **Signing Secret**

---

## Step 2 — Configure environment

```bash
# Clone or create the project folder
cd visa-photo-bot

# Copy and fill in the env file
cp .env.example .env
# Edit .env with your real tokens
```

---

## Step 3 — Install and run locally

```bash
# Create a virtual environment
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the bot
python src/app.py
```

The server starts on `http://localhost:3000`

---

## Step 4 — Expose locally with ngrok (dev only)

```bash
# In a separate terminal
ngrok http 3000
```

Copy the `https://xxxx.ngrok-free.app` URL — you'll need it for Slack.

---

## Step 5 — Configure Slack event subscriptions

1. In your Slack app settings → **Event Subscriptions** → toggle **Enable Events** ON
2. Set Request URL to: `https://your-ngrok-url.ngrok-free.app/slack/events`
   - Slack will immediately send a challenge — the bot must be running to verify it
3. Under **Subscribe to bot events**, add:
   - `message.channels`
   - `message.groups` (if you use private channels)
4. Click **Save Changes**

---

## Step 6 — Invite the bot to your channel

In Slack, open your `#visa-photos` channel and type:
```
/invite @Visa Photo Bot
```

---

## Step 7 — Test it

1. Post any image in `#visa-photos`
2. The bot posts "Checking…" in the thread immediately
3. Within ~5 seconds it updates with a full verdict

---

## Production deployment (Railway / Render / Fly.io)

### Using Docker

```bash
docker build -t visa-photo-bot .
docker run -p 3000:3000 --env-file .env visa-photo-bot
```

### Railway (easiest)

1. Push this folder to a GitHub repo
2. Go to https://railway.app → New Project → Deploy from GitHub
3. Add all three environment variables in the Railway dashboard
4. Railway gives you a public URL — use that as your Slack event URL

### Environment variables to set in production

| Variable | Where to get it |
|---|---|
| `SLACK_BOT_TOKEN` | Slack App → OAuth & Permissions |
| `SLACK_SIGNING_SECRET` | Slack App → Basic Information |
| `ANTHROPIC_API_KEY` | https://console.anthropic.com/ |

---

## How the bot message looks in Slack

**When the photo passes:**
```
✅ Visa Photo Check — PASS
Submitted by: Priya Sharma
Summary: Photo meets all international visa standards.

✅ Face centered — Good framing
✅ White background — Clean white background
✅ Lighting even — Well lit, no shadows
... (all 12 checks)

Checked by Visa Photo Bot · Powered by Claude Vision
```

**When the photo fails:**
```
❌ Visa Photo Check — FAIL
Submitted by: Priya Sharma
Summary: Background is not white and shadows visible on face.

✅ Face centered — Good framing
❌ White background — Blue/grey wall detected
❌ No shadows — Shadow on left cheek
...

📝 Action required for customer:
Please retake the photo against a plain white wall in even lighting.
Avoid windows or single-sided light sources.

Checked by Visa Photo Bot · Powered by Claude Vision
```

---

## Customising the standards

Edit `VISA_PHOTO_PROMPT` in `src/app.py` to tighten or relax any criterion,
or add country-specific rules (e.g. "No head coverings except for religious reasons").

---

## Troubleshooting

| Issue | Fix |
|---|---|
| Bot doesn't respond | Check it's invited to the channel with `/invite` |
| "Photo analysis failed" | Check `ANTHROPIC_API_KEY` is set correctly |
| Slack shows "Your URL didn't respond" | Make sure the bot is running before pasting the URL |
| Images not downloading | Ensure `files:read` scope is added and bot is reinstalled |
