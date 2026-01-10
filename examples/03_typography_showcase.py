"""
Typography Showcase Example
"""

import sys
import os

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from html2pic import Html2Pic

html = '''
<div class="typography">
    <h1>Elegant Typography</h1>
    <p class="lead">Beautiful text rendering with custom fonts</p>
    <p class="body">This paragraph demonstrates how html2pic handles various text styles seamlessly.</p>
</div>
'''

css = '''
.typography {
    padding: 40px;
    background-image: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    text-align: center;
}

h1 {
    font-size: 42px;
    font-weight: bold;
    margin: 0 0 16px 0;
}

.lead {
    font-size: 20px;
    margin: 0 0 24px 0;
}

.body {
    font-size: 16px;
    line-height: 1.6;
    max-width: 500px;
    margin: 0 auto;
}
'''

if __name__ == "__main__":
    renderer = Html2Pic(html, css)
    image = renderer.render()
    image.save("03_typography_showcase_output.png")
    
    print("Typography showcase example rendered successfully!")
    print("Output saved to '03_typography_showcase_output.png'")
