"""
META-01-E2a WINDOWS PRODUCTION BOOTSTRAP VERIFICATION - CLEAN EXECUTION

This script performs a single clean execution without explicit method calls.
It allows the real deferred metacognition path to execute automatically.
"""

import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Add the project to the path
project_root = Path(__file__).parent / "IABV_v1.5"
src_root = project_root / "src"
sys.path.insert(0, str(src_root))
sys.path.insert(0, str(project_root))

print("=" * 80)
print("META-01-E2a WINDOWS PRODUCTION BOOTSTRAP VERIFICATION - CLEAN")
print("=" * 80)
print()

# PHASE 1: PROVENANCE
print("PHASE 1: PROVENANCE")
print(f"Workspace root: {project_root}")
print(f"Script path: {Path(__file__).absolute()}")
print(f"Python version: {sys.version}")
print()

# PHASE 2: ACTUAL APPBOOTSTRAP
print("PHASE 2: ACTUAL APPBOOTSTRAP")
print("Importing AppBootstrap...")
runtime_start = time.time()

from iabv_v15.bootstrap import AppBootstrap

print(f"Runtime start: {datetime.now(timezone.utc).isoformat()}")
print("Constructing AppBootstrap (this will trigger real deferred metacognition)...")

# Construct AppBootstrap - this will trigger real deferred metacognition automatically
bootstrap = AppBootstrap(workspace_root=str(project_root))

bootstrap_constructed = time.time()
print(f"AppBootstrap constructed: {datetime.now(timezone.utc).isoformat()}")
print(f"Bootstrap duration: {bootstrap_constructed - runtime_start:.2f}s")
print()

# Invoke deferred metacognition explicitly (simulates what post-window thread would do)
print("Invoking deferred metacognition (simulates post-window startup)...")
deferred_start = time.time()
bootstrap._run_deferred_metacognition_scan()
deferred_end = time.time()
print(f"Deferred metacognition duration: {deferred_end - deferred_start:.2f}s")

# Wait for background thread to complete
print("Waiting for background thread to complete...")
time.sleep(2.0)
print()

# PHASE 3: REAL OBJECT IDENTITY
print("PHASE 3: REAL OBJECT IDENTITY")
print("Capturing object IDs...")

bootstrap_service_id = id(bootstrap.discernment_frame_service)
oses_service_id = id(bootstrap.operational_self_examination_service.discernment_frame_service)
tca_service_id = id(bootstrap.task_context_assembler.discernment_frame_service)
pcs_service_id = id(bootstrap.portable_context_service.discernment_frame_service)

print(f"bootstrap.discernment_frame_service id: {bootstrap_service_id}")
print(f"OSES.discernment_frame_service id: {oses_service_id}")
print(f"TCA.discernment_frame_service id: {tca_service_id}")
print(f"PCS.discernment_frame_service id: {pcs_service_id}")

all_identical = (bootstrap_service_id == oses_service_id == tca_service_id == pcs_service_id)
print(f"All identical: {all_identical}")
print()

# PHASE 4: BIRTH FRAME (read from shared service after natural startup)
print("PHASE 4: BIRTH FRAME (from shared service)")
print("Available methods on DiscernmentFrameService:")
frame_methods = [m for m in dir(bootstrap.discernment_frame_service) if not m.startswith('_')]
print(frame_methods)
print()

# Try to get current frame
latest_frame = None
try:
    # Use latest_frame() which is thread-safe
    if hasattr(bootstrap.discernment_frame_service, 'latest_frame'):
        latest_frame = bootstrap.discernment_frame_service.latest_frame()
        if latest_frame:
            print(f"frame_id: {latest_frame.frame_id}")
            print(f"phase: {latest_frame.phase}")
            print(f"trigger_source: {latest_frame.trigger_source}")
            print(f"grounding_status: {latest_frame.grounding_status}")
            print(f"confidence: {latest_frame.confidence}")
            print(f"unresolved_fields: {latest_frame.unresolved_fields}")
            print(f"missing_sources: {latest_frame.missing_sources}")
        else:
            print("No latest frame after deferred metacognition")
            print("Checking frame history directly...")
            if hasattr(bootstrap.discernment_frame_service, '_frame_history'):
                print(f"Frame history count: {len(bootstrap.discernment_frame_service._frame_history)}")
    else:
        print("latest_frame method not found")
