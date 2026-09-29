"""
PCS Import Provenance Inspection
Determines exactly which PortableContextService was imported and from where.
"""

import sys
import os
import inspect
from pathlib import Path

# Add the project to the path
project_root = Path(__file__).parent / "IABV_v1.5"
src_root = project_root / "src"
sys.path.insert(0, str(src_root))
sys.path.insert(0, str(project_root))

print("=" * 80)
print("PCS IMPORT PROVENANCE INSPECTION")
print("=" * 80)
print()

print("ENVIRONMENT:")
print(f"sys.executable: {sys.executable}")
print(f"sys.version: {sys.version}")
print(f"cwd: {Path.cwd()}")
print(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'NOT SET')}")
print()

print("SYS.PATH:")
for i, p in enumerate(sys.path[:10]):
    print(f"  [{i}] {p}")
print()

print("IABV MODULE:")
import iabv_v15
print(f"iabv_v15.__file__: {iabv_v15.__file__}")
print(f"iabv_v15.__version__: {getattr(iabv_v15, '__version__', 'NOT SET')}")
print()

print("PCS MODULE:")
import iabv_v15.services.evolution.portable_context_service as pcs_module
print(f"pcs_module.__file__: {pcs_module.__file__}")
print(f"pcs_module.__name__: {pcs_module.__name__}")
print()

print("PORTABLECONTEXTSERVICE CLASS:")
from iabv_v15.services.evolution.portable_context_service import PortableContextService
print(f"PortableContextService.__module__: {PortableContextService.__module__}")
print(f"PortableContextService.__qualname__: {PortableContextService.__qualname__}")
print(f"inspect.getsourcefile(PortableContextService): {inspect.getsourcefile(PortableContextService)}")
print()

print("AVAILABLE METHODS:")
methods = [m for m in dir(PortableContextService) if not m.startswith('_')]
print(f"Public methods: {methods}")
print()

print("SPECIFIC METHOD CHECKS:")
print(f"hasattr(build_package): {hasattr(PortableContextService, 'build_package')}")
print(f"hasattr(build_package): {hasattr(PortableContextService, 'build_package')}")
print(f"hasattr(_discernment_frame_section): {hasattr(PortableContextService, '_discernment_frame_section')}")
print(f"hasattr(_unresolved_metacognitive_links_section): {hasattr(PortableContextService, '_unresolved_metacognitive_links_section')}")
print(f"hasattr(current_package): {hasattr(PortableContextService, 'current_package')}")
print(f"hasattr(compact_export): {hasattr(PortableContextService, 'compact_export')}")
print()

print("METHOD SIGNATURES:")
if hasattr(PortableContextService, 'build_package'):
    try:
        sig = inspect.signature(PortableContextService.build_package)
        print(f"build_package signature: {sig}")
    except Exception as e:
        print(f"build_package signature error: {e}")

if hasattr(PortableContextService, '_discernment_frame_section'):
    try:
        sig = inspect.signature(PortableContextService._discernment_frame_section)
        print(f"_discernment_frame_section signature: {sig}")
    except Exception as e:
        print(f"_discernment_frame_section signature error: {e}")
print()

print("SOURCE FILE LINES (build_package check):")
try:
    source_file = inspect.getsourcefile(PortableContextService)
    if source_file:
        with open(source_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for i, line in enumerate(lines):
                if 'def build_package' in line:
                    print(f"Line {i+1}: {line.strip()}")
                    # Show context
                    for j in range(max(0, i-2), min(len(lines), i+3)):
                        print(f"  {j+1}: {lines[j].rstrip()}")
                    break
            else:
                print("build_package method not found in source")
    else:
        print("Source file not found")
except Exception as e:
    print(f"Source inspection error: {e}")
print()

print("=" * 80)
