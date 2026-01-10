"""
Quick Start Example - Basic card layout from README
"""

import sys
import os

# Fix encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from html2pic import Html2Pic

# Your HTML content
html = '''
<div class="card">
    <h1>Hello, World!</h1>
    <p class="subtitle">Generated with html2pic</p>
</div>
'''

# Your CSS styles
css = '''
.card {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 30px;
    background-color: #f0f8ff;
    border-radius: 15px;
    width: 300px;
}

h1 {
    color: #2c3e50;
    font-size: 28px;
    margin: 0 0 10px 0;
}

.subtitle {
    color: #7f8c8d;
    font-size: 16px;
    margin: 0;
}
'''

if __name__ == "__main__":
    # Create and render
    renderer = Html2Pic(html, css)
    image = renderer.render()
    image.save("01_quick_start_output.png")
    
    print("✅ Quick start example rendered successfully!")
    print("📸 Check '01_quick_start_output.png' for the result")