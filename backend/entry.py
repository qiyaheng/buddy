"""PyInstaller 打包入口：避免以 app/main.py 直接作为脚本导致相对导入失败。

用法（与 sidecar 约定一致）：backend[.exe] --host 127.0.0.1 --port 18790
"""

from __future__ import annotations

import sys


def _parse_args(argv: list[str]) -> tuple[str, int]:
    host = "127.0.0.1"
    port = 18790
    i = 0
    while i < len(argv):
        if argv[i] == "--host" and i + 1 < len(argv):
            host = argv[i + 1]
            i += 2
        elif argv[i] == "--port" and i + 1 < len(argv):
            port = int(argv[i + 1])
            i += 2
        else:
            i += 1
    return host, port


def main() -> None:
    import uvicorn

    from app.main import app

    host, port = _parse_args(sys.argv[1:])
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
