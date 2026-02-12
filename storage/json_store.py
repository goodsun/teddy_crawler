"""
JSON Store - Save crawled data to JSON files
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path


class JSONStore:
    """Handle JSON storage for crawled data"""
    
    def __init__(self, output_dir: str = 'output'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def save_single_result(self, data: Dict[str, Any], filename: Optional[str] = None) -> str:
        """Save single crawl result to JSON file"""
        try:
            if not filename:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                url_part = self._sanitize_url_for_filename(data.get('url', 'unknown'))
                filename = f"crawl_{timestamp}_{url_part}.json"
            
            if not filename.endswith('.json'):
                filename += '.json'
            
            filepath = self.output_dir / filename
            
            # Add metadata
            output_data = {
                'metadata': {
                    'crawled_at': datetime.now().isoformat(),
                    'url': data.get('url', ''),
                    'crawler_version': '1.0.0'
                },
                'data': data
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Saved to: {filepath}")
            return str(filepath)
            
        except Exception as e:
            print(f"❌ Error saving to JSON: {e}")
            raise
    
    def save_batch_results(self, results: List[Dict[str, Any]], filename: Optional[str] = None) -> str:
        """Save batch crawl results to JSON file"""
        try:
            if not filename:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"batch_crawl_{timestamp}.json"
            
            if not filename.endswith('.json'):
                filename += '.json'
            
            filepath = self.output_dir / filename
            
            # Add metadata
            output_data = {
                'metadata': {
                    'crawled_at': datetime.now().isoformat(),
                    'total_urls': len(results),
                    'crawler_version': '1.0.0'
                },
                'results': results
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Batch saved to: {filepath}")
            return str(filepath)
            
        except Exception as e:
            print(f"❌ Error saving batch to JSON: {e}")
            raise
    
    def append_to_jsonl(self, data: Dict[str, Any], filename: str) -> str:
        """Append single result to JSONL file (one JSON object per line)"""
        try:
            if not filename.endswith('.jsonl'):
                filename += '.jsonl'
            
            filepath = self.output_dir / filename
            
            # Add metadata to each record
            record = {
                'crawled_at': datetime.now().isoformat(),
                **data
            }
            
            with open(filepath, 'a', encoding='utf-8') as f:
                json.dump(record, f, ensure_ascii=False)
                f.write('\n')
            
            return str(filepath)
            
        except Exception as e:
            print(f"❌ Error appending to JSONL: {e}")
            raise
    
    def load_results(self, filename: str) -> Dict[str, Any]:
        """Load results from JSON file"""
        try:
            filepath = self.output_dir / filename
            
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return data
            
        except Exception as e:
            print(f"❌ Error loading from JSON: {e}")
            raise
    
    def load_jsonl_results(self, filename: str) -> List[Dict[str, Any]]:
        """Load results from JSONL file"""
        try:
            filepath = self.output_dir / filename
            results = []
            
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        results.append(json.loads(line))
            
            return results
            
        except Exception as e:
            print(f"❌ Error loading from JSONL: {e}")
            raise
    
    def list_output_files(self) -> List[str]:
        """List all output files"""
        try:
            files = []
            for file_path in self.output_dir.glob('*'):
                if file_path.is_file() and file_path.suffix in ['.json', '.jsonl']:
                    files.append(file_path.name)
            
            return sorted(files, reverse=True)  # Most recent first
            
        except Exception as e:
            print(f"❌ Error listing files: {e}")
            return []
    
    def save_screenshot(self, screenshot_bytes: bytes, url: str, suffix: str = '') -> str:
        """Save screenshot to output directory"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            url_part = self._sanitize_url_for_filename(url)
            
            if suffix:
                filename = f"screenshot_{timestamp}_{url_part}_{suffix}.png"
            else:
                filename = f"screenshot_{timestamp}_{url_part}.png"
            
            filepath = self.output_dir / filename
            
            with open(filepath, 'wb') as f:
                f.write(screenshot_bytes)
            
            print(f"📸 Screenshot saved to: {filepath}")
            return str(filepath)
            
        except Exception as e:
            print(f"❌ Error saving screenshot: {e}")
            raise
    
    def create_summary_report(self, results: List[Dict[str, Any]]) -> str:
        """Create a summary report of crawl results"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"summary_report_{timestamp}.json"
            filepath = self.output_dir / filename
            
            # Generate summary statistics
            total_urls = len(results)
            successful = sum(1 for r in results if r.get('success', False))
            failed = total_urls - successful
            
            # Extract common statistics
            text_extracted = sum(1 for r in results if r.get('data', {}).get('text'))
            links_extracted = sum(1 for r in results if r.get('data', {}).get('links'))
            images_extracted = sum(1 for r in results if r.get('data', {}).get('images'))
            
            summary = {
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'crawler_version': '1.0.0'
                },
                'statistics': {
                    'total_urls': total_urls,
                    'successful_crawls': successful,
                    'failed_crawls': failed,
                    'success_rate': round((successful / total_urls * 100) if total_urls > 0 else 0, 2),
                    'text_extraction_count': text_extracted,
                    'links_extraction_count': links_extracted,
                    'images_extraction_count': images_extracted
                },
                'detailed_results': results
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            
            print(f"📊 Summary report saved to: {filepath}")
            return str(filepath)
            
        except Exception as e:
            print(f"❌ Error creating summary report: {e}")
            raise
    
    def _sanitize_url_for_filename(self, url: str) -> str:
        """Sanitize URL to create safe filename"""
        if not url:
            return 'unknown'
        
        # Remove protocol and replace unsafe characters
        clean = url.replace('http://', '').replace('https://', '')
        clean = clean.replace('/', '_')
        clean = clean.replace('?', '_')
        clean = clean.replace('&', '_')
        clean = clean.replace('=', '_')
        clean = clean.replace('#', '_')
        clean = clean.replace(':', '_')
        
        # Limit length
        return clean[:50] if len(clean) > 50 else clean