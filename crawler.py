#!/usr/bin/env python3
"""
Teddy Crawler - 汎用Webクローラー基盤
Playwrightベースの設定ファイル駆動型Webクローラー

使用例:
  python3 crawler.py fetch https://example.com
  python3 crawler.py batch config.yaml
  python3 crawler.py fetch https://example.com --screenshot --profile=default
"""

import asyncio
import argparse
import sys
import time
import yaml
import random
from pathlib import Path
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

# 相対インポート
from extractors import TextExtractor, LinkExtractor, ImageExtractor
from storage import JSONStore


class TeddyCrawler:
    """メインクローラークラス"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or self._load_default_config()
        self.storage = JSONStore(output_dir=self._get_output_dir())
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        
        # Extractors
        self.text_extractor = TextExtractor()
        self.link_extractor = LinkExtractor()
        self.image_extractor = ImageExtractor()
        
        # Profile settings
        self.profile_dir = Path(__file__).parent / "profiles"
        self.profile_dir.mkdir(exist_ok=True)
        
        # Reference to external profiles
        self.external_profile_dir = Path("/home/ec2-user/tools/teddy_browser/profiles")
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.start_browser()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close_browser()
    
    async def start_browser(self):
        """ブラウザを起動"""
        try:
            self.playwright = await async_playwright().start()
            
            # Browser type and launch options
            browser_options = {
                'headless': not self.config.get('debug', {}).get('headful', False),
                'args': ['--no-sandbox', '--disable-dev-shm-usage']
            }
            
            if self.config.get('debug', {}).get('devtools', False):
                browser_options['devtools'] = True
            
            self.browser = await self.playwright.chromium.launch(**browser_options)
            
            # Create context with profile if specified
            await self._create_context()
            
            print("🚀 Browser started successfully")
            
        except Exception as e:
            print(f"❌ Error starting browser: {e}")
            raise
    
    async def close_browser(self):
        """ブラウザを終了"""
        try:
            if self.context:
                await self.context.close()
            
            if self.browser:
                await self.browser.close()
            
            if hasattr(self, 'playwright'):
                await self.playwright.stop()
            
            print("🛑 Browser closed")
            
        except Exception as e:
            print(f"❌ Error closing browser: {e}")
    
    async def fetch_single_url(self, url: str, custom_config: Optional[Dict] = None) -> Dict[str, Any]:
        """単一URLを取得"""
        print(f"🎯 Fetching: {url}")
        
        config = {**self.config, **(custom_config or {})}
        
        try:
            page = await self.context.new_page()
            
            # User-Agentを設定
            user_agent = config.get('settings', {}).get('user_agent')
            if user_agent:
                await page.set_extra_http_headers({'User-Agent': user_agent})
            
            # ページに移動
            timeout = config.get('settings', {}).get('timeout', 30000)
            await page.goto(url, timeout=timeout, wait_until='domcontentloaded')
            
            # 待機処理
            wait_time = config.get('settings', {}).get('delay', 2000)
            if config.get('wait'):
                wait_time = config['wait']
            
            if wait_time > 0:
                await page.wait_for_timeout(wait_time)
            
            # スクロール処理
            if config.get('scroll', False):
                await self._handle_scrolling(page, config)
            
            # データ抽出
            result = {
                'url': url,
                'timestamp': time.time(),
                'success': True,
                'data': {}
            }
            
            # 抽出タイプに応じてデータを取得
            extract_types = config.get('extract', ['text', 'links', 'images'])
            selectors = config.get('selectors', {})
            
            if 'text' in extract_types:
                if selectors:
                    text_data = await self.text_extractor.extract_with_selectors(page, selectors)
                else:
                    text_data = await self.text_extractor.extract_all_text(page)
                result['data']['text'] = text_data
            
            if 'links' in extract_types:
                if selectors:
                    links_data = await self.link_extractor.extract_with_selectors(page, selectors)
                else:
                    links_data = await self.link_extractor.extract_all_links(page)
                result['data']['links'] = links_data
            
            if 'images' in extract_types:
                if selectors:
                    images_data = await self.image_extractor.extract_with_selectors(page, selectors)
                else:
                    images_data = await self.image_extractor.extract_all_images(page)
                result['data']['images'] = images_data
            
            # スクリーンショット
            if config.get('screenshot', False):
                screenshot = await page.screenshot(full_page=True)
                screenshot_path = self.storage.save_screenshot(screenshot, url)
                result['screenshot'] = screenshot_path
            
            await page.close()
            
            print(f"✅ Successfully crawled: {url}")
            return result
            
        except Exception as e:
            print(f"❌ Error crawling {url}: {e}")
            return {
                'url': url,
                'timestamp': time.time(),
                'success': False,
                'error': str(e)
            }
    
    async def fetch_batch(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """バッチでURLを取得"""
        print(f"📦 Starting batch crawl: {len(jobs)} jobs")
        
        results = []
        
        for i, job in enumerate(jobs, 1):
            print(f"\n--- Job {i}/{len(jobs)}: {job.get('name', 'unnamed')} ---")
            
            # Job specific config
            job_config = {**self.config.get('settings', {}), **job}
            
            result = await self.fetch_single_url(job['url'], job_config)
            result['job_name'] = job.get('name', f'job_{i}')
            results.append(result)
            
            # Rate limiting
            delay = self.config.get('settings', {}).get('delay', 2000)
            if delay > 0 and i < len(jobs):  # Don't wait after last job
                print(f"⏳ Waiting {delay}ms...")
                await asyncio.sleep(delay / 1000)
        
        print(f"\n🎉 Batch crawl completed: {len(results)} results")
        return results
    
    async def _create_context(self):
        """ブラウザコンテキストを作成"""
        context_options = {}
        
        # Profile設定
        profile_name = self.config.get('settings', {}).get('profile')
        if profile_name:
            profile_path = self._get_profile_path(profile_name)
            if profile_path and profile_path.exists():
                context_options['user_data_dir'] = str(profile_path)
                print(f"📁 Using profile: {profile_path}")
        
        # Viewport設定
        context_options['viewport'] = {'width': 1920, 'height': 1080}
        
        self.context = await self.browser.new_context(**context_options)
    
    async def _handle_scrolling(self, page: Page, config: Dict):
        """スクロール処理"""
        try:
            scroll_count = config.get('scroll_count')
            
            if scroll_count:
                # 指定回数スクロール
                for i in range(scroll_count):
                    await page.evaluate('window.scrollBy(0, window.innerHeight)')
                    await page.wait_for_timeout(1000)
                    print(f"📜 Scroll {i+1}/{scroll_count}")
            else:
                # 最下部までスクロール
                previous_height = 0
                scroll_attempts = 0
                max_attempts = 50  # 無限ループ防止
                
                while scroll_attempts < max_attempts:
                    await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                    await page.wait_for_timeout(1000)
                    
                    current_height = await page.evaluate('document.body.scrollHeight')
                    if current_height == previous_height:
                        break
                    
                    previous_height = current_height
                    scroll_attempts += 1
                    
                    if scroll_attempts % 10 == 0:
                        print(f"📜 Scrolling... ({scroll_attempts} attempts)")
                
                print(f"📜 Scrolling completed after {scroll_attempts} attempts")
                
        except Exception as e:
            print(f"❌ Error during scrolling: {e}")
    
    def _get_profile_path(self, profile_name: str) -> Optional[Path]:
        """プロファイルパスを取得"""
        # First check local profiles
        local_profile = self.profile_dir / profile_name
        if local_profile.exists():
            return local_profile
        
        # Then check external teddy_browser profiles
        if self.external_profile_dir.exists():
            external_profile = self.external_profile_dir / profile_name
            if external_profile.exists():
                return external_profile
        
        return None
    
    def _get_output_dir(self) -> str:
        """出力ディレクトリを取得"""
        output_dir = Path(__file__).parent / "output"
        output_dir.mkdir(exist_ok=True)
        return str(output_dir)
    
    def _load_default_config(self) -> Dict:
        """デフォルト設定を読み込み"""
        return {
            'settings': {
                'delay': 2000,
                'timeout': 30000,
                'user_agent': 'TeddyCrawler/1.0 (Educational Purpose)',
                'screenshot': False,
                'output_format': 'json'
            },
            'debug': {
                'verbose': False,
                'headful': False,
                'devtools': False
            }
        }
    
    @classmethod
    def load_config(cls, config_path: str) -> Dict:
        """設定ファイルを読み込み"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"❌ Error loading config: {e}")
            return {}


