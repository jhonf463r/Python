from __future__ import annotations

import os
import sys
import time
import traceback
from pathlib import Path


def main() -> int:
    # Top-level crash guard: if AppBootstrap() or run() dies, write the error
    # to a crash log so it survives hidden-console launches (shortcut / VBS).
    try:
        from iabv_v15.bootstrap import AppBootstrap
        from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer

        # Emit runtime_process_started at canonical process lifecycle boundary
        tracer = get_runtime_tracer()
        tracer.trace_runtime_process_started(
            pid=os.getpid(),
            workspace=str(Path.cwd()),
        )

        return AppBootstrap(_defer_services=True).run()
    except Exception:
        # Emit runtime_process_crash on top-level exception path
        from iabv_v15.services.evolution.runtime_audit_tracer import get_runtime_tracer
        tracer = get_runtime_tracer()
        tracer.trace_runtime_process_crash(
            error_type=type(sys.exc_info()[1]).__name__ if sys.exc_info()[1] else 'Exception',
            error_message=str(sys.exc_info()[1]) if sys.exc_info()[1] else '',
            traceback_summary=traceback.format_exc(),
        )

        crash_msg = (
            f'=== BURVE CRASH {time.strftime("%Y-%m-%d %H:%M:%S")} ===\n'
            f'{traceback.format_exc()}\n'
        )
        # Try multiple locations for the crash log
        for log_dir in [
            Path('data/logs'),
            Path.home() / '.iabv' / 'logs',
        ]:
            try:
                log_dir.mkdir(parents=True, exist_ok=True)
                (log_dir / 'ui_crash.log').write_text(crash_msg, encoding='utf-8')
                break
            except Exception:
                continue
        # Also print to stderr in case console is visible
        print(crash_msg, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
