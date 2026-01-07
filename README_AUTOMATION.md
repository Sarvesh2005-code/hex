# OpenClip 24/7 Autonomous System

## Features

✅ **Fully Autonomous** - Runs 24/7 without manual intervention
✅ **Content Discovery** - Automatically finds videos from channels, keywords, playlists
✅ **Queue Management** - Persistent job queue with retry logic
✅ **Rate Limiting** - Respects YouTube upload quotas
✅ **Multi-Channel Notifications** - Email, Discord, Telegram
✅ **Health Monitoring** - Automatic health checks and alerts
✅ **Web Dashboard** - Monitor status via web interface
✅ **Free Hosting** - Deploy on Render's free tier

## Architecture

```
┌─────────────────┐
│  Content        │
│  Discovery      │──┐
└─────────────────┘  │
                     │
┌─────────────────┐  │    ┌──────────────┐
│   Scheduler     │──┼───▶│   Job Queue   │
└─────────────────┘  │    └──────────────┘
                     │           │
┌─────────────────┐  │           ▼
│  Health Monitor │  │    ┌──────────────┐
└─────────────────┘  │    │   Processor   │
                     │    └──────────────┘
┌─────────────────┐  │           │
│  Rate Limiter   │──┼───────────┘
└─────────────────┘  │           │
                     │           ▼
┌─────────────────┐  │    ┌──────────────┐
│   Notifier      │◀─┼────│   YouTube     │
└─────────────────┘  │    │   Upload      │
                     │    └──────────────┘
```

## Quick Start

1. **Setup Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

2. **Run Locally**
   ```bash
   python -m src.automation
   ```

3. **Deploy to Render**
   - See `DEPLOYMENT.md` for detailed instructions

## Components

### Content Discovery (`src/discovery.py`)
- Monitor YouTube channels
- Search by keywords
- Monitor playlists
- Filter and deduplicate URLs

### Queue Management (`src/queue.py`)
- Persistent SQLite database
- Job status tracking
- Automatic retry logic
- Priority-based processing

### Scheduler (`src/scheduler.py`)
- Cron-like scheduling
- Interval-based tasks
- Daily/hourly schedules

### Notifications (`src/notifier.py`)
- Discord webhooks
- Telegram bot
- Email (SMTP)
- Rich formatting

### Health Monitoring (`src/health.py`)
- Disk space monitoring
- Memory usage tracking
- API connectivity checks
- Error rate tracking

### Rate Limiting (`src/ratelimit.py`)
- Daily upload limits
- Hourly rate limiting
- Quota tracking
- Automatic throttling

## Configuration

All settings can be configured via environment variables or `config.yaml`.

See `AUTOMATION_SETUP.md` for detailed configuration guide.

## Monitoring

### Web Dashboard
Access at: `http://localhost:5000` (when running locally)

### Health Endpoint
```bash
curl http://localhost:5000/health
```

### Statistics API
```bash
curl http://localhost:5000/api/stats
```

## Notifications

The system sends notifications for:
- ✅ Successful video uploads
- ❌ Upload failures
- ⚠️ Processing errors
- 🔴 Health alerts
- 📊 Daily summaries
- ⚠️ Quota warnings

## Free Hosting Options

### Render (Recommended)
- 750 hours/month free
- Easy GitHub integration
- Auto-deploy on push

### Railway
- $5 free credit/month
- True 24/7 operation
- Easy setup

### GitHub Actions
- 2000 minutes/month free
- Not suitable for 24/7
- Good for scheduled tasks

## Tips for Free Tier

1. **Use Keep-Alive**: Ping service every 10 minutes to prevent spin-down
2. **Batch Processing**: Process multiple videos in one run
3. **Smart Scheduling**: Don't run discovery too frequently
4. **Cache Everything**: Avoid re-processing videos
5. **Rate Limiting**: Respect YouTube quotas

## Troubleshooting

### Service Keeps Restarting
- Check logs for errors
- Verify environment variables
- Check API key validity

### No Videos Discovered
- Verify channel IDs/keywords
- Check discovery logs
- Ensure sources have recent content

### Notifications Not Working
- Verify webhook URLs/tokens
- Check notification logs
- Test each channel individually

## Support

For issues:
1. Check logs in `logs/` directory
2. Review database: `data/automation.db`
3. Check health endpoint
4. Review notification logs

## License

Same as main project.

