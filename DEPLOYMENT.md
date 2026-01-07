# 24/7 Autonomous Deployment Guide

## Overview
This guide will help you deploy OpenClip as a fully autonomous 24/7 system on Render's free tier.

## Prerequisites

1. **GitHub Account** - For hosting your code
2. **Render Account** - Sign up at https://render.com (free tier available)
3. **API Keys**:
   - Gemini API Key (for content analysis)
   - Discord Webhook URL (optional, for notifications)
   - Telegram Bot Token (optional, for notifications)
   - Email credentials (optional, for email notifications)

## Step 1: Setup Notifications

### Discord Webhook
1. Go to your Discord server settings
2. Navigate to Integrations → Webhooks
3. Create a new webhook
4. Copy the webhook URL
5. Set as environment variable: `DISCORD_WEBHOOK_URL`

### Telegram Bot
1. Message @BotFather on Telegram
2. Create a new bot with `/newbot`
3. Copy the bot token
4. Get your chat ID by messaging your bot, then visit: `https://api.telegram.org/bot<TOKEN>/getUpdates`
5. Set environment variables:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`

### Email (Gmail)
1. Enable 2-factor authentication
2. Generate an App Password: https://myaccount.google.com/apppasswords
3. Set environment variables:
   - `SMTP_SERVER=smtp.gmail.com`
   - `SMTP_PORT=587`
   - `EMAIL_USER=your_email@gmail.com`
   - `EMAIL_PASSWORD=your_app_password`
   - `EMAIL_TO=recipient@email.com`

## Step 2: Configure Content Discovery

Set these environment variables in Render:

- `YOUTUBE_CHANNEL_IDS` - Comma-separated channel IDs to monitor
- `DISCOVERY_KEYWORDS` - Comma-separated keywords to search
- `PLAYLIST_URLS` - Comma-separated playlist URLs to monitor

Example:
```
YOUTUBE_CHANNEL_IDS=UCxxxxx,UCyyyyy
DISCOVERY_KEYWORDS=python tutorial,web development
PLAYLIST_URLS=https://youtube.com/playlist?list=xxxxx
```

## Step 3: Deploy to Render

### Option A: Using render.yaml (Recommended)

1. Push your code to GitHub
2. Go to Render Dashboard → New → Blueprint
3. Connect your GitHub repository
4. Render will automatically detect `render.yaml`
5. Set all environment variables in Render dashboard
6. Deploy!

### Option B: Manual Setup

1. Push your code to GitHub
2. Go to Render Dashboard → New → Background Worker
3. Connect your GitHub repository
4. Configure:
   - **Name**: `openclip-automation`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python -m src.automation`
5. Add all environment variables
6. Deploy!

## Step 4: Environment Variables

Add these in Render's Environment Variables section:

### Required
```
GEMINI_API_KEY=your_gemini_api_key
```

### Optional (Notifications)
```
DISCORD_WEBHOOK_URL=your_discord_webhook_url
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_USER=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
EMAIL_TO=recipient@email.com
```

### Optional (Content Discovery)
```
YOUTUBE_CHANNEL_IDS=channel_id1,channel_id2
DISCOVERY_KEYWORDS=keyword1,keyword2
PLAYLIST_URLS=url1,url2
```

### Optional (Scheduling)
```
SCHEDULE_INTERVAL_HOURS=6
MAX_UPLOADS_PER_DAY=5
HEALTH_CHECK_INTERVAL=300
```

## Step 5: Monitoring

### Web Dashboard (Optional)
To enable the web dashboard:

1. Create a new Web Service in Render
2. Set start command: `python -m src.web.app`
3. Set port: `5000`
4. Access at: `https://your-service.onrender.com`

### Health Check Endpoint
The automation includes a health check at `/health` endpoint.

## Step 6: Manual Job Submission

You can manually add jobs to the queue:

```python
from src.database import Database
from src.queue import JobQueue

db = Database()
queue = JobQueue(db)

# Add a job
queue.add("https://youtube.com/watch?v=VIDEO_ID", priority=10)
```

## Troubleshooting

### Service Keeps Restarting
- Check logs in Render dashboard
- Verify all required environment variables are set
- Check API key validity

### No Videos Being Discovered
- Verify channel IDs/keywords are correct
- Check discovery logs
- Ensure channels have recent videos

### Uploads Not Working
- Verify Chrome profile path (if using)
- Check rate limits (max 6 uploads/day)
- Review upload logs

### Notifications Not Sending
- Verify webhook URLs/tokens are correct
- Check notification logs
- Test each notification channel individually

## Free Tier Limitations

### Render Free Tier
- **750 hours/month** - Enough for 24/7 operation
- **Spins down after 15 min inactivity** - Use cron jobs or keep-alive
- **512MB RAM** - Should be sufficient for this use case

### Workarounds
1. **Keep-Alive**: Use a cron job service (like cron-job.org) to ping your service every 10 minutes
2. **Uptime Monitoring**: Use UptimeRobot (free) to ping your health endpoint
3. **Alternative**: Use Railway ($5 free credit/month) for true 24/7

## Cost Optimization Tips

1. **Batch Processing**: Process multiple videos in one run
2. **Smart Scheduling**: Don't run discovery too frequently
3. **Cache Everything**: Use caching to avoid re-processing
4. **Rate Limiting**: Respect YouTube quotas to avoid issues

## Support

For issues or questions:
1. Check logs in Render dashboard
2. Review error logs in database
3. Check health endpoint: `/health`
4. Review notification logs

## Next Steps

1. Monitor the first few runs
2. Adjust discovery settings based on results
3. Fine-tune rate limits
4. Set up monitoring alerts
5. Review and optimize based on statistics

