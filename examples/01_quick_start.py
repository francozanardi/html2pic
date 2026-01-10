"""
Quick Start Example - Basic card layout
"""

import sys
import os

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from html2pic import Html2Pic

html = '''
<div class="card">
    <h1>Hello, html2pic!</h1>
    <p>Transform HTML to images with ease</p>
</div>
'''

css = '''
.card {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 40px;
    background-image: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 20px;
    width: 400px;
}

h1 {
    color: white;
    font-size: 32px;
    font-weight: bold;
    margin: 0 0 12px 0;
}

p {
    color: rgba(255,255,255,0.9);
    font-size: 18px;
    margin: 0;
}
'''

if __name__ == "__main__":
    renderer = Html2Pic(html, css)
    image = renderer.render()
    image.save("01_quick_start_output.png")
    
    print("Quick start example rendered successfully!")
    print("Output saved to '01_quick_start_output.png'")
