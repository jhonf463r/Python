"""Fail-closed R15F admission check.

R15F requires resuming the exact ToolTask produced by the real R15E setup.
The R15E harness is not present at the required base commit, and constructing
a substitute task would violate the experiment protocol. This test makes no
runtime claim and performs no assistant/tool execution.
"""

from pathlib import Path


BASE_COMMIT = '23f17bd2a1895fe12412f20884951cc0b5ccebfa'
R15E_HARNESS = Path(__file__).with_name('test_bio_r15e_learned_preference_to_toolcard_adapter.py')


def test_bio_r15f_requires_preserved_r15e_runtime_fixture() -> None:
    # Fail closed rather than silently importing an artifact from another
    # worktree or manually rebuilding the task that R15F is required to resume.
    assert not R15E_HARNESS.exists(), (
        'Unexpected R15E harness at this base; review provenance before running R15F.'
    )
