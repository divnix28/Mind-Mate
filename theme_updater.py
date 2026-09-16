import os
import re

file_path = r'c:\Users\ASUS\Downloads\MINDMATE\templates\MINDMATE.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add styles and tailwind config for dark theme + animations
head_end = content.find('</head>')
styles_to_inject = """
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    animation: {
                        'gradient': 'gradient 15s ease infinite',
                        'glass-pulse': 'glassPulse 3s ease-in-out infinite',
                    },
                    keyframes: {
                        gradient: {
                            '0%, 100%': { 'background-position': '0% 50%' },
                            '50%': { 'background-position': '100% 50%' },
                        },
                        glassPulse: {
                            '0%, 100%': { 'box-shadow': '0 0 15px rgba(59, 130, 246, 0.1)', 'border-color': 'rgba(59, 130, 246, 0.2)' },
                            '50%': { 'box-shadow': '0 0 25px rgba(59, 130, 246, 0.3)', 'border-color': 'rgba(59, 130, 246, 0.4)' },
                        }
                    }
                }
            }
        }
    </script>
    <style>
        .glass-panel {
            background: rgba(15, 23, 42, 0.65);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid rgba(59, 130, 246, 0.2);
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        }
        .animated-bg {
            background: linear-gradient(-45deg, #020617, #0f172a, #1e3a8a, #0f172a);
            background-size: 400% 400%;
            animation: gradient 15s ease infinite;
        }
    </style>
"""

# Strip existing tailwind config script if any
content = re.sub(r'<script>\s*tailwind\.config = \{.*?</script>', '', content, flags=re.DOTALL)
content = content.replace('</head>', styles_to_inject + '\n</head>')

# Basic replacements for body
content = content.replace(
    '<body\n    class="bg-white text-slate-900', 
    '<body\n    class="animated-bg text-slate-100'
)
content = content.replace('selection:bg-emerald-500', 'selection:bg-blue-500')
content = content.replace('selection:text-slate-900', 'selection:text-white')

# Broad replacements
replacements = {
    'bg-white/80': 'glass-panel',
    'bg-white': 'glass-panel',
    'bg-slate-100': 'bg-slate-800/60',
    'bg-slate-50': 'bg-slate-800/40',
    'text-slate-900': 'text-slate-100',
    'text-slate-800': 'text-slate-200',
    'text-slate-700': 'text-slate-300',
    'text-slate-600': 'text-slate-400',
    'border-slate-200': 'border-slate-700/50',
    'border-slate-300': 'border-slate-600/50',
    'emerald': 'blue',
    'green': 'indigo'
}

for old, new in replacements.items():
    content = content.replace(old, new)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Theme updated successfully.")
