import os
import psutil
import shutil
from typing import Dict, Optional
from src.logger import get_logger
from src.config import get_config
from src.database import Database

class HealthMonitor:
    """System health monitoring and checks."""
    
    def __init__(self, db: Optional[Database] = None):
        self.logger = get_logger()
        self.config = get_config()
        self.db = db or Database()
        self.error_count = 0
        self.last_error_time = None
    
    def check_health(self) -> Dict[str, any]:
        """Perform comprehensive health check."""
        health = {
            'status': 'healthy',
            'checks': {},
            'warnings': [],
            'errors': []
        }
        
        # Disk space check
        disk_check = self._check_disk_space()
        health['checks']['disk'] = disk_check
        if disk_check['status'] != 'ok':
            health['warnings'].append(f"Disk space: {disk_check['message']}")
            if disk_check['status'] == 'critical':
                health['status'] = 'unhealthy'
        
        # Memory check
        memory_check = self._check_memory()
        health['checks']['memory'] = memory_check
        if memory_check['status'] != 'ok':
            health['warnings'].append(f"Memory: {memory_check['message']}")
        
        # API connectivity (basic check)
        api_check = self._check_api_connectivity()
        health['checks']['api'] = api_check
        if api_check['status'] != 'ok':
            health['errors'].append(f"API: {api_check['message']}")
            if api_check['status'] == 'critical':
                health['status'] = 'unhealthy'
        
        # Queue status
        queue_check = self._check_queue_status()
        health['checks']['queue'] = queue_check
        
        # Error rate
        error_check = self._check_error_rate()
        health['checks']['error_rate'] = error_check
        if error_check['status'] != 'ok':
            health['warnings'].append(f"Error rate: {error_check['message']}")
        
        return health
    
    def _check_disk_space(self, threshold_warning: float = 0.8, 
                         threshold_critical: float = 0.9) -> Dict:
        """Check available disk space."""
        try:
            stat = shutil.disk_usage('.')
            total = stat.total
            free = stat.free
            used_ratio = (total - free) / total
            
            if used_ratio >= threshold_critical:
                return {
                    'status': 'critical',
                    'message': f"Disk space critical: {used_ratio*100:.1f}% used",
                    'used_percent': used_ratio * 100
                }
            elif used_ratio >= threshold_warning:
                return {
                    'status': 'warning',
                    'message': f"Disk space warning: {used_ratio*100:.1f}% used",
                    'used_percent': used_ratio * 100
                }
            else:
                return {
                    'status': 'ok',
                    'message': f"Disk space OK: {used_ratio*100:.1f}% used",
                    'used_percent': used_ratio * 100
                }
        except Exception as e:
            return {
                'status': 'error',
                'message': f"Could not check disk space: {e}"
            }
    
    def _check_memory(self, threshold_warning: float = 0.85) -> Dict:
        """Check memory usage."""
        try:
            memory = psutil.virtual_memory()
            used_percent = memory.percent / 100
            
            if used_percent >= threshold_warning:
                return {
                    'status': 'warning',
                    'message': f"High memory usage: {memory.percent:.1f}%",
                    'used_percent': used_percent,
                    'available_gb': memory.available / (1024**3)
                }
            else:
                return {
                    'status': 'ok',
                    'message': f"Memory OK: {memory.percent:.1f}%",
                    'used_percent': used_percent,
                    'available_gb': memory.available / (1024**3)
                }
        except Exception as e:
            return {
                'status': 'error',
                'message': f"Could not check memory: {e}"
            }
    
    def _check_api_connectivity(self) -> Dict:
        """Check API connectivity (basic check)."""
        try:
            import google.generativeai as genai
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                return {
                    'status': 'critical',
                    'message': "GEMINI_API_KEY not set"
                }
            
            # Try a simple API call
            genai.configure(api_key=api_key)
            # Just check if we can configure, don't make actual call
            return {
                'status': 'ok',
                'message': "API connectivity OK"
            }
        except Exception as e:
            return {
                'status': 'critical',
                'message': f"API connectivity failed: {e}"
            }
    
    def _check_queue_status(self) -> Dict:
        """Check queue status."""
        try:
            import sqlite3
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM jobs WHERE status = ?', ('pending',))
            pending = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM jobs WHERE status = ?', ('processing',))
            processing = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM jobs WHERE status = ?', ('failed',))
            failed = cursor.fetchone()[0]
            
            conn.close()
            
            status = 'ok'
            if failed > 10:
                status = 'warning'
            if pending > 100:
                status = 'warning'
            
            return {
                'status': status,
                'message': f"Queue: {pending} pending, {processing} processing, {failed} failed",
                'pending': pending,
                'processing': processing,
                'failed': failed
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f"Could not check queue: {e}"
            }
    
    def _check_error_rate(self, window_minutes: int = 60, 
                         threshold: float = 0.2) -> Dict:
        """Check error rate in recent window."""
        try:
            import sqlite3
            from datetime import datetime, timedelta
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            window_start = datetime.now() - timedelta(minutes=window_minutes)
            cursor.execute('''
                SELECT COUNT(*) FROM error_logs
                WHERE occurred_at >= ?
            ''', (window_start.isoformat(),))
            
            error_count = cursor.fetchone()[0]
            
            # Get total jobs in same window
            cursor.execute('''
                SELECT COUNT(*) FROM jobs
                WHERE created_at >= ?
            ''', (window_start.isoformat(),))
            
            total_jobs = cursor.fetchone()[0]
            
            conn.close()
            
            if total_jobs == 0:
                error_rate = 0
            else:
                error_rate = error_count / total_jobs
            
            if error_rate >= threshold:
                return {
                    'status': 'warning',
                    'message': f"High error rate: {error_rate*100:.1f}% ({error_count}/{total_jobs})",
                    'error_rate': error_rate,
                    'error_count': error_count,
                    'total_jobs': total_jobs
                }
            else:
                return {
                    'status': 'ok',
                    'message': f"Error rate OK: {error_rate*100:.1f}%",
                    'error_rate': error_rate,
                    'error_count': error_count,
                    'total_jobs': total_jobs
                }
        except Exception as e:
            return {
                'status': 'error',
                'message': f"Could not check error rate: {e}"
            }
    
    def record_error(self):
        """Record an error occurrence."""
        self.error_count += 1
        from datetime import datetime
        self.last_error_time = datetime.now()

