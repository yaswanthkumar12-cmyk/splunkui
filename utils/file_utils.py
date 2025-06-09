import os
import zipfile
import re

def create_splunk_app(path, app_name, index_name, sources=None):
    import os

    os.makedirs(path, exist_ok=True)

    # Create core folders
    folders = ['default', 'local', 'metadata', 'bin']
    for folder in folders:
        os.makedirs(os.path.join(path, folder), exist_ok=True)

    # README
    with open(os.path.join(path, 'README.txt'), 'w') as f:
        f.write(f"App: {app_name}\nIndex: {index_name}\n")

    # Sample script in /bin
    with open(os.path.join(path, 'bin', 'sample_script.py'), 'w') as f:
        f.write("""#!/usr/bin/env python3
print("This is a placeholder Splunk script.")
""")

    # default/app.conf
    with open(os.path.join(path, 'default', 'app.conf'), 'w') as f:
        f.write(f"""[install]
state = enabled

[ui]
is_visible = true
label = {app_name}

[launcher]
author = Auto Generator
description = Splunk app created via UI
version = 1.0.0
""")

    # default/inputs.conf - create entries per source
    with open(os.path.join(path, 'default', 'inputs.conf'), 'w') as f:
        if sources:
            for source in sources:
                source_name = source['name']
                log_path = source['logpath'].replace('\\','\\\\').replace('/','\\\\')
                sourcetype = f"{app_name}_{source_name}".replace(" ", "_").lower()
                f.write(f"""#app name={app_name}

[monitor://{log_path}]
disabled = false
index = {index_name}
sourcetype = {sourcetype}
source_name = {source_name}

""")
        else:
            # fallback if no sources provided
            f.write(f"""[monitor:///var/log/{app_name}]
disabled = false
index = {index_name}
sourcetype = {app_name}_log
""")

    # default/props.conf - general for app_name_log
    with open(os.path.join(path, 'default', 'props.conf'), 'w') as f:
        f.write(f"""[{app_name}_log]
TIME_FORMAT = %Y-%m-%d %H:%M:%S
TIME_PREFIX = ^
MAX_EVENTS = 1000
SHOULD_LINEMERGE = false
TRANSFORMS-set = setnull,setparsing
""")

    # default/transforms.conf
    with open(os.path.join(path, 'default', 'transforms.conf'), 'w') as f:
        f.write("""[setnull]
REGEX = .
DEST_KEY = queue
FORMAT = nullQueue

[setparsing]
REGEX = .
DEST_KEY = queue
FORMAT = indexQueue
""")

    # default/eventtypes.conf - example with app_name_log error search
    with open(os.path.join(path, 'default', 'eventtypes.conf'), 'w') as f:
        f.write(f"""[{app_name}_errors]
search = sourcetype={app_name}_log error OR fail OR exception
""")

    # default/tags.conf
    with open(os.path.join(path, 'default', 'tags.conf'), 'w') as f:
        f.write(f"""[{app_name}_log]
eventtype={app_name}_errors = informative
""")

    # default/sourcetypes.conf
    with open(os.path.join(path, 'default', 'sourcetypes.conf'), 'w') as f:
        f.write(f"""[{app_name}_log]
category = Custom
description = Log sourcetype for {app_name}
pulldown_type = true
""")

    # metadata/default.meta
    with open(os.path.join(path, 'metadata', 'default.meta'), 'w') as f:
        f.write("""[]
access = read : [ * ], write : [ admin ]
export = system
""")

def extract_zip(file_storage, destination):
    with zipfile.ZipFile(file_storage, 'r') as zip_ref:
        zip_ref.extractall(destination)

def rezip_app(source_dir, zip_path):
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(source_dir):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, source_dir)
                zipf.write(full_path, rel_path)

def get_config_files(app_path):
    config_files = []
    for root, _, files in os.walk(app_path):
        for file in files:
            rel_path = os.path.relpath(os.path.join(root, file), app_path)
            config_files.append(rel_path)
    return config_files

def save_file(path, content):
    # Clean leading/trailing whitespace
    content = content.strip()
    
    # Normalize lines
    lines = [line.strip() for line in content.splitlines() if line.strip()]

    # Ensure blank lines before every [monitor://...] stanza
    updated_lines = []
    for i, line in enumerate(lines):
        if line.startswith('[monitor:///'):
            # Insert blank line before if previous line is not already blank
            if i > 0 and updated_lines[-1] != '':
                updated_lines.append('')
        updated_lines.append(line)

    # Join and write to file
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(updated_lines) + '\n')


def is_valid_splunk_conf(content):
    lines = content.strip().splitlines()
    current_section = None
    for i, line in enumerate(lines, 1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('[') and line.endswith(']'):
            current_section = line
        elif '=' in line:
            if not current_section:
                return False, f"Line {i}: Key-value pair found outside any section."
        else:
            return False, f"Line {i}: Invalid line format: '{line}'"
    return True, "Valid Splunk configuration."
