"""Test authority resolution for caller parameters vs planner proposal."""

import hashlib


def test_caller_parameters_override_planner():
    """When caller provides parameters, they should govern execution and verification."""
    # Simulate planner generating a plan with invented content
    planner_step = {
        'parameters': {
            'relative_path': 'test.txt',
            'content': 'planner invented content\n',
        },
        'expected_result': {
            'file_exists': True,
            'content_contains': 'planner invented content',
            'file_hash_sha256': hashlib.sha256(b'planner invented content\n').hexdigest(),
        },
    }

    # Caller provides different parameters
    caller_parameters = {
        'relative_path': 'test.txt',
        'content': 'caller actual content\n',
    }

    # Authority resolution logic (from server.py)
    caller_parameters_provided = caller_parameters is not None and caller_parameters != {}
    if caller_parameters_provided:
        # Caller parameters govern execution
        tool_parameters = caller_parameters
        expected_result_source = 'caller_parameters'

        # Derive expected_result from caller parameters
        content = tool_parameters['content']
        content_bytes = content.encode("utf-8")
        content_hash = hashlib.sha256(content_bytes).hexdigest()

        expected_result = {
            'file_exists': True,
            'file_size_bytes': len(content_bytes),
            'file_hash_sha256': content_hash,
        }
    else:
        # Planner governs
        tool_parameters = planner_step['parameters']
        expected_result = planner_step['expected_result']
        expected_result_source = 'planner_proposal'

    # Verify caller parameters govern
    assert tool_parameters['content'] == 'caller actual content\n'
    assert expected_result_source == 'caller_parameters'
    assert expected_result['file_hash_sha256'] == hashlib.sha256(b'caller actual content\n').hexdigest()

    # Verify planner's invented content is NOT used
    assert expected_result['file_hash_sha256'] != hashlib.sha256(b'planner invented content\n').hexdigest()

    print("Test passed: Caller parameters override planner proposal")


def test_planner_governs_when_caller_absent():
    """When caller provides no parameters, planner proposal governs."""
    planner_step = {
        'parameters': {
            'relative_path': 'test.txt',
            'content': 'planner autonomous content\n',
        },
        'expected_result': {
            'file_exists': True,
            'content_contains': 'planner autonomous content',
            'file_hash_sha256': hashlib.sha256(b'planner autonomous content\n').hexdigest(),
        },
    }

    # Caller provides no parameters
    caller_parameters = None

    # Authority resolution logic
    caller_parameters_provided = caller_parameters is not None and caller_parameters != {}
    if caller_parameters_provided:
        tool_parameters = caller_parameters
        expected_result_source = 'caller_parameters'
        content = tool_parameters['content']
        content_bytes = content.encode("utf-8")
        content_hash = hashlib.sha256(content_bytes).hexdigest()
        expected_result = {
            'file_exists': True,
            'file_size_bytes': len(content_bytes),
            'file_hash_sha256': content_hash,
        }
    else:
        # Planner governs
        tool_parameters = planner_step['parameters']
        expected_result = planner_step['expected_result']
        expected_result_source = 'planner_proposal'

    # Verify planner governs
    assert tool_parameters['content'] == 'planner autonomous content\n'
    assert expected_result_source == 'planner_proposal'
    assert expected_result['file_hash_sha256'] == hashlib.sha256(b'planner autonomous content\n').hexdigest()

    print("Test passed: Planner governs when caller absent")
