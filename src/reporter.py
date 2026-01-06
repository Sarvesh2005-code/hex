import json
import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from src.logger import get_logger

class Reporter:
    """Generate processing statistics and reports."""
    
    def __init__(self, output_dir="output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.logger = get_logger()
    
    def generate_report(self, results: List[Dict[str, Any]], format: str = 'json') -> str:
        """
        Generate a processing report.
        
        Args:
            results: List of processing results from process_single_video
            format: 'json' or 'csv'
        
        Returns:
            Path to generated report file
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Calculate statistics
        total_videos = len(results)
        successful_videos = sum(1 for r in results if r.get('success', False))
        total_clips_found = sum(r.get('clips_found', 0) for r in results)
        total_clips_processed = sum(r.get('clips_processed', 0) for r in results)
        total_errors = sum(len(r.get('errors', [])) for r in results)
        total_time = sum(r.get('processing_time', 0) for r in results)
        
        stats = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_videos': total_videos,
                'successful_videos': successful_videos,
                'failed_videos': total_videos - successful_videos,
                'total_clips_found': total_clips_found,
                'total_clips_processed': total_clips_processed,
                'total_errors': total_errors,
                'total_processing_time_seconds': round(total_time, 2),
                'average_time_per_video': round(total_time / total_videos, 2) if total_videos > 0 else 0
            },
            'videos': results
        }
        
        if format == 'json':
            report_path = self.output_dir / f"report_{timestamp}.json"
            with open(report_path, 'w') as f:
                json.dump(stats, f, indent=2)
            self.logger.info(f"Report saved to: {report_path}")
            return str(report_path)
        
        elif format == 'csv':
            report_path = self.output_dir / f"report_{timestamp}.csv"
            with open(report_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'URL', 'Success', 'Clips Found', 'Clips Processed', 
                    'Processing Time (s)', 'Errors'
                ])
                
                for result in results:
                    writer.writerow([
                        result.get('url', ''),
                        result.get('success', False),
                        result.get('clips_found', 0),
                        result.get('clips_processed', 0),
                        round(result.get('processing_time', 0), 2),
                        '; '.join(result.get('errors', []))
                    ])
            
            self.logger.info(f"Report saved to: {report_path}")
            return str(report_path)
        
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def print_summary(self, results: List[Dict[str, Any]]):
        """Print a summary to console."""
        total_videos = len(results)
        successful_videos = sum(1 for r in results if r.get('success', False))
        total_clips_processed = sum(r.get('clips_processed', 0) for r in results)
        total_time = sum(r.get('processing_time', 0) for r in results)
        
        print("\n" + "="*60)
        print("PROCESSING SUMMARY")
        print("="*60)
        print(f"Total Videos: {total_videos}")
        print(f"Successful: {successful_videos}")
        print(f"Failed: {total_videos - successful_videos}")
        print(f"Total Clips Created: {total_clips_processed}")
        print(f"Total Time: {total_time:.2f}s")
        if total_videos > 0:
            print(f"Average Time per Video: {total_time / total_videos:.2f}s")
        print("="*60)

