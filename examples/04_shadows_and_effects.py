"""
Advanced Effects: Shadows and Positioning
"""

import sys
import os

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from html2pic import Html2Pic

html = '''
<div class="showcase">
    <h1 class="main-title">Advanced Effects</h1>
    <div class="feature-box">
        <h2>Shadows & Styling</h2>
        <p>This example demonstrates text shadows, box shadows, and advanced styling.</p>
    </div>
    <div class="floating-badge">NEW!</div>
</div>
'''

css = '''
.showcase {
    width: 500px;
    background-color: #667eea;
    padding: 30px;
    border-radius: 15px;
    position: relative;
}

.main-title {
    color: white;
    font-size: 36px;
    font-weight: bold;
    text-align: center;
    margin-bottom: 20px;
    text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5);
}

.feature-box {
    background-color: white;
    padding: 25px;
    border-radius: 12px;
    box-shadow: 0 8px 16px rgba(0, 0, 0, 0.4);
    margin-top: 20px;
}

.feature-box h2 {
    color: #2c3e50;
    margin-bottom: 10px;
    text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.4);
}

.feature-box p {
    color: #7f8c8d;
    line-height: 1.5;
}

.floating-badge {
    position: absolute;
    top: -5px;
    left: 20px;
    background-color: #e74c3c;
    color: white;
    padding: 8px 16px;
    border-radius: 20px;
    font-weight: bold;
    font-size: 14px;
    box-shadow: 0 4px 8px rgba(231, 76, 60, 0.4);
    text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.4);
}
'''

if __name__ == "__main__":
    renderer = Html2Pic(html, css)
    image = renderer.render()
    image.save("04_shadows_and_effects_output.png")
    
    print("Shadows and effects example rendered successfully!")
    print("Output saved to '04_shadows_and_effects_output.png'")
