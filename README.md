## YouTube → Groq → Telegram Monitor

Monitors a YouTube channel via RSS.
When a new video appears:
- Fetches transcript via third-party site
- Summarizes using Groq API
- Sends summary to Telegram

### Setup
1. Create Telegram bot
2. Create Groq API key
3. Add GitHub Secrets:
   - TELEGRAM_BOT_TOKEN
   - TELEGRAM_CHAT_ID
   - GROQ_API_KEY
4. Enable GitHub Actions

Runs every 15 minutes.
