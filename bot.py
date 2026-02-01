import os
import re
import requests
from bs4 import BeautifulSoup
from telegram import Update, ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ---------- CONFIG ----------
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]

# Regex to detect YouTube URLs
YOUTUBE_URL_REGEX = r"(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)[\w-]+"

# ---------- HELPERS ----------

def fetch_transcript(video_url):
    """Fetch transcript using youtubetotranscript.com"""
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
    """Send transcript to Groq and get summary"""
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
                    "From the following YouTube transcript, extract exactly 4 concise key points.\n"
                    "Rules:\n"
                    "- Each point must be one sentence\n"
                    "- No intro, no conclusion\n"
                    "- No numbering\n"
                    "- No emojis\n\n"
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

    return r.json()["choices"][0]["message"]["content"].strip()

def format_summary(title, summary, video_url):
    """Format the Telegram message with emojis and bullets"""
    points = summary.split("\n")
    icons = ["💡", "🔥", "⚡", "🎯"]
    formatted_points = "\n".join(
        f"{icons[i]} {points[i].strip()}"
        for i in range(min(4, len(points)))
    )

    message = (
        f"🎬 *{title}*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{formatted_points}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔗 [Watch Video]({video_url})\n\n"
        f"#TechChannel"
    )
    return message

# ---------- TELEGRAM HANDLERS ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send me a YouTube link and I'll summarize it for you!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    match = re.search(YOUTUBE_URL_REGEX, text)
    if not match:
        await update.message.reply_text("Please send a valid YouTube link.")
        return

    video_url = text
    title = "YouTube Video"

    # Send typing action
    await context.bot.send_chat_action(chat_id=update.message.chat_id, action="typing")

    try:
        transcript = fetch_transcript(video_url)
        summary = summarize_with_groq(transcript)
        message = format_summary(title, summary, video_url)
    except Exception as e:
        message = (
            f"⚠️ Could not summarize the video.\n\n"
            f"🔗 [Watch Video]({video_url})"
        )

    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

# ---------- MAIN ----------

def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