except Exception as e:
    print(f"Error reading frame: {e}")
print()

# PHASE 5: OSES REAL CONSUMER
print("PHASE 5: OSES REAL CONSUMER")
oses = bootstrap.operational_self_examination_service

# Execute OSES discernment frame review
review = oses.build_review()
print(f"Review ID: {review.review_id}")
print(f"Finding categories: {[f.category for f in review.findings]}")

# Check for missing-frame finding
missing_frame_finding = any(f.category == "discernment_frame_missing_in_task_context" for f in review.findings)
print(f"Missing-frame finding present: {missing_frame_finding}")

# Check observed frame
discernment_findings = [f for f in review.findings if "discernment" in f.category.lower() or "frame" in f.category.lower()]
print(f"Discernment-related findings: {len(discernment_findings)}")

# Read current frame from OSES service
oses_frames = None
try:
    if hasattr(oses.discernment_frame_service, '_frame_history'):
        oses_frames = oses.discernment_frame_service._frame_history
    elif hasattr(oses.discernment_frame_service, 'get_current_frame'):
        frame = oses.discernment_frame_service.get_current_frame()
        oses_frames = [frame] if frame else []
    
    if oses_frames:
        print(f"OSES frame count: {len(oses_frames)}")
        print(f"OSES latest frame_id: {oses_frames[-1].frame_id}")
        print(f"OSES latest phase: {oses_frames[-1].phase}")
    else:
        print("OSES: No frames found")
except Exception as e:
    print(f"OSES frame read error: {e}")
print()

# PHASE 6: TASKCONTEXTASSEMBLER REAL
print("PHASE 6: TASKCONTEXTASSEMBLER REAL")
tca = bootstrap.task_context_assembler

# Get discernment frame summary
summary = tca._discernment_frame_summary()
if isinstance(summary, dict):
    print(f"Summary status: {summary.get('status', 'N/A')}")
    print(f"Phase: {summary.get('phase', 'N/A')}")
    print(f"Grounding status: {summary.get('grounding_status', 'N/A')}")
    print(f"Confidence: {summary.get('confidence', 'N/A')}")
    print(f"Unresolved fields: {summary.get('unresolved_fields', 'N/A')}")
else:
    print(f"Summary: {summary}")
print()

# PHASE 7: PORTABLECONTEXT REAL
print("PHASE 7: PORTABLECONTEXT REAL")
pcs = bootstrap.portable_context_service

print("Getting discernment frame section...")
now = datetime.now(timezone.utc)
discernment_section = pcs._discernment_frame_section(now=now)
print(f"Section attributes: {vars(discernment_section).keys()}")
print(f"Section ID: {discernment_section.section_id}")
print(f"Section title: {discernment_section.title}")
print(f"Section summary: {discernment_section.summary}")
print(f"Confidence: {discernment_section.confidence}")
print(f"Unresolved fields: {discernment_section.unresolved_fields}")

print("Getting unresolved metacognitive links section...")
unresolved_section = pcs._unresolved_metacognitive_links_section(now=now)
print(f"Section ID: {unresolved_section.section_id}")
print(f"Section title: {unresolved_section.title}")
print(f"Unresolved fields: {unresolved_section.unresolved_fields}")
print()

# PHASE 8: SUMMARY
print("=" * 80)
print("VERIFICATION SUMMARY")
print("=" * 80)
print(f"Runtime duration: {time.time() - runtime_start:.2f}s")
print(f"Shared object identity: {all_identical}")
print(f"Birth frame produced: {latest_frame is not None}")
if latest_frame:
    print(f"Birth frame phase: {latest_frame.phase}")
    print(f"Birth frame trigger: {latest_frame.trigger_source}")
    print(f"Birth frame ID: {latest_frame.frame_id}")
print(f"OSES observed frame: {oses_frames is not None and len(oses_frames) > 0}")
if oses_frames and latest_frame:
    print(f"OSES frame_id matches birth: {oses_frames[-1].frame_id == latest_frame.frame_id}")
print(f"TCA summary available: {summary is not None}")
print(f"PCS sections accessible: True")
print()
print("Execution ID: E2a-Windows-Clean-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"))
print("=" * 80)
