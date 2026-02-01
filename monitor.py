import os
import json
import requests
import feedparser
from bs4 import BeautifulSoup

# CONFIG
RSS_URL = "https://www.youtube.com/feeds/videos.xml?channel_id=UCrvchO1h6lWZAuGaa1LqX9Q"
STATE_FILE = "state.json"

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]

# ---------- helpers ----------

def load_state():
    with open(STATE_FILE, "r") as f:
        return json.load(f)

def save_state(video_id):
    with open(STATE_FILE, "w") as f:
        json.dump({"last_video_id": video_id}, f)

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }, timeout=20)

def fetch_transcript(video_url):
    # using youtubetotranscript.com (HTML scrape)
    r = requests.post(
        "https://youtubetotranscript.com",
        data={"youtube_url": video_url},
        timeout=30
    )
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")
    textarea = soup.find("textarea")

    if not textarea or not textarea.text.strip():
        raise RuntimeError("Transcript not found")

    return textarea.text.strip()

def summarize_with_groq(text):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "llama3-8b-8192",
        "messages": [
            {
                "role": "user",
                "content": (
                    "Summarize this YouTube video transcript as:\n"
                    "- 5 bullet points\n"
                    "- TL;DR\n"
                    "- Key takeaway\n\n"
                    f"{text}"
                )
            }
        ]
    }

    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=60
    )
    r.raise_for_status()

    return r.json()["choices"][0]["message"]["content"]

# ---------- main ----------

def main():
    state = load_state()
    last_video = state.get("last_video_id")

    feed = feedparser.parse(RSS_URL)
    if not feed.entries:
        return

    latest = feed.entries[0]
    video_id = latest.yt_videoid
    video_url = latest.link
    title = latest.title

    if video_id == last_video:
        return

    try:
        transcript = fetch_transcript(video_url)
        summary = summarize_with_groq(transcript)

        message = (
            f"📺 *New YouTube Video*\n\n"
            f"*{title}*\n\n"
            f"{summary}\n\n"
            f"[Watch video]({video_url})"
        )

    except Exception as e:
        message = (
            f"⚠️ New video detected:\n\n"
            f"*{title}*\n\n"
            f"Transcript could not be fetched.\n"
            f"[Watch video]({video_url})"
        )

    send_telegram(message)
    save_state(video_id)

if __name__ == "__main__":
    main()
