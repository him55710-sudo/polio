import os
import re

project_root = r"c:\Users\임현수\Downloads\unifoli for real\unifoli for real"

# Patterns in order of specificity
replacements = [
    # Schema versions
    (re.compile(r'unifoli\.raw_pdf\.v1'), "unifoli.raw_pdf.v1"),
    (re.compile(r'unifoli\.neis\.normalized\.v1'), "unifoli.neis.normalized.v1"),
    (re.compile(r'unifoli\.masked_pdf\.v1'), "unifoli.masked_pdf.v1"),
    
    # Package names and variables (catch CamelCase and snake_case)
    (re.compile(r'unifoli_api'), "unifoli_api"),
    (re.compile(r'unifoli_ingest'), "unifoli_ingest"),
    (re.compile(r'unifoli_render'), "unifoli_render"),
    (re.compile(r'unifoli_worker'), "unifoli_worker"),
    (re.compile(r'unifoli_domain'), "unifoli_domain"),
    (re.compile(r'unifoli_shared'), "unifoli_shared"),
    (re.compile(r'unifoli_parsers'), "unifoli_parsers"),
    (re.compile(r'unifoli_prompts'), "unifoli_prompts"),
    (re.compile(r'unifoli_backend'), "unifoli_backend"),
    (re.compile(r'unifoli-monorepo'), "unifoli-monorepo"),
    
    # Generic branding
    (re.compile(r'UniFoli'), "UniFoli"),
    (re.compile(r'UNIFOLI'), "UNIFOLI"),
    (re.compile(r'unifoli(?![_-])'), "unifoli"), # only if not followed by _ or - (which are handled above)
]

exclude_dirs = {
    ".git", "__pycache__", ".venv", ".pytest_cache", ".vercel", 
    "node_modules", "dist", "storage", "build", "unifoli_backend.egg-info",
    "artifacts", "brain", ".agents"
}

def process_file(file_path):
    # Only process text files
    if file_path.endswith(('.py', '.md', '.txt', '.json', '.yml', '.yaml', '.ini', 
                           '.ps1', '.sh', '.toml', '.ts', '.tsx', '.html', '.css', '.js')):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception:
            return

        new_content = content
        for pattern, replacement in replacements:
            new_content = pattern.sub(replacement, new_content)

        if new_content != content:
            print(f"Updating {file_path}")
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

for root, dirs, files in os.walk(project_root):
    dirs[:] = [d for d in dirs if d not in exclude_dirs]
    for file in files:
        file_path = os.path.join(root, file)
        process_file(file_path)

print("Final rebranding replacement complete.")
