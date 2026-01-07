"""
Simple web dashboard for monitoring automation.
"""
from flask import Flask, jsonify, render_template_string
from src.database import Database
from src.queue import JobQueue
from src.health import HealthMonitor
from src.ratelimit import RateLimiter

app = Flask(__name__)
db = Database()
queue = JobQueue(db)
health_monitor = HealthMonitor(db)
rate_limiter = RateLimiter(db)

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>OpenClip Automation Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .stat { display: inline-block; margin: 10px; padding: 15px; background: #f0f0f0; border-radius: 5px; }
        .stat-value { font-size: 24px; font-weight: bold; }
        .stat-label { font-size: 12px; color: #666; }
    </style>
</head>
<body>
    <h1>OpenClip Automation Dashboard</h1>
    <div id="stats"></div>
    <script>
        function updateStats() {
            fetch('/api/stats').then(r => r.json()).then(data => {
                document.getElementById('stats').innerHTML = `
                    <div class="stat">
                        <div class="stat-value">${data.queue.pending}</div>
                        <div class="stat-label">Pending Jobs</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">${data.queue.processing}</div>
                        <div class="stat-label">Processing</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">${data.queue.failed}</div>
                        <div class="stat-label">Failed</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">${data.quota.daily.remaining}</div>
                        <div class="stat-label">Daily Uploads Remaining</div>
                    </div>
                `;
            });
        }
        updateStats();
        setInterval(updateStats, 5000);
    </script>
</body>
</html>
"""

@app.route('/')
def dashboard():
    """Main dashboard page."""
    return render_template_string(DASHBOARD_HTML)

@app.route('/health')
def health():
    """Health check endpoint."""
    health_status = health_monitor.check_health()
    return jsonify(health_status), 200 if health_status['status'] == 'healthy' else 503

@app.route('/api/stats')
def stats():
    """Get statistics."""
    import sqlite3
    conn = sqlite3.connect(db.db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM jobs WHERE status = ?', ('pending',))
    pending = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM jobs WHERE status = ?', ('processing',))
    processing = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM jobs WHERE status = ?', ('failed',))
    failed = cursor.fetchone()[0]
    
    conn.close()
    
    quota_status = rate_limiter.get_quota_status()
    
    return jsonify({
        'queue': {
            'pending': pending,
            'processing': processing,
            'failed': failed
        },
        'quota': quota_status
    })

@app.route('/api/jobs')
def jobs():
    """Get recent jobs."""
    import sqlite3
    conn = sqlite3.connect(db.db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM jobs
        ORDER BY created_at DESC
        LIMIT 50
    ''')
    
    jobs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(jobs)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)

