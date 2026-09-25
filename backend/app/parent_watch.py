"""父进程看门狗。

Electron 主进程被强杀或崩溃（来不及执行 before-quit 清理）时，sidecar
作为子进程可能成为孤儿。此处通过 SMEBUDDY_PARENT_PID 监测 Electron 主进程，
发现其消失后自动退出。
"""

from __future__ import annotations

import ctypes
import logging
import os
import sys
import threading
import time

logger = logging.getLogger(__name__)

_STILL_ACTIVE = 259
_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


def _parent_alive_win(pid: int) -> bool:
    kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
    handle = kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return False
    code = ctypes.c_ulong(0)
    ok = kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
    kernel32.CloseHandle(handle)
    return bool(ok) and code.value == _STILL_ACTIVE


def _parent_alive_posix(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def start_parent_watchdog() -> None:
    pid_str = os.environ.get("SMEBUDDY_PARENT_PID")
    if not pid_str:
        return
    try:
        parent_pid = int(pid_str)
    except ValueError:
        return

    is_win = sys.platform == "win32"

    def watch() -> None:
        time.sleep(3)
        while True:
            alive = _parent_alive_win(parent_pid) if is_win else _parent_alive_posix(parent_pid)
            if not alive:
                logger.warning("检测到父进程 %s 已退出，sidecar 自动退出", parent_pid)
                os._exit(0)
            time.sleep(2)

    threading.Thread(target=watch, name="parent-watchdog", daemon=True).start()
