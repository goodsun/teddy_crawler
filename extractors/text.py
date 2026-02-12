"""
Text Extractor - Extract text content from web pages
"""

from playwright.async_api import Page
from typing import Dict, List, Any, Optional
import re


class TextExtractor:
    """Extract text content from web pages"""
    
    def __init__(self):
        self.default_selectors = {
            'title': ['title', 'h1', '[data-testid*="title"]', '.title'],
            'content': ['main', 'article', '.content', '.post', '#content'],
            'paragraphs': ['p'],
            'headings': ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']
        }
    
    async def extract_all_text(self, page: Page) -> Dict[str, Any]:
        """Extract all text content from page"""
        try:
            result = {
                'title': await self._extract_title(page),
                'content': await self._extract_main_content(page),
                'paragraphs': await self._extract_paragraphs(page),
                'headings': await self._extract_headings(page),
                'meta_description': await self._extract_meta_description(page)
            }
            
            # Remove empty values
            return {k: v for k, v in result.items() if v}
            
        except Exception as e:
            print(f"Error extracting text: {e}")
            return {}
    
    async def extract_with_selectors(self, page: Page, selectors: Dict[str, str]) -> Dict[str, Any]:
        """Extract text using custom CSS selectors"""
        result = {}
        
        for key, selector in selectors.items():
            try:
                elements = await page.query_selector_all(selector)
                if elements:
                    texts = []
                    for element in elements:
                        text = await element.inner_text()
                        if text and text.strip():
                            texts.append(text.strip())
                    
                    if texts:
                        result[key] = texts if len(texts) > 1 else texts[0]
                        
            except Exception as e:
                print(f"Error with selector '{selector}': {e}")
                continue
        
        return result
    
    async def _extract_title(self, page: Page) -> Optional[str]:
        """Extract page title"""
        try:
            # Try multiple selectors in order
            for selector in self.default_selectors['title']:
                element = await page.query_selector(selector)
                if element:
                    text = await element.inner_text()
                    if text and text.strip():
                        return text.strip()
            
            # Fallback to page title
            return await page.title()
            
        except Exception:
            return None
    
    async def _extract_main_content(self, page: Page) -> Optional[str]:
        """Extract main content"""
        try:
            for selector in self.default_selectors['content']:
                element = await page.query_selector(selector)
                if element:
                    text = await element.inner_text()
                    if text and len(text.strip()) > 100:  # Minimum content length
                        return self._clean_text(text)
            
            # Fallback to body text
            body_text = await page.evaluate('() => document.body.innerText')
            return self._clean_text(body_text) if body_text else None
            
        except Exception:
            return None
    
    async def _extract_paragraphs(self, page: Page) -> List[str]:
        """Extract all paragraphs"""
        try:
            elements = await page.query_selector_all('p')
            paragraphs = []
            
            for element in elements:
                text = await element.inner_text()
                if text and text.strip() and len(text.strip()) > 20:
                    paragraphs.append(text.strip())
            
            return paragraphs
            
        except Exception:
            return []
    
    async def _extract_headings(self, page: Page) -> Dict[str, List[str]]:
        """Extract all headings by level"""
        try:
            headings = {}
            
            for level in range(1, 7):  # h1-h6
                elements = await page.query_selector_all(f'h{level}')
                texts = []
                
                for element in elements:
                    text = await element.inner_text()
                    if text and text.strip():
                        texts.append(text.strip())
                
                if texts:
                    headings[f'h{level}'] = texts
            
            return headings
            
        except Exception:
            return {}
    
    async def _extract_meta_description(self, page: Page) -> Optional[str]:
        """Extract meta description"""
        try:
            meta = await page.query_selector('meta[name="description"]')
            if meta:
                content = await meta.get_attribute('content')
                return content.strip() if content else None
            return None
            
        except Exception:
            return None
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text"""
        if not text:
            return ""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        return text