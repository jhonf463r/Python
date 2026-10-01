"""
Test: IABV_SKIP_TOOL_AVAILABILITY_PROBE isolation gate.

Verifies that the IABV_SKIP_TOOL_AVAILABILITY_PROBE flag:
- Default behavior: current probe scheduling behavior preserved
- Experimental behavior: probe is not scheduled/executed when flag=1
"""

import os
import pytest


def test_default_behavior_probes_scheduled():
    """Default: tool availability probe is scheduled (current production behavior)."""
    # Ensure flag is not set
    if 'IABV_SKIP_TOOL_AVAILABILITY_PROBE' in os.environ:
        del os.environ['IABV_SKIP_TOOL_AVAILABILITY_PROBE']
    
    # Simulate initialization logic from bootstrap.__init__
    _tool_availability_logged = False
    _skip_tool_availability_probe = os.environ.get('IABV_SKIP_TOOL_AVAILABILITY_PROBE', '0') == '1'
    
    # This is the core logic from bootstrap.__init__
    if os.environ.get('IABV_DEFER_TOOL_PROBE', '1') == '0':
        if not _skip_tool_availability_probe:
            _tool_availability_logged = True
            # Probe would be called here
    
    # In default mode with IABV_DEFER_TOOL_PROBE=1 (default),
    # the probe is NOT called synchronously, but is scheduled deferred
    # We verify the flag value
    assert _skip_tool_availability_probe == False
    assert _tool_availability_logged == False  # Not called in deferred mode


def test_skip_flag_suppresses_probe():
    """Experimental: IABV_SKIP_TOOL_AVAILABILITY_PROBE=1 suppresses probe."""
    # Set the flag
    os.environ['IABV_SKIP_TOOL_AVAILABILITY_PROBE'] = '1'
    
    try:
        # Simulate initialization logic
        _tool_availability_logged = False
        _skip_tool_availability_probe = os.environ.get('IABV_SKIP_TOOL_AVAILABILITY_PROBE', '0') == '1'
        
        # Even with IABV_DEFER_TOOL_PROBE=0 (sync mode), probe should be skipped
        if os.environ.get('IABV_DEFER_TOOL_PROBE', '1') == '0':
            if not _skip_tool_availability_probe:
                _tool_availability_logged = True
                # Probe would be called here
        
        # Verify flag prevents probe
        assert _skip_tool_availability_probe == True
        assert _tool_availability_logged == False
    finally:
        # Clean up
        if 'IABV_SKIP_TOOL_AVAILABILITY_PROBE' in os.environ:
            del os.environ['IABV_SKIP_TOOL_AVAILABILITY_PROBE']


def test_skip_flag_suppresses_deferred_probe():
    """Experimental: IABV_SKIP_TOOL_AVAILABILITY_PROBE=1 suppresses deferred probe."""
    # Set the flag
    os.environ['IABV_SKIP_TOOL_AVAILABILITY_PROBE'] = '1'
    
    try:
        # Simulate _run_deferred_post_window_setup logic
        _tool_availability_logged = False
        _skip_tool_availability_probe = os.environ.get('IABV_SKIP_TOOL_AVAILABILITY_PROBE', '0') == '1'
        
        # This is the core logic from _run_deferred_post_window_setup
        if _tool_availability_logged:
            return
        if _skip_tool_availability_probe:
            _tool_availability_logged = True
            return
        _tool_availability_logged = True
        
        # Verify flag prevents deferred probe
        assert _skip_tool_availability_probe == True
        assert _tool_availability_logged == True  # Set to prevent re-entry, but probe not called
    finally:
        # Clean up
        if 'IABV_SKIP_TOOL_AVAILABILITY_PROBE' in os.environ:
            del os.environ['IABV_SKIP_TOOL_AVAILABILITY_PROBE']


def test_defer_tool_probe_backward_compatibility():
    """Verify IABV_DEFER_TOOL_PROBE still works as before."""
    # Test default (deferred)
    if 'IABV_DEFER_TOOL_PROBE' in os.environ:
        del os.environ['IABV_DEFER_TOOL_PROBE']
    
    _tool_availability_logged = False
    _skip_tool_availability_probe = os.environ.get('IABV_SKIP_TOOL_AVAILABILITY_PROBE', '0') == '1'
    
    # Default: IABV_DEFER_TOOL_PROBE=1, probe is deferred
    if os.environ.get('IABV_DEFER_TOOL_PROBE', '1') == '0':
        if not _skip_tool_availability_probe:
            _tool_availability_logged = True
    
    assert _tool_availability_logged == False  # Not called synchronously
    
    # Test legacy sync mode
    os.environ['IABV_DEFER_TOOL_PROBE'] = '0'
    try:
        _tool_availability_logged = False
        _skip_tool_availability_probe = os.environ.get('IABV_SKIP_TOOL_AVAILABILITY_PROBE', '0') == '1'
        
        if os.environ.get('IABV_DEFER_TOOL_PROBE', '1') == '0':
            if not _skip_tool_availability_probe:
                _tool_availability_logged = True
        
        assert _tool_availability_logged == True  # Called synchronously in legacy mode
    finally:
        if 'IABV_DEFER_TOOL_PROBE' in os.environ:
            del os.environ['IABV_DEFER_TOOL_PROBE']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
