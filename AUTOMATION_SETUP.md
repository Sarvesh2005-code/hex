# Automation Setup Guide

## Quick Start

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set Environment Variables**
   Copy the example below and create a `.env` file:
   ```bash
   GEMINI_API_KEY=your_key
   DISCORD_WEBHOOK_URL=your_webhook
   TELEGRAM_BOT_TOKEN=your_token
   TELEGRAM_CHAT_ID=your_chat_id
   ```

3. **Run Automation**
   ```bash
   python -m src.automation
   ```

## Environment Variables

### Required
- `GEMINI_API_KEY` - Your Google Gemini API key

### Optional - Notifications
- `DISCORD_WEBHOOK_URL` - Discord webhook URL
- `TELEGRAM_BOT_TOKEN` - Telegram bot token
- `TELEGRAM_CHAT_ID` - Your Telegram chat ID
- `SMTP_SERVER` - SMTP server (default: smtp.gmail.com)
- `SMTP_PORT` - SMTP port (default: 587)
- `EMAIL_USER` - Email username
- `EMAIL_PASSWORD` - Email password/app password
- `EMAIL_TO` - Recipient email

### Optional - Content Discovery
- `YOUTUBE_CHANNEL_IDS` - Comma-separated channel IDs
- `DISCOVERY_KEYWORDS` - Comma-separated keywords
- `PLAYLIST_URLS` - Comma-separated playlist URLs

### Optional - Scheduling
- `SCHEDULE_INTERVAL_HOURS` - Discovery interval (default: 6)
- `MAX_UPLOADS_PER_DAY` - Max uploads per day (default: 5)
- `HEALTH_CHECK_INTERVAL` - Health check interval in seconds (default: 300)

## Notification Setup

### Discord
1. Server Settings → Integrations → Webhooks
2. Create webhook
3. Copy URL to `DISCORD_WEBHOOK_URL`

### Telegram
1. Message @BotFather
2. Create bot: `/newbot`
3. Get token
4. Message your bot
5. Visit: `https://api.telegram.org/bot<TOKEN>/getUpdates`
6. Find `chat.id` in response
7. Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`

### Email (Gmail)
1. Enable 2FA
2. Create App Password: https://myaccount.google.com/apppasswords
3. Set `EMAIL_USER`, `EMAIL_PASSWORD`, `EMAIL_TO`

## Content Discovery

### Channel Monitoring
Get channel ID from channel URL:
- `https://youtube.com/channel/UCxxxxx` → `UCxxxxx`
- Set `YOUTUBE_CHANNEL_IDS=UCxxxxx,UCyyyyy`

### Keyword Search
Set `DISCOVERY_KEYWORDS=python tutorial,web development`

### Playlist Monitoring
Set `PLAYLIST_URLS=https://youtube.com/playlist?list=xxxxx`

## Local Testing

```bash
# Run automation locally
python -m src.automation

# Run web dashboard
python -m src.web.app

# Check health
curl http://localhost:5000/health
```

## Deployment

See `DEPLOYMENT.md` for Render deployment instructions.

