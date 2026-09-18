#!/bin/bash
# L5 Evidence Capture Script
# Captures git provenance externally before test execution
# Calculates artifact SHA256 independently after test execution

set -e

cd "$(dirname "$0")"

# Capture git provenance BEFORE execution
PROVENANCE_TESTED_HEAD=$(git rev-parse HEAD)
PROVENANCE_PARENT=$(git rev-parse HEAD^)
PROVENANCE_TREE=$(git rev-parse HEAD^{tree})
PROVENANCE_BRANCH=$(git branch --show-current)
PROVENANCE_REPO=$(git config --get remote.origin.url)
PROVENANCE_TIMESTAMP_START=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

echo "=== GIT PROVENANCE CAPTURE ==="
echo "REPO: $PROVENANCE_REPO"
echo "BRANCH: $PROVENANCE_BRANCH"
echo "TESTED_HEAD: $PROVENANCE_TESTED_HEAD"
echo "PARENT: $PROVENANCE_PARENT"
echo "TREE_SHA: $PROVENANCE_TREE"
echo "TIMESTAMP_START: $PROVENANCE_TIMESTAMP_START"
echo ""

# Run the test
TIMESTAMP=$(date -u +"%Y%m%d_%H%M%S")
LOG_FILE="l5_experiment_${TIMESTAMP}_runtime.log"

echo "=== RUNNING L5 TEST ==="
echo "LOG: $LOG_FILE"
echo ""

export PYTHONPATH="$(pwd)/src"
python -m pytest -vv -s tests/windows_e2e/test_l5_real_g3_causal_closure.py::test_l5_real_g3_causal_closure 2>&1 | tee "$LOG_FILE"
EXIT_CODE=$?

PROVENANCE_TIMESTAMP_END=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

echo ""
echo "=== TEST COMPLETED ==="
echo "EXIT_CODE: $EXIT_CODE"
echo "TIMESTAMP_END: $PROVENANCE_TIMESTAMP_END"
echo ""

# Calculate artifact SHA256 independently
if [ -f "$LOG_FILE" ]; then
    ARTIFACT_SHA256=$(sha256sum "$LOG_FILE" | cut -d' ' -f1)

    echo "=== ARTIFACT INTEGRITY ==="
    echo "ARTIFACT_PATH: $LOG_FILE"
    echo "ARTIFACT_SHA256: $ARTIFACT_SHA256"
    echo ""

    # Create manifest
    cat > "l5_experiment_${TIMESTAMP}_manifest.txt" <<EOF
EXPERIMENT_ID: $TIMESTAMP
REPO: $PROVENANCE_REPO
BRANCH: $PROVENANCE_BRANCH
TESTED_HEAD: $PROVENANCE_TESTED_HEAD
PARENT: $PROVENANCE_PARENT
TREE_SHA: $PROVENANCE_TREE
RUNTIME_START: $PROVENANCE_TIMESTAMP_START
RUNTIME_END: $PROVENANCE_TIMESTAMP_END
ARTIFACT_PATH: $LOG_FILE
ARTIFACT_SHA256: $ARTIFACT_SHA256
EXIT_CODE: $EXIT_CODE
EOF

    echo "=== MANIFEST CREATED ==="
    echo "MANIFEST: l5_experiment_${TIMESTAMP}_manifest.txt"
    echo ""

    echo "=== COMPLETE EVIDENCE PACKAGE ==="
    echo "1. Runtime log: $LOG_FILE"
    echo "2. Manifest: l5_experiment_${TIMESTAMP}_manifest.txt"
    echo "3. SHA256: $ARTIFACT_SHA256"
else
    echo "ERROR: Log file not created: $LOG_FILE"
    exit 1
fi

exit $EXIT_CODE
