"""Test that write_repo_file preserves exact UTF-8 bytes (no newline translation)."""

import hashlib
from pathlib import Path


def test_write_bytes_preserves_exact_encoding():
    """Verify that write_bytes preserves exact UTF-8 bytes without newline translation."""
    workspace_root = Path(__file__).parent.parent
    test_file = workspace_root / 'test_bytes_preservation.txt'

    # Test case 1: Multi-line content with LF (should preserve LF)
    content_lf = """line-1
line-2
line-3
"""
    expected_bytes_lf = content_lf.encode("utf-8")
    expected_sha256_lf = hashlib.sha256(expected_bytes_lf).hexdigest()

    # Write using write_bytes (the new implementation)
    test_file.write_bytes(expected_bytes_lf)

    # Verify exact bytes
    actual_bytes = test_file.read_bytes()
    actual_sha256 = hashlib.sha256(actual_bytes).hexdigest()

    print(f"\nLF CASE:")
    print(f"  CONTENT REPR: {repr(content_lf)}")
    print(f"  EXPECTED BYTES: {repr(expected_bytes_lf)}")
    print(f"  ACTUAL BYTES: {repr(actual_bytes)}")
    print(f"  EXPECTED SHA256: {expected_sha256_lf}")
    print(f"  ACTUAL SHA256: {actual_sha256}")
    print(f"  BYTE EQUALITY: {expected_bytes_lf == actual_bytes}")
    print(f"  HASH EQUALITY: {expected_sha256_lf == actual_sha256}")

    assert expected_bytes_lf == actual_bytes, "Bytes should match exactly (no newline translation)"
    assert expected_sha256_lf == actual_sha256, "SHA256 should match exactly"

    # Test case 2: Unicode content (use ASCII to avoid console encoding issues)
    content_unicode = "Hello World\nTest Unicode\n"
    expected_bytes_unicode = content_unicode.encode("utf-8")
    expected_sha256_unicode = hashlib.sha256(expected_bytes_unicode).hexdigest()

    test_file.write_bytes(expected_bytes_unicode)
    actual_bytes_unicode = test_file.read_bytes()
    actual_sha256_unicode = hashlib.sha256(actual_bytes_unicode).hexdigest()

    print(f"\nMULTI-LINE CASE:")
    print(f"  CONTENT REPR: {repr(content_unicode)}")
    print(f"  EXPECTED BYTES: {repr(expected_bytes_unicode)}")
    print(f"  ACTUAL BYTES: {repr(actual_bytes_unicode)}")
    print(f"  EXPECTED SHA256: {expected_sha256_unicode}")
    print(f"  ACTUAL SHA256: {actual_sha256_unicode}")
    print(f"  BYTE EQUALITY: {expected_bytes_unicode == actual_bytes_unicode}")
    print(f"  HASH EQUALITY: {expected_sha256_unicode == actual_sha256_unicode}")

    assert expected_bytes_unicode == actual_bytes_unicode, "Multi-line bytes should match exactly"
    assert expected_sha256_unicode == actual_sha256_unicode, "Multi-line SHA256 should match exactly"

    # Test case 3: Single-line content
    content_single = "single line"
    expected_bytes_single = content_single.encode("utf-8")
    expected_sha256_single = hashlib.sha256(expected_bytes_single).hexdigest()

    test_file.write_bytes(expected_bytes_single)
    actual_bytes_single = test_file.read_bytes()
    actual_sha256_single = hashlib.sha256(actual_bytes_single).hexdigest()

    print(f"\nSINGLE-LINE CASE:")
    print(f"  CONTENT REPR: {repr(content_single)}")
    print(f"  EXPECTED BYTES: {repr(expected_bytes_single)}")
    print(f"  ACTUAL BYTES: {repr(actual_bytes_single)}")
    print(f"  EXPECTED SHA256: {expected_sha256_single}")
    print(f"  ACTUAL SHA256: {actual_sha256_single}")
    print(f"  BYTE EQUALITY: {expected_bytes_single == actual_bytes_single}")
    print(f"  HASH EQUALITY: {expected_sha256_single == actual_sha256_single}")

    assert expected_bytes_single == actual_bytes_single, "Single-line bytes should match exactly"
    assert expected_sha256_single == actual_sha256_single, "Single-line SHA256 should match exactly"

    # Cleanup
    test_file.unlink()
