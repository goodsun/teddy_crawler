"""
Link Extractor - Extract links from web pages
"""

from playwright.async_api import Page
from typing import Dict, List, Any, Optional
from urllib.parse import urljoin, urlparse
import re


class LinkExtractor:
    """Extract links from web pages"""
    
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url
        self.exclude_patterns = [
            r'javascript:',
            r'mailto:',
            r'tel:',
            r'#$',  # Fragment-only links
        ]
    
    async def extract_all_links(self, page: Page) -> Dict[str, Any]:
        """Extract all links from page"""
        try:
            result = {
                'internal_links': [],
                'external_links': [],
                'navigation_links': [],
                'content_links': [],
                'images_with_links': [],
                'total_count': 0
            }
            
            # Get current page URL for relative link resolution
            current_url = page.url
            parsed_current = urlparse(current_url)
            base_domain = f"{parsed_current.scheme}://{parsed_current.netloc}"
            
            # Extract all links
            links = await page.query_selector_all('a[href]')
            
            for link in links:
                try:
                    href = await link.get_attribute('href')
                    text = await link.inner_text()
                    title = await link.get_attribute('title')
                    
                    if not href or self._should_exclude(href):
                        continue
                    
                    # Resolve relative URLs
                    absolute_url = urljoin(current_url, href)
                    
                    link_data = {
                        'url': absolute_url,
                        'text': text.strip() if text else '',
                        'title': title if title else '',
                        'original_href': href
                    }
                    
                    # Categorize link
                    if self._is_internal_link(absolute_url, base_domain):
                        result['internal_links'].append(link_data)
                    else:
                        result['external_links'].append(link_data)
                    
                    # Check if in navigation
                    if await self._is_navigation_link(link):
                        result['navigation_links'].append(link_data)
                    else:
                        result['content_links'].append(link_data)
                    
                    # Check if link contains image
                    img = await link.query_selector('img')
                    if img:
                        img_src = await img.get_attribute('src')
                        img_alt = await img.get_attribute('alt')
                        link_data['image'] = {
                            'src': urljoin(current_url, img_src) if img_src else '',
                            'alt': img_alt if img_alt else ''
                        }
                        result['images_with_links'].append(link_data)
                    
                except Exception as e:
                    print(f"Error processing link: {e}")
                    continue
            
            result['total_count'] = len(result['internal_links']) + len(result['external_links'])
            
            return result
            
        except Exception as e:
            print(f"Error extracting links: {e}")
            return {}
    
    async def extract_with_selectors(self, page: Page, selectors: Dict[str, str]) -> Dict[str, Any]:
        """Extract links using custom CSS selectors"""
        result = {}
        current_url = page.url
        
        for key, selector in selectors.items():
            try:
                elements = await page.query_selector_all(selector)
                links = []
                
                for element in elements:
                    # Try to get href from element or find link within element
                    href = await element.get_attribute('href')
                    
                    if not href:
                        # Look for link within element
                        link_child = await element.query_selector('a[href]')
                        if link_child:
                            href = await link_child.get_attribute('href')
                    
                    if href and not self._should_exclude(href):
                        text = await element.inner_text()
                        title = await element.get_attribute('title')
                        
                        link_data = {
                            'url': urljoin(current_url, href),
                            'text': text.strip() if text else '',
                            'title': title if title else '',
                            'original_href': href
                        }
                        links.append(link_data)
                
                if links:
                    result[key] = links
                    
            except Exception as e:
                print(f"Error with selector '{selector}': {e}")
                continue
        
        return result
    
    async def extract_specific_patterns(self, page: Page, patterns: List[str]) -> Dict[str, List[Dict]]:
        """Extract links matching specific patterns"""
        result = {}
        
        try:
            all_links = await page.query_selector_all('a[href]')
            current_url = page.url
            
            for pattern in patterns:
                matching_links = []
                
                for link in all_links:
                    href = await link.get_attribute('href')
                    if not href:
                        continue
                    
                    if re.search(pattern, href):
                        text = await link.inner_text()
                        title = await link.get_attribute('title')
                        
                        link_data = {
                            'url': urljoin(current_url, href),
                            'text': text.strip() if text else '',
                            'title': title if title else '',
                            'original_href': href,
                            'matched_pattern': pattern
                        }
                        matching_links.append(link_data)
                
                if matching_links:
                    result[f'pattern_{pattern}'] = matching_links
            
            return result
            
        except Exception as e:
            print(f"Error extracting pattern links: {e}")
            return {}
    
    def _should_exclude(self, href: str) -> bool:
        """Check if link should be excluded"""
        if not href or href.strip() == '':
            return True
        
        for pattern in self.exclude_patterns:
            if re.search(pattern, href, re.IGNORECASE):
                return True
        
        return False
    
    def _is_internal_link(self, url: str, base_domain: str) -> bool:
        """Check if link is internal to the site"""
        try:
            parsed = urlparse(url)
            return parsed.netloc == '' or url.startswith(base_domain)
        except:
            return False
    
    async def _is_navigation_link(self, element) -> bool:
        """Check if link is likely a navigation link"""
        try:
            # Check if link is within common navigation selectors
            nav_selectors = ['nav', '.nav', '.navigation', '.menu', 'header', 'footer', '.sidebar']
            
            for selector in nav_selectors:
                parent = await element.evaluate(f'(el) => el.closest("{selector}")')
                if parent:
                    return True
            
            return False
            
        except:
            return False