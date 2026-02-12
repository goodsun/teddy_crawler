"""
Image Extractor - Extract images from web pages
"""

from playwright.async_api import Page
from typing import Dict, List, Any, Optional
from urllib.parse import urljoin, urlparse
import re


class ImageExtractor:
    """Extract images from web pages"""
    
    def __init__(self):
        self.image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp']
        self.exclude_patterns = [
            r'data:image',  # Skip data URLs for now
            r'\.ico$',      # Skip favicons
            r'pixel\.gif',  # Skip tracking pixels
            r'1x1\.',       # Skip 1x1 tracking images
        ]
    
    async def extract_all_images(self, page: Page) -> Dict[str, Any]:
        """Extract all images from page"""
        try:
            result = {
                'images': [],
                'background_images': [],
                'total_count': 0,
                'by_type': {}
            }
            
            current_url = page.url
            
            # Extract regular img tags
            img_elements = await page.query_selector_all('img')
            
            for img in img_elements:
                try:
                    img_data = await self._extract_img_data(img, current_url)
                    if img_data:
                        result['images'].append(img_data)
                
                except Exception as e:
                    print(f"Error extracting img element: {e}")
                    continue
            
            # Extract background images from CSS
            bg_images = await self._extract_background_images(page, current_url)
            result['background_images'] = bg_images
            
            # Calculate totals and categorize
            result['total_count'] = len(result['images']) + len(result['background_images'])
            result['by_type'] = self._categorize_images(result['images'])
            
            return result
            
        except Exception as e:
            print(f"Error extracting images: {e}")
            return {}
    
    async def extract_with_selectors(self, page: Page, selectors: Dict[str, str]) -> Dict[str, Any]:
        """Extract images using custom CSS selectors"""
        result = {}
        current_url = page.url
        
        for key, selector in selectors.items():
            try:
                elements = await page.query_selector_all(selector)
                images = []
                
                for element in elements:
                    # Check if element itself is an image
                    tag_name = await element.evaluate('el => el.tagName.toLowerCase()')
                    
                    if tag_name == 'img':
                        img_data = await self._extract_img_data(element, current_url)
                        if img_data:
                            images.append(img_data)
                    else:
                        # Look for images within element
                        img_children = await element.query_selector_all('img')
                        for img in img_children:
                            img_data = await self._extract_img_data(img, current_url)
                            if img_data:
                                images.append(img_data)
                        
                        # Check for background images
                        bg_img = await self._get_background_image(element, current_url)
                        if bg_img:
                            images.append(bg_img)
                
                if images:
                    result[key] = images
                    
            except Exception as e:
                print(f"Error with selector '{selector}': {e}")
                continue
        
        return result
    
    async def extract_by_size(self, page: Page, min_width: int = 100, min_height: int = 100) -> List[Dict[str, Any]]:
        """Extract images above minimum size threshold"""
        try:
            result = []
            current_url = page.url
            
            img_elements = await page.query_selector_all('img')
            
            for img in img_elements:
                try:
                    # Get image dimensions
                    dimensions = await img.bounding_box()
                    if not dimensions:
                        continue
                    
                    if dimensions['width'] >= min_width and dimensions['height'] >= min_height:
                        img_data = await self._extract_img_data(img, current_url)
                        if img_data:
                            img_data['dimensions'] = {
                                'width': dimensions['width'],
                                'height': dimensions['height']
                            }
                            result.append(img_data)
                
                except Exception as e:
                    print(f"Error checking image size: {e}")
                    continue
            
            return result
            
        except Exception as e:
            print(f"Error extracting images by size: {e}")
            return []
    
    async def _extract_img_data(self, img_element, current_url: str) -> Optional[Dict[str, Any]]:
        """Extract data from img element"""
        try:
            src = await img_element.get_attribute('src')
            if not src or self._should_exclude(src):
                return None
            
            # Resolve relative URLs
            absolute_url = urljoin(current_url, src)
            
            img_data = {
                'url': absolute_url,
                'alt': await img_element.get_attribute('alt') or '',
                'title': await img_element.get_attribute('title') or '',
                'original_src': src,
                'type': 'img'
            }
            
            # Try to get additional attributes
            width = await img_element.get_attribute('width')
            height = await img_element.get_attribute('height')
            
            if width or height:
                img_data['attributes'] = {}
                if width:
                    img_data['attributes']['width'] = width
                if height:
                    img_data['attributes']['height'] = height
            
            # Get srcset if available
            srcset = await img_element.get_attribute('srcset')
            if srcset:
                img_data['srcset'] = srcset
            
            return img_data
            
        except Exception:
            return None
    
    async def _extract_background_images(self, page: Page, current_url: str) -> List[Dict[str, Any]]:
        """Extract CSS background images"""
        try:
            # JavaScript to find elements with background images
            bg_images = await page.evaluate('''
                () => {
                    const elements = document.querySelectorAll('*');
                    const bgImages = [];
                    
                    elements.forEach(el => {
                        const style = window.getComputedStyle(el);
                        const bgImage = style.backgroundImage;
                        
                        if (bgImage && bgImage !== 'none' && bgImage.includes('url(')) {
                            const match = bgImage.match(/url\\(['"]?([^'"]+)['"]?\\)/);
                            if (match) {
                                bgImages.push({
                                    url: match[1],
                                    element: {
                                        tagName: el.tagName.toLowerCase(),
                                        className: el.className,
                                        id: el.id
                                    }
                                });
                            }
                        }
                    });
                    
                    return bgImages;
                }
            ''')
            
            result = []
            for bg_img in bg_images:
                if not self._should_exclude(bg_img['url']):
                    bg_img['url'] = urljoin(current_url, bg_img['url'])
                    bg_img['type'] = 'background'
                    result.append(bg_img)
            
            return result
            
        except Exception as e:
            print(f"Error extracting background images: {e}")
            return []
    
    async def _get_background_image(self, element, current_url: str) -> Optional[Dict[str, Any]]:
        """Get background image from specific element"""
        try:
            bg_image = await element.evaluate('''
                el => {
                    const style = window.getComputedStyle(el);
                    const bgImage = style.backgroundImage;
                    if (bgImage && bgImage !== 'none' && bgImage.includes('url(')) {
                        const match = bgImage.match(/url\\(['"]?([^'"]+)['"]?\\)/);
                        return match ? match[1] : null;
                    }
                    return null;
                }
            ''')
            
            if bg_image and not self._should_exclude(bg_image):
                return {
                    'url': urljoin(current_url, bg_image),
                    'type': 'background',
                    'original_src': bg_image
                }
            
            return None
            
        except Exception:
            return None
    
    def _should_exclude(self, src: str) -> bool:
        """Check if image should be excluded"""
        if not src or src.strip() == '':
            return True
        
        for pattern in self.exclude_patterns:
            if re.search(pattern, src, re.IGNORECASE):
                return True
        
        return False
    
    def _categorize_images(self, images: List[Dict]) -> Dict[str, int]:
        """Categorize images by file extension"""
        categories = {}
        
        for img in images:
            try:
                url = img.get('url', '')
                parsed = urlparse(url)
                path = parsed.path.lower()
                
                for ext in self.image_extensions:
                    if path.endswith(ext):
                        ext_clean = ext.replace('.', '')
                        categories[ext_clean] = categories.get(ext_clean, 0) + 1
                        break
                else:
                    categories['unknown'] = categories.get('unknown', 0) + 1
                    
            except Exception:
                categories['unknown'] = categories.get('unknown', 0) + 1
        
        return categories