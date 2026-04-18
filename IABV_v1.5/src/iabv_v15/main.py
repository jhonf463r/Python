from __future__ import annotations

from iabv_v15.bootstrap import AppBootstrap


def main() -> int:
    return AppBootstrap().run()


if __name__ == "__main__":
    raise SystemExit(main())
