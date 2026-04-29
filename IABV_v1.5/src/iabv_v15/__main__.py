"""Entry point: `python -m iabv_v15 <command>`.

Subcommands:

    cm ...   — Control Master CLI (see iabv_v15.cli.control_master).
    app      — boot the full application (default if no args).
"""
from __future__ import annotations

import time as _time

# Capture the earliest possible timestamp BEFORE heavy imports.
# This is propagated to startup_timeline so marks can report
# t_ms_from_process (wall time from Python process entry).
_PROCESS_T0 = _time.perf_counter()

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] == "app":
        # Propagate process-start timestamp to the timeline module
        import iabv_v15.infra.startup_timeline as _st
        _st._PROCESS_T0 = _PROCESS_T0

        from iabv_v15.main import main as app_main

        rest = argv[1:] if argv and argv[0] == "app" else argv
        if rest:
            print(
                "warning: 'app' subcommand ignores extra arguments", file=sys.stderr
            )
        return app_main()

    if argv[0] in {"-h", "--help"}:
        parser = argparse.ArgumentParser(
            prog="python -m iabv_v15",
            description="IABV v1.5 entrypoint.",
        )
        parser.add_argument(
            "subcommand",
            choices=["app", "cm"],
            help="Subcommand to dispatch.",
        )
        parser.parse_args(argv)
        return 0

    if argv[0] == "cm":
        from iabv_v15.cli.control_master import main as cm_main

        return cm_main(argv[1:])

    print(f"error: unknown subcommand '{argv[0]}'", file=sys.stderr)
    print("usage: python -m iabv_v15 [app | cm ...]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
