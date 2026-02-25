"""
HTML and DOM preprocessing utilities.
"""

from typing import Dict, Any, List
from bs4 import BeautifulSoup


class HTMLPreprocessor:
    """
    Preprocesses HTML for easier consumption by the agent.
    """
    
    def __init__(self, simplify: bool = True):
        self.simplify = simplify
    
    def process(self, html: str) -> Dict[str, Any]:
        """
        Process HTML into structured format.
        
        Args:
            html: Raw HTML string
            
        Returns:
            Dictionary with processed HTML data
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove unwanted tags
        if self.simplify:
            for tag in soup(['script', 'style', 'meta', 'link']):
                tag.decompose()
        
        # Extract text
        text = soup.get_text(separator=' ', strip=True)
        
        # Extract interactive elements
        interactive = self._extract_interactive_elements(soup)
        
        return {
            "cleaned_html": str(soup),
            "text": text,
            "interactive_elements": interactive
        }
    
    def _extract_interactive_elements(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract clickable/interactive elements"""
        elements = []
        
        selectors = ['a', 'button', 'input', 'select', 'textarea']
        
        for tag_name in selectors:
            for idx, elem in enumerate(soup.find_all(tag_name)):
                element_info = {
                    "tag": tag_name,
                    "id": elem.get('id', ''),
                    "class": ' '.join(elem.get('class', [])),
                    "text": elem.get_text(strip=True)[:100],
                    "type": elem.get('type', ''),
                    "name": elem.get('name', ''),
                    "href": elem.get('href', '') if tag_name == 'a' else '',
                }
                elements.append(element_info)
        
        return elements
    
    def simplify_html(self, html: str, max_length: int = 10000) -> str:
        """
        Aggressively simplify HTML to reduce size.
        
        Args:
            html: Raw HTML
            max_length: Maximum length of output
            
        Returns:
            Simplified HTML string
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove all scripts, styles, etc.
        for tag in soup(['script', 'style', 'meta', 'link', 'svg', 'img']):
            tag.decompose()
        
        # Get simplified HTML
        simplified = str(soup)
        
        # Truncate if needed
        if len(simplified) > max_length:
            simplified = simplified[:max_length] + "..."
        
        return simplified
