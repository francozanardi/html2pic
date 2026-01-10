"""
Background Images Example - Demonstrates background-image support
"""

import sys
import os

# Fix encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from html2pic import Html2Pic

html = '''
<div class="container">
    <div class="bg-demo cover-demo">
        <h3>Background Cover</h3>
        <p>Image scaled to cover entire area</p>
    </div>
    <div class="bg-demo contain-demo">
        <h3>Background Contain</h3>
        <p>Image scaled to fit within area</p>
    </div>
    <div class="bg-demo tile-demo">
        <h3>Background Tile</h3>
        <p>Image repeated at natural size</p>
    </div>
</div>
'''

css = '''
.container {
    display: flex;
    flex-direction: column;
    gap: 20px;
    padding: 30px;
    background-color: #f5f5f5;
}

.bg-demo {
    width: 400px;
    height: 120px;
    padding: 20px;
    border-radius: 8px;
    color: white;
    text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.7);
}

.cover-demo {
    background-color: #3498db;
    background-image: url('background.webp');
    background-size: cover;
}

.contain-demo {
    background-color: #2ecc71;
    background-image: url('background.webp');
    background-size: contain;
}

.tile-demo {
    background-color: #e74c3c;
    background-image: url('background.webp');
    background-size: auto;
}

.bg-demo h3 {
    margin: 0 0 8px 0;
    font-size: 20px;
}

.bg-demo p {
    margin: 0;
    font-size: 14px;
    opacity: 0.9;
}
'''

if __name__ == "__main__":
    renderer = Html2Pic(html, css)
    image = renderer.render()
    image.save("05_background_images_output.png")
    
    print("✅ Background images example rendered successfully!")
    print("📸 Check '05_background_images_output.png' for the result")
    print("ℹ️  Background images are commented out - uncomment and add real image paths to test")