# CLI Functions

async def fetch_command(args):
    """Fetch command implementation"""
    config = TeddyCrawler.load_config('config.yaml') if Path('config.yaml').exists() else {}
    
    # Apply command line overrides
    if args.screenshot:
        config.setdefault('settings', {})['screenshot'] = True
    
    if args.profile:
        config.setdefault('settings', {})['profile'] = args.profile
    
    if args.user_agent:
        config.setdefault('settings', {})['user_agent'] = args.user_agent
    
    if args.headful:
        config.setdefault('debug', {})['headful'] = True
    
    async with TeddyCrawler(config) as crawler:
        # Prepare custom config
        custom_config = {
            'extract': ['text', 'links', 'images'],
            'screenshot': args.screenshot
        }
        
        if args.wait:
            custom_config['wait'] = args.wait
        
        if args.scroll:
            custom_config['scroll'] = True
        
        result = await crawler.fetch_single_url(args.url, custom_config)
        
        # Save result
        if args.output:
            filepath = crawler.storage.save_single_result(result, args.output)
        else:
            filepath = crawler.storage.save_single_result(result)
        
        print(f"\n📁 Result saved to: {filepath}")


async def batch_command(args):
    """Batch command implementation"""
    config_path = args.config
    
    if not Path(config_path).exists():
        print(f"❌ Config file not found: {config_path}")
        return
    
    config = TeddyCrawler.load_config(config_path)
    jobs = config.get('jobs', [])
    
    if not jobs:
        print("❌ No jobs defined in config file")
        return
    
    async with TeddyCrawler(config) as crawler:
        results = await crawler.fetch_batch(jobs)
        
        # Save results
        if args.output:
            filepath = crawler.storage.save_batch_results(results, args.output)
        else:
            filepath = crawler.storage.save_batch_results(results)
        
        # Create summary
        summary_path = crawler.storage.create_summary_report(results)
        
        print(f"\n📁 Results saved to: {filepath}")
        print(f"📊 Summary saved to: {summary_path}")


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description='Teddy Crawler - 汎用Webクローラー基盤')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Fetch command
    fetch_parser = subparsers.add_parser('fetch', help='単一URLを取得')
    fetch_parser.add_argument('url', help='取得するURL')
    fetch_parser.add_argument('--output', '-o', help='出力ファイル名')
    fetch_parser.add_argument('--screenshot', '-s', action='store_true', help='スクリーンショットを取得')
    fetch_parser.add_argument('--profile', '-p', help='使用するプロファイル名')
    fetch_parser.add_argument('--user-agent', '-ua', help='User-Agent文字列')
    fetch_parser.add_argument('--wait', '-w', type=int, help='待機時間（ミリ秒）')
    fetch_parser.add_argument('--scroll', action='store_true', help='無限スクロール対応')
    fetch_parser.add_argument('--headful', action='store_true', help='ブラウザを表示')
    
    # Batch command
    batch_parser = subparsers.add_parser('batch', help='バッチで複数URLを取得')
    batch_parser.add_argument('config', help='設定ファイルパス')
    batch_parser.add_argument('--output', '-o', help='出力ファイル名')
    
    # List command
    list_parser = subparsers.add_parser('list', help='出力ファイル一覧を表示')
    
    args = parser.parse_args()
    
    if args.command == 'fetch':
        asyncio.run(fetch_command(args))
    elif args.command == 'batch':
        asyncio.run(batch_command(args))
    elif args.command == 'list':
        storage = JSONStore()
        files = storage.list_output_files()
        if files:
            print("📁 Output files:")
            for file in files:
                print(f"  - {file}")
        else:
            print("📁 No output files found")
    else:
        parser.print_help()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)