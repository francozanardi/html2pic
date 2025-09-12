"""
Flexbox Card Layout Example from README
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
<div class="user-card">
    <div class="avatar"></div>
    <div class="user-info">
        <h2>Alex Doe</h2>
        <p>@alexdoe</p>
    </div>
</div>
'''

css = '''
.user-card {
    display: flex;
    align-items: center;
    gap: 15px;
    padding: 20px;
    background-color: white;
    border-radius: 12px;
    border: 1px solid #e1e8ed;
}

.avatar {
    width: 60px;
    height: 60px;
    background-image: url('background.webp');
    border-radius: 50%;
}

.user-info h2 {
    margin: 0 0 4px 0;
    font-size: 18px;
    color: #14171a;
}

.user-info p {
    margin: 0;
    color: #657786;
    font-size: 14px;
}
'''

if __name__ == "__main__":
    renderer = Html2Pic(html, css)
    image = renderer.render()
    image.save("02_flexbox_card_output.png")
    
    print("✅ Flexbox card example rendered successfully!")
    print("📸 Check '02_flexbox_card_output.png' for the result")
    
    renderer.print_warnings()