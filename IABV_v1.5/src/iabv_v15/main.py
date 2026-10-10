from __future__ import annotations

import os
import sys
import time
import traceback
from pathlib import Path


def main() -> int:
    # I1 isolation is opt-in. A failure in this mode must not write a crash
    # log to the repository or the ordinary user profile.
    isolated_mode = os.environ.get("IABV_I1_ISOLATED_MODE", "").strip() == "1"
    workspace_root = (os.environ.get("IABV_WORKSPACE_ROOT") or None) if isolated_mode else None
    try:
        from iabv_v15.bootstrap import AppBootstrap
        return AppBootstrap(
            workspace_root=workspace_root,
            _defer_services=True,
        ).run()
    except Exception:
        crash_msg = (
            f'=== BURVE CRASH {time.strftime("%Y-%m-%d %H:%M:%S")} ===\n'
            f'{traceback.format_exc()}\n'
        )
        if not isolated_mode:
            # Preserve legacy fallback behavior outside I1 isolated mode.
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
        print(crash_msg, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
