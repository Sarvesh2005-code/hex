import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from src.logger import get_logger

class Database:
    """SQLite database for job queue and persistence."""
    
    def __init__(self, db_path="data/automation.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.logger = get_logger()
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Jobs table (queue management)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                priority INTEGER DEFAULT 5,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,
                max_retries INTEGER DEFAULT 3,
                metadata TEXT,
                UNIQUE(url, status)
            )
        ''')
        
        # Videos table (processing history)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL UNIQUE,
                video_id TEXT,
                title TEXT,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                clips_found INTEGER DEFAULT 0,
                clips_processed INTEGER DEFAULT 0,
                processing_time REAL,
                status TEXT,
                metadata TEXT
            )
        ''')
        
        # Statistics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL UNIQUE,
                videos_processed INTEGER DEFAULT 0,
                clips_created INTEGER DEFAULT 0,
                uploads_successful INTEGER DEFAULT 0,
                uploads_failed INTEGER DEFAULT 0,
                errors_count INTEGER DEFAULT 0,
                total_processing_time REAL DEFAULT 0
            )
        ''')
        
        # Settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Error logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS error_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER,
                error_type TEXT,
                error_message TEXT,
                stack_trace TEXT,
                occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (job_id) REFERENCES jobs(id)
            )
        ''')
        
        conn.commit()
        conn.close()
        self.logger.debug("Database initialized")
    
    def add_job(self, url: str, priority: int = 5, metadata: Optional[Dict] = None) -> int:
        """Add a job to the queue."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        metadata_json = json.dumps(metadata) if metadata else None
        
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO jobs (url, priority, metadata)
                VALUES (?, ?, ?)
            ''', (url, priority, metadata_json))
            
            job_id = cursor.lastrowid
            if job_id == 0:
                # Job already exists, get its ID
                cursor.execute('SELECT id FROM jobs WHERE url = ? AND status = ?', (url, 'pending'))
                result = cursor.fetchone()
                job_id = result[0] if result else None
            
            conn.commit()
            conn.close()
            
            if job_id:
                self.logger.debug(f"Added job {job_id} for URL: {url}")
            return job_id
        except Exception as e:
            conn.close()
            self.logger.error(f"Error adding job: {e}")
            raise
    
    def get_next_job(self) -> Optional[Dict]:
        """Get the next pending job (highest priority first)."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM jobs
            WHERE status = 'pending'
            ORDER BY priority DESC, created_at ASC
            LIMIT 1
        ''')
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            job = dict(row)
            if job.get('metadata'):
                job['metadata'] = json.loads(job['metadata'])
            return job
        return None
    
    def update_job_status(self, job_id: int, status: str, error_message: Optional[str] = None):
        """Update job status."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if status == 'processing':
            cursor.execute('''
                UPDATE jobs SET status = ?, started_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (status, job_id))
        elif status in ('completed', 'failed'):
            cursor.execute('''
                UPDATE jobs SET status = ?, completed_at = CURRENT_TIMESTAMP, error_message = ?
                WHERE id = ?
            ''', (status, error_message, job_id))
        else:
            cursor.execute('UPDATE jobs SET status = ? WHERE id = ?', (status, job_id))
        
        conn.commit()
        conn.close()
        self.logger.debug(f"Updated job {job_id} status to {status}")
    
    def increment_retry(self, job_id: int):
        """Increment retry count for a job."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE jobs SET retry_count = retry_count + 1
            WHERE id = ?
        ''', (job_id,))
        
        conn.commit()
        conn.close()
    
    def add_video_record(self, url: str, video_id: Optional[str] = None, 
                        title: Optional[str] = None, clips_found: int = 0,
                        clips_processed: int = 0, processing_time: Optional[float] = None,
                        status: str = 'completed', metadata: Optional[Dict] = None):
        """Add a video processing record."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        metadata_json = json.dumps(metadata) if metadata else None
        
        cursor.execute('''
            INSERT OR REPLACE INTO videos 
            (url, video_id, title, clips_found, clips_processed, processing_time, status, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (url, video_id, title, clips_found, clips_processed, processing_time, status, metadata_json))
        
        conn.commit()
        conn.close()
        self.logger.debug(f"Added video record for: {url}")
    
    def log_error(self, job_id: Optional[int], error_type: str, 
                  error_message: str, stack_trace: Optional[str] = None):
        """Log an error."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO error_logs (job_id, error_type, error_message, stack_trace)
            VALUES (?, ?, ?, ?)
        ''', (job_id, error_type, error_message, stack_trace))
        
        conn.commit()
        conn.close()
    
    def update_statistics(self, date: str, videos_processed: int = 0, 
                         clips_created: int = 0, uploads_successful: int = 0,
                         uploads_failed: int = 0, errors_count: int = 0,
                         processing_time: float = 0):
        """Update daily statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO statistics 
            (date, videos_processed, clips_created, uploads_successful, 
             uploads_failed, errors_count, total_processing_time)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                videos_processed = videos_processed + ?,
                clips_created = clips_created + ?,
                uploads_successful = uploads_successful + ?,
                uploads_failed = uploads_failed + ?,
                errors_count = errors_count + ?,
                total_processing_time = total_processing_time + ?
        ''', (date, videos_processed, clips_created, uploads_successful, 
              uploads_failed, errors_count, processing_time,
              videos_processed, clips_created, uploads_successful,
              uploads_failed, errors_count, processing_time))
        
        conn.commit()
        conn.close()
    
    def get_statistics(self, days: int = 7) -> List[Dict]:
        """Get statistics for the last N days."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM statistics
            WHERE date >= date('now', '-' || ? || ' days')
            ORDER BY date DESC
        ''', (days,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            try:
                return json.loads(result[0])
            except:
                return result[0]
        return default
    
    def set_setting(self, key: str, value: Any):
        """Set a setting value."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        value_json = json.dumps(value) if not isinstance(value, str) else value
        
        cursor.execute('''
            INSERT OR REPLACE INTO settings (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (key, value_json))
        
        conn.commit()
        conn.close()

