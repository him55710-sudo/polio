import os
import re

root_dir = r"c:\Users\임현수\Downloads\unifoli for real\unifoli for real\backend"

replacements = [
    (re.compile(r'\bunifoli_api\b'), "unifoli_api"),
    (re.compile(r'\bunifoli_ingest\b'), "unifoli_ingest"),
    (re.compile(r'\bunifoli_render\b'), "unifoli_render"),
    (re.compile(r'\bunifoli_worker\b'), "unifoli_worker"),
    (re.compile(r'\bunifoli_domain\b'), "unifoli_domain"),
    (re.compile(r'\bunifoli_shared\b'), "unifoli_shared"),
    (re.compile(r'\bunifoli_parsers\b'), "unifoli_parsers"),
    (re.compile(r'\bunifoli_prompts\b'), "unifoli_prompts"),
    (re.compile(r'\bunifoli\b'), "unifoli"),
    (re.compile(r'\bUniFoli\b'), "UniFoli"),
    (re.compile(r'\bUNIFOLI\b'), "UNIFOLI"),
    (re.compile(r'\bunifoli\.raw_pdf\.v1\b'), "unifoli.raw_pdf.v1"),
    (re.compile(r'\bunifoli\.neis\.normalized\.v1\b'), "unifoli.neis.normalized.v1"),
    (re.compile(r'\bunifoli\.masked_pdf\.v1\b'), "unifoli.masked_pdf.v1"),
]

exclude_dirs = {".git", "__pycache__", ".venv", ".pytest_cache", ".vercel", "build", "unifoli_backend.egg-info"}

def process_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        # Skip binary files
        return

    new_content = content
    for pattern, replacement in replacements:
        new_content = pattern.sub(replacement, new_content)

    if new_content != content:
        print(f"Updating {file_path}")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

for root, dirs, files in os.walk(root_dir):
    dirs[:] = [d for d in dirs if d not in exclude_dirs]
    for file in files:
        if file.endswith(('.py', '.md', '.txt', '.json', '.yml', '.yaml', '.ini', '.ps1', '.sh', '.toml')):
            file_path = os.path.join(root, file)
            process_file(file_path)

print("Replacement complete.")
