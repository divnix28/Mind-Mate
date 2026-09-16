import os
import re

files = [
    r'c:\Users\ASUS\Downloads\MINDMATE\templates\index.html',
    r'c:\Users\ASUS\Downloads\MINDMATE\templates\MINDMATE.html',
    r'c:\Users\ASUS\Downloads\MINDMATE\templates\counselor_login.html',
    r'c:\Users\ASUS\Downloads\MINDMATE\templates\counselor_dashboard.html',
]

font_link = '<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">\n'

new_glass = """        .glass-panel {
            background: rgba(15, 23, 42, 0.45);
            backdrop-filter: blur(24px);
            -webkit-backdrop-filter: blur(24px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3), inset 0 0 0 1px rgba(255, 255, 255, 0.05);
        }"""

for file_path in files:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Inject font link if not present
    if 'fonts.googleapis.com/css2?family=Outfit' not in content:
        content = content.replace('</title>', '</title>\n    ' + font_link)
        
    # Inject fontFamily into tailwind.config
    if 'fontFamily: {' not in content:
        content = content.replace('theme: {', "theme: {\n                fontFamily: { sans: ['Outfit', 'sans-serif'] },")

    # Replace old glass panel
    content = re.sub(r'\.glass-panel\s*\{[^}]*\}', new_glass, content, flags=re.MULTILINE)

    # Enhance button micro-interactions
    content = content.replace('transform hover:-translate-y-0.5 active:translate-y-0', 'transform hover:-translate-y-1 hover:scale-105 active:scale-95 transition-all duration-300')
    content = content.replace('hover:bg-blue-500 text-white font-medium', 'hover:bg-blue-500 text-white font-medium hover:shadow-[0_0_20px_rgba(59,130,246,0.6)] transform hover:-translate-y-1 hover:scale-105 active:scale-95 transition-all duration-300')
    content = content.replace('hover:bg-blue-500 text-white font-semibold', 'hover:bg-blue-500 text-white font-semibold hover:shadow-[0_0_20px_rgba(59,130,246,0.6)] transform hover:-translate-y-1 hover:scale-105 active:scale-95 transition-all duration-300')
    content = content.replace('hover:bg-blue-100', 'hover:bg-blue-500/20 hover:scale-105 active:scale-95 transition-all duration-300')
    
    # Update tabs to scale on click
    content = content.replace('tab-btn px-4 py-1.5', 'tab-btn px-4 py-1.5 hover:scale-105 active:scale-95')

    # Focus rings on inputs
    content = content.replace('focus:ring-1 focus:ring-blue-500', 'focus:ring-2 focus:ring-blue-500/50')
    content = content.replace('focus:ring-1 focus:ring-blue-400', 'focus:ring-2 focus:ring-blue-400/50')

    # Card hover scaling
    content = content.replace('animate-float', 'animate-float hover:scale-105 transition-transform duration-300')
    content = content.replace('animate-float-delayed', 'animate-float-delayed hover:scale-105 transition-transform duration-300')
    content = content.replace('hover:bg-slate-800/40 transition-all duration-300 rounded-xl', 'hover:bg-slate-800/60 hover:scale-[1.02] active:scale-[0.99] transition-all duration-300 rounded-xl')

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

print("UI enhancements applied successfully.")
