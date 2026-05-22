"""
Visa Photo Checker - Slack Bot
CS agent posts a photo, tags the bot, and it instantly replies good or bad.
Usage: @Atlys Photo Checker [attached photo]
"""

import os
import base64
import logging
import requests
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request
from anthropic import Anthropic

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

slack_app = App(
    token=os.environ["SLACK_BOT_TOKEN"],
    signing_secret=os.environ["SLACK_SIGNING_SECRET"],
)
anthropic_client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
flask_app = Flask(__name__)
handler = SlackRequestHandler(slack_app)

VISA_PHOTO_PROMPT = """
You are a visa photo checker for Atlys. Look at this photo and decide if it is
acceptable for a visa application based on the rules below.

Reply in this exact format — nothing else:

RESULT: GOOD
(if the photo passes every rule)

— OR —

RESULT: BAD
ISSUES:
- <issue 1, written as a clear, friendly instruction the customer can act on, e.g. "Please retake against a plain white background">
- <issue 2>
- <add as many as needed>

Rules — the photo MUST meet ALL of these:

IMAGE QUALITY
- Must be a colour photo (not black and white or filtered)
- Must be clear, sharp, and in focus — no blur or pixelation
- Must be high resolution
- No visible filters, heavy editing, or unnatural skin tones
- Photo must not be folded, torn, scratched, or damaged
- No selfie-style distortion
- Correct aspect ratio and cropping — do not flag minor spacing at the top of the head

BACKGROUND
- Plain white, off-white, or light-coloured background (cream or light grey is acceptable)
- No patterns, textures, or objects in the background
- No other people visible
- No obvious shadows on the background (minor shadows are acceptable)
- Background must be evenly lit with good contrast between subject and background

FACE & HEAD POSITION
- Face must be centred in the frame and directly facing the camera
- Full face clearly visible — no obstructions
- Entire head visible from chin to top of head
- Head not tilted
- Head size proportionate within the frame — do not flag minor variations
- Both sides of the face fully visible
- Hair must not cover the eyes or face

EYES & EXPRESSION
- Both eyes open and clearly visible
- Neutral facial expression
- Mouth closed — no smiling with teeth visible
- No red-eye

LIGHTING
- Even lighting across the entire face
- No harsh or obvious shadows on the face (slight, natural shadows are acceptable)
- No glare or reflections on the face

GLASSES & HEAD COVERINGS
- No sunglasses
- If glasses are worn: eyes must be fully visible, no glare on lenses, no tinted lenses
- Head coverings must not obscure any facial features — full facial outline must be visible

CLOTHING & ACCESSORIES
- Wearing normal, everyday clothing
- No uniforms or camouflage clothing
- No headphones or electronic devices visible
- Shoulders straight and visible

Be strict. If even one rule fails, the result is BAD.
List every issue found — do not stop at the first one.
Write each issue as a short, friendly instruction the customer can immediately act on.
"""


def download_image(file_info: dict) -> bytes | None:
    url = file_info.get("url_private_download") or file_info.get("url_private")
    if not url:
        return None
    resp = requests.get(
        url,
        headers={"Authorization": f"Bearer {os.environ['SLACK_BOT_TOKEN']}"},
        timeout=15,
    )
    return resp.content if resp.status_code == 200 else None


def check_photo(image_bytes: bytes, mime_type: str) -> tuple[bool, list[str]]:
    b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
    message = anthropic_client.messages.create(
        model="claude-opus-4-5",
        max_tokens=512,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": mime_type, "data": b64}},
                {"type": "text", "text": VISA_PHOTO_PROMPT},
            ],
        }],
    )
    text = message.content[0].text.strip()
    is_good = "RESULT: GOOD" in text
    issues = []
    if not is_good and "ISSUES:" in text:
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("- "):
                issues.append(line[2:])
    return is_good, issues


@slack_app.event("app_mention")
def handle_mention(event, client, say):
    """Fires when someone tags @Atlys Photo Checker in a message with a photo."""
    files = event.get("files", [])
    channel = event["channel"]
    thread_ts = event.get("thread_ts") or event["ts"]

    if not files:
        say(
            text="Please attach a visa photo when mentioning me and I'll check it right away!",
            thread_ts=thread_ts,
        )
        return

    for file_info in files:
        if not file_info.get("mimetype", "").startswith("image/"):
            continue

        # Post immediate acknowledgement
        placeholder = client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text=":mag: Checking visa photo…",
        )

        try:
            image_bytes = download_image(file_info)
            if not image_bytes:
                raise ValueError("Could not download image")

            is_good, issues = check_photo(image_bytes, file_info["mimetype"])

            if is_good:
                text = "✅ *Photo looks good!* This meets visa photo standards."
            else:
                lines = ["❌ *Photo needs to be retaken.* Please ask the customer to fix the following:"]
                for issue in issues:
                    lines.append(f"• {issue}")
                text = "\n".join(lines)

            client.chat_update(channel=channel, ts=placeholder["ts"], text=text)

        except Exception:
            logger.exception("Photo check failed")
            client.chat_update(
                channel=channel,
                ts=placeholder["ts"],
                text="⚠️ Could not check photo. Please try again.",
            )


@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    if request.content_type and "application/json" in request.content_type:
        data = request.get_json(silent=True)
        if data and data.get("type") == "url_verification":
            return {"challenge": data["challenge"]}
    return handler.handle(request)


@flask_app.route("/health")
def health():
    return {"status": "ok"}, 200


if __name__ == "__main__":
    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
