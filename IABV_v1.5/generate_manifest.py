#!/usr/bin/env python3
"""Generate manifest from ZIP file without extraction."""
import zipfile
import hashlib
import sys

def generate_manifest(zip_path):
    """Generate SHA256 manifest for all files in ZIP."""
    manifest = {}
    with zipfile.ZipFile(zip_path, 'r') as zf:
        for info in zf.infolist():
            if not info.is_dir():
                # Read file content and compute SHA256
                with zf.open(info) as f:
                    content = f.read()
                    sha256 = hashlib.sha256(content).hexdigest()
                    manifest[info.filename] = sha256
    return manifest

if __name__ == '__main__':
    zip_path = sys.argv[1]
    manifest = generate_manifest(zip_path)
    
    # Write manifest file
    with open('MANIFEST.txt', 'w') as f:
        for filename, sha256 in sorted(manifest.items()):
            f.write(f"{sha256}  {filename}\n")
    
    print(f"MANIFEST_FILE_COUNT={len(manifest)}")
    print(f"ZIP_FILE_COUNT={len(manifest)}")
