import os
import re

def check_mojibake(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Look for common Mojibake pattern: ? followed by Korean-like bytes that were incorrectly decoded
            # ?[숈|?쒖|?숈] etc.
            # A more general pattern: '?' followed by common mojibake characters
            mojibake_pattern = re.compile(r'\?[숈쒖숈옄쑚]') 
            matches = mojibake_pattern.findall(content)
            if matches:
                return f"Found potential Mojibake in {file_path}: {set(matches)}"
    except Exception as e:
        return f"Error reading {file_path}: {e}"
    return None

pages_dir = r"c:\Users\임현수\Downloads\polio for real\polio for real\frontend\src\pages"
results = []
for root, dirs, files in os.walk(pages_dir):
    for file in files:
        if file.endswith('.tsx'):
            result = check_mojibake(os.path.join(root, file))
            if result:
                results.append(result)

if not results:
    print("No Mojibake found in .tsx files.")
else:
    for res in results:
        print(res)
