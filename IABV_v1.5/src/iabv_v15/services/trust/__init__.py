"""P0.213 V5: Clean Trust Boundary Package.

This package implements the canonical trust boundary architecture:
- Single authority chain
- OS-controlled identity
- Real Windows IPC
- Atomic capability consumption
- Fail-closed verification

Architecture Principles:
1. ONE canonical authority owner
2. NO duplicate authority registries
3. NO parallel legacy paths
4. NO compatibility authorities
5. Production callers required for all components
"""
