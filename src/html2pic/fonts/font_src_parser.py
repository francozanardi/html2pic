"""Font source URL parsing."""
from typing import Optional


class FontSrcParser:
    """Parses CSS font src property values."""
    
    def parse(self, src: str) -> Optional[str]:
        """Parse src property and extract the font file path."""
        src = src.strip()
        src_values = [s.strip() for s in src.split(',')]

        for src_value in src_values:
            font_url = self._extract_url(src_value)
            if font_url:
                return font_url
        return None
    
    def _extract_url(self, src_value: str) -> Optional[str]:
        """Extract URL from a src value containing url() and optional format()."""
        src_value = src_value.strip()
        
        url_start = src_value.find('url(')
        if url_start == -1:
            return None

        paren_count = 0
        url_end = -1

        for i in range(url_start + 4, len(src_value)):
            if src_value[i] == '(':
                paren_count += 1
            elif src_value[i] == ')':
                if paren_count == 0:
                    url_end = i
                    break
                paren_count -= 1

        if url_end == -1:
            return None

        url_content = src_value[url_start + 4:url_end].strip()

        if (url_content.startswith('"') and url_content.endswith('"')) or \
           (url_content.startswith("'") and url_content.endswith("'")):
            url_content = url_content[1:-1]

        return url_content
