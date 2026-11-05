# IABV v1.5

IABV v1.5 is a desktop control application with hybrid local-first AI routing.

> **Development status:** this repository is under active development and architectural review. The presence of source code, tests, workflows, or persisted artifacts does not by itself establish production readiness or operational authorization.

## Requirements

- Python 3.11 or newer.
- Project dependencies are declared in `pyproject.toml`.
- Windows-specific dependencies are marked with environment conditions in the project metadata.

## Install the development environment

From the `IABV_v1.5/` directory:

```powershell
python -m pip install -e ".[dev]"
```

## Run the test suite

From the same directory:

```powershell
python -m pytest
```

The command above is the project test entry point; this README change does not claim that the suite has been executed or passed.

## Workspace and persisted data

The default configuration uses the supplied `workspace_root`, or the current working directory when one is not supplied, as the workspace root. Its default data directory is `<workspace_root>/data`, including the SQLite database and evolution, session, tool-teaching, and other application artifacts.

Run commands from the intended workspace root and review generated data before committing or sharing it. Some runtime directories are already tracked in Git; adding an ignore rule does not remove files that are already in the repository. Persisted sessions, browser state, credentials, and user-provided context must not be treated as harmless build output.

## Project guidance and continuity

- [AGENTS.md](AGENTS.md) contains repository-level contributor and continuity guidance.
- [CHAT-ARCH continuity index](docs/history/CHAT-ARCH/README.md) is a historical navigation aid.
- [CURRENT-STATE.md](docs/history/CHAT-ARCH/CURRENT-STATE.md) is the canonical source for the active task route, next action, technical gates, and current permissions. Its historical content must not be interpreted as current routing.

This README is a package/project entry point. It does not replace the canonical route, authorize protected operations, or claim that any runtime, bridge, or production gate has been satisfied.
