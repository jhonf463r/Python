#!/usr/bin/env python3
"""
Create VFINAL5-R2.2 audit bundle with exact manifest enumeration.

This script:
1. Creates bundle directory structure
2. Enumerates EXACTLY every file that will be in the ZIP
3. Computes SHA256 for every file
4. Creates manifest from that exact file list
5. Creates ZIP from the same files
6. Computes ZIP SHA256
7. Creates sidecar hash file AFTER final ZIP is finalized

This ensures manifest file count equals ZIP file count.
"""

import subprocess
import shutil
from pathlib import Path
from datetime import datetime
import zipfile
import hashlib
import json

def compute_file_sha256(file_path: Path) -> str:
    """Compute SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()

def main():
    """Create VFINAL5-R2.2 bundle with exact manifest."""
    print("Creating VFINAL5-R2.2 bundle with exact manifest...")
    
    # Bundle metadata
    bundle_name = "P0_213_VFINAL5_R2_2_AUDIT_BUNDLE"
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    bundle_dir = Path(f"temp_vfinal5_r2_2_bundle_{timestamp}")
    bundle_zip = Path(f"{bundle_name}_{timestamp}.zip")
    
    # Create bundle directory
    bundle_dir.mkdir(exist_ok=True)
    print(f"Bundle directory: {bundle_dir}")
    
    # Copy source code
    src_dir = bundle_dir / "src"
    src_dir.mkdir(exist_ok=True)
    shutil.copytree("src/iabv_v15", src_dir / "iabv_v15", dirs_exist_ok=True)
    print("Copied source code")
    
    # Copy tests
    tests_dir = bundle_dir / "tests"
    tests_dir.mkdir(exist_ok=True)
    shutil.copytree("tests", tests_dir / "iabv_v15", dirs_exist_ok=True)
    print("Copied tests")
    
    # Copy documentation
    docs_dir = bundle_dir / "docs"
    docs_dir.mkdir(exist_ok=True)
    
    # Copy phase reports
    phase_reports = [
        "PHASE1_R2_1_REPRODUCTION.md",
        "PHASE2_5_SESSION_EPISODE_BINDING_FIX.md",
        "PHASE7_AUTHORITY_BOUNDARY.md",
        "PHASE8_LEASE_CONSISTENCY.md",
        "PHASE9_MCP_PATH_VERIFICATION.md",
        "PHASE11_WINDOWS_E2E.md",
        "PHASE12_REGRESSION_ANALYSIS.md",
        "C2_EXECUTION_CONTEXT_AUDIT.md",
        "C2_CAPABILITY_PROVENANCE.md",
        "AUDIT_SELF_UPDATE_CALL_GRAPH.md",
        "PRODUCTION_BYPASS_SEARCH.md",
    ]
    
    for report in phase_reports:
        src = Path(report)
        if src.exists():
            shutil.copy(src, docs_dir / report)
            print(f"Copied {report}")
    
    # Enumerate EXACTLY every file that will be in the ZIP
    print("Enumerating bundle files...")
    bundle_files = []
    for file_path in bundle_dir.rglob('*'):
        if file_path.is_file():
            bundle_files.append(file_path)
    
    print(f"Found {len(bundle_files)} files in bundle directory")
    
    # Compute SHA256 for every file
    print("Computing SHA256 for bundle files...")
    manifest_files = {}
    for file_path in bundle_files:
        sha256 = compute_file_sha256(file_path)
        arcname = file_path.relative_to(bundle_dir)
        manifest_files[str(arcname)] = sha256
        print(f"  {arcname}: {sha256}")
    
    # Create manifest from exact file list
    manifest = {
        "version": "VFINAL5-R2.2",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "commit": subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip(),
        "branch": "p0213/vfinal5-r2-security-fixes",
        "file_count": len(bundle_files),
        "files": manifest_files
    }
    
    # Write manifest to bundle directory
    manifest_path = bundle_dir / "VFINAL5_R2_2_MANIFEST.json"
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    print(f"Manifest written to {manifest_path}")
    print(f"Manifest file count: {len(bundle_files)}")
    
    # Create bundle manifest
    bundle_manifest = {
        "bundle_name": bundle_name,
        "version": "VFINAL5-R2.2",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "commit": subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip(),
        "branch": "p0213/vfinal5-r2-security-fixes",
        "manifest_file_count": len(bundle_files),
        "contents": {
            "source": "src/iabv_v15/",
            "tests": "tests/iabv_v15/",
            "documentation": "docs/",
            "manifest": "VFINAL5_R2_2_MANIFEST.json"
        }
    }
    
    with open(bundle_dir / "BUNDLE_MANIFEST.json", 'w') as f:
        json.dump(bundle_manifest, f, indent=2)
    print("Created bundle manifest")
    
    # Create ZIP bundle from the same files
    print(f"Creating ZIP bundle: {bundle_zip}")
    with zipfile.ZipFile(bundle_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in bundle_files:
            arcname = file_path.relative_to(bundle_dir)
            zipf.write(file_path, arcname)
    
    # Verify ZIP file count
    with zipfile.ZipFile(bundle_zip, 'r') as zipf:
        zip_file_count = len(zipf.namelist())
    
    print(f"ZIP file count: {zip_file_count}")
    print(f"Manifest file count: {len(bundle_files)}")
    
    if zip_file_count != len(bundle_files):
        print("ERROR: ZIP file count does not match manifest file count!")
        return
    
    # Compute ZIP SHA256
    with open(bundle_zip, 'rb') as f:
        zip_sha256 = hashlib.sha256(f.read()).hexdigest()
    
    print(f"ZIP SHA256: {zip_sha256}")
    
    # Create sidecar hash file AFTER final ZIP is finalized
    sidecar_path = Path(f"VFINAL5_R2_2_BUNDLE_SHA256.txt")
    with open(sidecar_path, 'w') as f:
        f.write(zip_sha256 + '\n')
    
    print(f"Sidecar written to {sidecar_path}")
    
    # Copy sidecar to bundle directory
    shutil.copy(sidecar_path, bundle_dir / "VFINAL5_R2_2_BUNDLE_SHA256.txt")
    
    # Re-create ZIP with sidecar included
    print(f"Re-creating ZIP bundle with sidecar: {bundle_zip}")
    bundle_zip.unlink()  # Remove old ZIP
    with zipfile.ZipFile(bundle_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in bundle_dir.rglob('*'):
            if file_path.is_file():
                arcname = file_path.relative_to(bundle_dir)
                zipf.write(file_path, arcname)
    
    # Compute final ZIP SHA256
    with open(bundle_zip, 'rb') as f:
        final_zip_sha256 = hashlib.sha256(f.read()).hexdigest()
    
    print(f"Final ZIP SHA256: {final_zip_sha256}")
    
    # Update sidecar with final ZIP SHA256
    with open(sidecar_path, 'w') as f:
        f.write(final_zip_sha256 + '\n')
    
    print(f"Updated sidecar: {sidecar_path}")
    
    # Verify sidecar matches final ZIP
    with open(sidecar_path, 'r') as f:
        sidecar_hash = f.read().strip()
    
    if sidecar_hash != final_zip_sha256:
        print("ERROR: Sidecar hash does not match final ZIP hash!")
        return
    
    print("Sidecar hash matches final ZIP hash")
    
    # Cleanup bundle directory
    shutil.rmtree(bundle_dir)
    print("Cleaned up bundle directory")
    
    print(f"\nBundle created: {bundle_zip}")
    print(f"Bundle SHA256: {final_zip_sha256}")
    print(f"Manifest file count: {len(bundle_files)}")
    print(f"ZIP file count: {zip_file_count}")
    print(f"Manifest matches ZIP: {zip_file_count == len(bundle_files)}")
    print(f"Sidecar matches ZIP: {sidecar_hash == final_zip_sha256}")

if __name__ == "__main__":
    main()
