from typing import List, Dict, Optional
from src.database import Database
from src.logger import get_logger

class JobQueue:
    """Persistent job queue management."""
    
    def __init__(self, db: Optional[Database] = None):
        self.db = db or Database()
        self.logger = get_logger()
    
    def add(self, url: str, priority: int = 5, metadata: Optional[Dict] = None) -> int:
        """Add a job to the queue."""
        return self.db.add_job(url, priority, metadata)
    
    def get_next(self) -> Optional[Dict]:
        """Get the next job from the queue."""
        return self.db.get_next_job()
    
    def mark_processing(self, job_id: int):
        """Mark a job as processing."""
        self.db.update_job_status(job_id, 'processing')
    
    def mark_completed(self, job_id: int):
        """Mark a job as completed."""
        self.db.update_job_status(job_id, 'completed')
    
    def mark_failed(self, job_id: int, error_message: str):
        """Mark a job as failed."""
        self.db.update_job_status(job_id, 'failed', error_message)
    
    def should_retry(self, job_id: int) -> bool:
        """Check if a job should be retried."""
        job = self.db.get_next_job()
        if not job or job.get('id') != job_id:
            # Get job directly
            conn = self.db.db_path
            import sqlite3
            conn_obj = sqlite3.connect(conn)
            conn_obj.row_factory = sqlite3.Row
            cursor = conn_obj.cursor()
            cursor.execute('SELECT * FROM jobs WHERE id = ?', (job_id,))
            row = cursor.fetchone()
            conn_obj.close()
            
            if row:
                job = dict(row)
        
        if not job:
            return False
        
        retry_count = job.get('retry_count', 0)
        max_retries = job.get('max_retries', 3)
        
        return retry_count < max_retries
    
    def retry_job(self, job_id: int):
        """Reset a failed job for retry."""
        import sqlite3
        self.db.increment_retry(job_id)
        # Reset status to pending
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        cursor.execute('UPDATE jobs SET status = ? WHERE id = ?', ('pending', job_id))
        conn.commit()
        conn.close()
        self.logger.info(f"Job {job_id} reset for retry")
    
    def get_pending_count(self) -> int:
        """Get count of pending jobs."""
        import sqlite3
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM jobs WHERE status = ?', ('pending',))
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def get_failed_jobs(self, limit: int = 10) -> List[Dict]:
        """Get recent failed jobs."""
        import sqlite3
        conn = sqlite3.connect(self.db.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM jobs WHERE status = 'failed'
            ORDER BY completed_at DESC LIMIT ?
        ''', (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

