from __future__ import annotations

import sys
import time
import traceback
from pathlib import Path


def main() -> int:
    # Top-level crash guard: if AppBootstrap() or run() dies, write the error
    # to a crash log so it survives hidden-console launches (shortcut / VBS).
    try:
        from iabv_v15.bootstrap import AppBootstrap
        return AppBootstrap(_defer_services=True).run()
    except Exception:
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
