from __future__ import annotations
from contextlib import contextmanager
import ctypes
import ctypes.wintypes
import os
import struct
import threading
from typing import Any

from zenmaster.errors import BackendUnavailable, SMUNotInitialized
from zenmaster.pmtable import PM_TABLE_CMDS, TABLE_SIZES, DEFAULT_TABLE_SIZE
from zenmaster.mailbox import (
    MP1, MP1_DEFAULT, RSMU, RSMU_DEFAULT, HSMP, HSMP_DEFAULT,
    mailbox_send, mailbox_query, transfer_with_retry,
)
from zenmaster.smu import SMU_OK, ModuleStatus

DRIVER_NAME = "PawnIO"
PCI_MUTEX_NAME: str = r"Global\Access_PCI"
_PCI_MUTEX_TIMEOUT_MS: int = 5000
_DEVICE_PATHS = [
    r"\\?\GLOBALROOT\Device\PawnIO",
    r"\\.\PawnIO",
]
_IOCTL_LOAD  = 0xA1B22084
_IOCTL_EXEC  = 0xA1B22104
_POLL_N      = 8192
_FAST_POLL   = 64
_POLL_SLEEP  = 0.0005
_lock        = threading.Lock()
_handle      = None
_k32         = None

_PAWNIO_INSTALLER_URL = "https://github.com/namazso/PawnIO.Setup/releases/latest/download/PawnIO_setup.exe"


_UNSET = object()
_pawnio_info_cache = _UNSET


def _pawnio_info() -> str | None:
    global _pawnio_info_cache
    if _pawnio_info_cache is _UNSET:
        _pawnio_info_cache = _query_pawnio_info()
    return _pawnio_info_cache


def _query_pawnio_info() -> str | None:
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\PawnIO",
        )
        try:
            return winreg.QueryValueEx(key, "DisplayVersion")[0]
        except OSError:
            return ""
    except OSError:
        return None


def secure_boot_enabled() -> bool:
    return False


def module_version() -> str:
    info = _pawnio_info()
    return info if info else "unknown"


def module_version_ok() -> bool:
    return _pawnio_info() is not None


def module_status() -> ModuleStatus:
    info = _pawnio_info()
    if info is None:
        return ModuleStatus(False, "unknown", "", "not_loaded")
    return ModuleStatus(True, info or "unknown", "", None)


def is_available() -> bool:
    return _pawnio_info() is not None


def acquire_pci_mutex(timeout_ms: int = _PCI_MUTEX_TIMEOUT_MS) -> Any:
    if _k32 is None:
        return None
    create_fn = getattr(_k32, "CreateMutexW", None)
    wait_fn = getattr(_k32, "WaitForSingleObject", None)
    if not create_fn or not wait_fn:
        return None
    try:
        h = create_fn(None, False, PCI_MUTEX_NAME)
        if not h or h == ctypes.c_void_p(-1).value:
            return None
        res = wait_fn(h, timeout_ms)
        if res in (0, 0x80):
            return h
        close_fn = getattr(_k32, "CloseHandle", None)
        if close_fn:
            close_fn(h)
        return None
    except Exception:
        return None


def release_pci_mutex(handle: Any) -> bool:
    if _k32 is None or handle is None:
        return False
    rel_fn = getattr(_k32, "ReleaseMutex", None)
    if not rel_fn:
        return False
    try:
        return bool(rel_fn(handle))
    except Exception:
        return False


def close_pci_mutex(handle: Any) -> bool:
    if _k32 is None or handle is None:
        return False
    close_fn = getattr(_k32, "CloseHandle", None)
    if not close_fn:
        return False
    try:
        return bool(close_fn(handle))
    except Exception:
        return False


@contextmanager
def pci_mutex_guard(timeout_ms: int = _PCI_MUTEX_TIMEOUT_MS) -> Any:
    h = acquire_pci_mutex(timeout_ms)
    try:
        yield h
    finally:
        if h is not None:
            release_pci_mutex(h)
            close_pci_mutex(h)


def _make_k32() -> Any:
    k32    = ctypes.windll.kernel32
    HANDLE = ctypes.wintypes.HANDLE
    DWORD  = ctypes.wintypes.DWORD
    BOOL   = ctypes.wintypes.BOOL
    k32.CreateFileW.restype  = HANDLE
    k32.CreateFileW.argtypes = [ctypes.c_wchar_p, DWORD, DWORD, ctypes.c_void_p, DWORD, DWORD, HANDLE]
    k32.DeviceIoControl.restype  = BOOL
    k32.DeviceIoControl.argtypes = [
        HANDLE, DWORD, ctypes.c_void_p, DWORD,
        ctypes.c_void_p, DWORD, ctypes.POINTER(DWORD), ctypes.c_void_p,
    ]
    k32.CloseHandle.restype  = BOOL
    k32.CloseHandle.argtypes = [HANDLE]
    k32.GetLastError.restype  = DWORD
    k32.GetLastError.argtypes = []
    k32.CreateMutexW.restype  = HANDLE
    k32.CreateMutexW.argtypes = [ctypes.c_void_p, BOOL, ctypes.c_wchar_p]
    k32.WaitForSingleObject.restype  = DWORD
    k32.WaitForSingleObject.argtypes = [HANDLE, DWORD]
    k32.ReleaseMutex.restype  = BOOL
    k32.ReleaseMutex.argtypes = [HANDLE]
    return k32


def _open_device(k32: Any) -> Any:
    invalid = ctypes.c_void_p(-1).value
    for path in _DEVICE_PATHS:
        h = k32.CreateFileW(path, 0xC0000000, 0x3, None, 3, 0, None)
        if h is not None and h != 0 and h != invalid:
            return h
    return None


def init() -> str:
    global _handle, _k32

    if _handle is not None:
        return "pawnio"

    module_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "RyzenSMU.bin")
    if not os.path.exists(module_path):
        raise BackendUnavailable(f"PawnIO module not found: {module_path}")

    ver = _pawnio_info()
    if ver is None:
        raise BackendUnavailable(
            "PawnIO driver is not installed.\n"
            f"Download and run the installer: {_PAWNIO_INSTALLER_URL}\n"
            "After installation, reboot and try again."
        )

    k32    = _make_k32()
    handle = _open_device(k32)
    if handle is None:
        raise BackendUnavailable(
            "PawnIO device not found. The driver may need a reboot to activate.\n"
            f"If not installed: {_PAWNIO_INSTALLER_URL}"
        )

    try:
        with open(module_path, "rb") as f:
            data = f.read()
        in_buf = ctypes.create_string_buffer(data)
        ret    = ctypes.wintypes.DWORD(0)
        ok     = k32.DeviceIoControl(
            ctypes.wintypes.HANDLE(handle),
            ctypes.wintypes.DWORD(_IOCTL_LOAD),
            ctypes.cast(in_buf, ctypes.c_void_p),
            ctypes.wintypes.DWORD(len(data)),
            None, 0,
            ctypes.byref(ret), None,
        )
        if not ok:
            err = k32.GetLastError()
            ver_str = f" (PawnIO v{ver})" if ver else ""
            raise BackendUnavailable(
                f"PawnIO LoadBinary failed (error {err}){ver_str}\n"
                "Make sure you are running as Administrator and PawnIO is fully installed.\n"
                f"If error is 1 (INVALID_FUNCTION), try reinstalling PawnIO: {_PAWNIO_INSTALLER_URL}"
            )
    except Exception:
        k32.CloseHandle(handle)
        raise

    _handle = handle
    _k32    = k32
    return "pawnio"


def active_backend() -> str | None:
    return "pawnio" if _handle is not None else None


def _require_init() -> None:
    if _handle is None or _k32 is None:
        raise SMUNotInitialized("PawnIO not initialized, call smu.init() first")


_cached_pm_ver: int | None = None
_cached_pm_size: int | None = None


def _execute(fn_name: str, in_args: list[int], out_count: int) -> list[int]:
    fn_bytes = fn_name.encode("ascii")[:31]
    name_buf = struct.pack("32s", fn_bytes)
    args_buf = struct.pack(f"<{len(in_args)}q", *in_args) if in_args else b""
    payload  = name_buf + args_buf
    in_buf   = ctypes.create_string_buffer(payload)
    out_buf  = ctypes.create_string_buffer(out_count * 8) if out_count else None
    out_sz   = out_count * 8 if out_count else 0
    ret      = ctypes.wintypes.DWORD(0)

    ok = _k32.DeviceIoControl(
        ctypes.wintypes.HANDLE(_handle),
        ctypes.wintypes.DWORD(_IOCTL_EXEC),
        ctypes.cast(in_buf, ctypes.c_void_p),
        ctypes.wintypes.DWORD(len(payload)),
        ctypes.cast(out_buf, ctypes.c_void_p) if out_buf else None,
        ctypes.wintypes.DWORD(out_sz),
        ctypes.byref(ret), None,
    )
    if not ok or ret.value == 0 or out_count == 0:
        return []
    count = min(ret.value // 8, out_count)
    return list(struct.unpack(f"<{count}q", out_buf.raw[: count * 8]))


def _execute_cmd(fn_name: str, in_args: list[int] = []) -> bool:
    fn_bytes = fn_name.encode("ascii")[:31]
    name_buf = struct.pack("32s", fn_bytes)
    args_buf = struct.pack(f"<{len(in_args)}q", *in_args) if in_args else b""
    payload  = name_buf + args_buf
    in_buf   = ctypes.create_string_buffer(payload)
    ret      = ctypes.wintypes.DWORD(0)

    ok = _k32.DeviceIoControl(
        ctypes.wintypes.HANDLE(_handle),
        ctypes.wintypes.DWORD(_IOCTL_EXEC),
        ctypes.cast(in_buf, ctypes.c_void_p),
        ctypes.wintypes.DWORD(len(payload)),
        None, 0,
        ctypes.byref(ret), None,
    )
    return bool(ok)


def _smn_read(addr: int) -> int:
    result = _execute("ioctl_read_smu_register", [addr], 1)
    return result[0] & 0xFFFFFFFF if result else 0


def _smn_write(addr: int, value: int) -> None:
    _execute("ioctl_write_smu_register", [addr, value], 0)


def _mailbox_send(msg: int, rsp: int, args_addr: int, op: int, arg0: int) -> int:
    return mailbox_send(_smn_write, _smn_read, msg, rsp, args_addr, op, arg0,
                         _POLL_N, _FAST_POLL, _POLL_SLEEP)


def _mailbox_query(msg: int, rsp: int, args_base: int, op: int, arg0: int = 0) -> tuple[int, list[int]]:
    return mailbox_query(_smn_write, _smn_read, msg, rsp, args_base, op, arg0,
                          _POLL_N, _FAST_POLL, _POLL_SLEEP)


def _resolve_pm_table() -> tuple[int, int] | None:
    _require_init()
    with _lock:
        with pci_mutex_guard():
            out = _execute("ioctl_resolve_pm_table", [], 2)
    if len(out) == 2 and out[0] != 0:
        return out[0], out[1]
    return None


def _update_pm_table(family: str = "") -> bool:
    _require_init()
    with _lock:
        with pci_mutex_guard():
            ok = _execute_cmd("ioctl_update_pm_table")
    if ok:
        return True
    if family in PM_TABLE_CMDS:
        _ver_op, _addr_op, transfer_op, _addr_64bit, extra = PM_TABLE_CMDS[family]
        msg, rsp, args_base = RSMU.get(family, RSMU_DEFAULT)
        status = _transfer_with_retry(msg, rsp, args_base, transfer_op, extra)
        return status == SMU_OK
    return False


def _read_physical_memory(phys_addr: int, size: int) -> bytes | None:
    n   = (size + 7) // 8
    raw = _execute("ioctl_read_pm_table", [], n)
    if raw:
        return struct.pack(f"<{len(raw)}q", *raw)[:size]
    return None


def _transfer_with_retry(msg: int, rsp: int, args_base: int, op: int, arg0: int = 0,
                         delays: tuple[float, ...] = (0.01, 0.1)) -> int:
    def once() -> int:
        with _lock:
            with pci_mutex_guard():
                return _mailbox_send(msg, rsp, args_base, op, arg0)
    return transfer_with_retry(once, delays)


def _send(table: dict, default: tuple, family: str, op: int, arg0: int) -> int:
    _require_init()
    msg, rsp, args = table.get(family, default)
    with _lock:
        with pci_mutex_guard():
            return _mailbox_send(msg, rsp, args, op, arg0)


def _query(table: dict, default: tuple, family: str, op: int, arg0: int) -> tuple[int, list[int]]:
    _require_init()
    msg, rsp, args = table.get(family, default)
    with _lock:
        with pci_mutex_guard():
            return _mailbox_query(msg, rsp, args, op, arg0)


def send_mp1(family: str, op: int, arg0: int = 0) -> int:
    return _send(MP1, MP1_DEFAULT, family, op, arg0)


def send_rsmu(family: str, op: int, arg0: int = 0) -> int:
    return _send(RSMU, RSMU_DEFAULT, family, op, arg0)


def query_mp1(family: str, op: int, arg0: int = 0) -> tuple[int, list[int]]:
    return _query(MP1, MP1_DEFAULT, family, op, arg0)


def query_rsmu(family: str, op: int, arg0: int = 0) -> tuple[int, list[int]]:
    return _query(RSMU, RSMU_DEFAULT, family, op, arg0)


def send_hsmp(family: str, op: int, arg0: int = 0) -> int:
    return _send(HSMP, HSMP_DEFAULT, family, op, arg0)


def query_hsmp(family: str, op: int, arg0: int = 0) -> tuple[int, list[int]]:
    return _query(HSMP, HSMP_DEFAULT, family, op, arg0)


def read_smn(addr: int) -> int:
    _require_init()
    with _lock:
        with pci_mutex_guard():
            return _smn_read(addr)


def write_smn(addr: int, value: int) -> None:
    _require_init()
    with _lock:
        with pci_mutex_guard():
            _smn_write(addr, value)


def smu_command(msg_id: int, arg: int = 0) -> int:
    _require_init()
    msg, rsp, args = MP1_DEFAULT
    with _lock:
        with pci_mutex_guard():
            return _mailbox_send(msg, rsp, args, msg_id, arg)


def get_smu_version(family: str = "") -> int:
    _require_init()
    with _lock:
        with pci_mutex_guard():
            out = _execute("ioctl_get_smu_version", [], 1)
    if out and out[0]:
        return out[0]
    msg, rsp, args = MP1.get(family, MP1_DEFAULT)
    with _lock:
        with pci_mutex_guard():
            status, res = _mailbox_query(msg, rsp, args, 0x02, 1)
    return res[0] if status == SMU_OK and res[0] else 0


def get_code_name() -> int:
    _require_init()
    out = _execute("ioctl_get_code_name", [], 1)
    return out[0] if out else -1


def pm_table_supported(family: str = "") -> bool:
    return family in PM_TABLE_CMDS


def read_pm_table_full(family: str = "") -> tuple[bytes, int] | None:
    _require_init()
    if not _handle:
        return None

    global _cached_pm_ver, _cached_pm_size

    if _cached_pm_ver is None:
        resolved = _resolve_pm_table()
        if resolved is not None:
            _cached_pm_ver, _ = resolved
            _cached_pm_size = TABLE_SIZES.get(_cached_pm_ver, DEFAULT_TABLE_SIZE)
        elif family in PM_TABLE_CMDS:
            ver = read_pm_table_version(family)
            if ver:
                _cached_pm_ver = ver
                _cached_pm_size = TABLE_SIZES.get(ver, DEFAULT_TABLE_SIZE)

    if _cached_pm_ver is None or not _cached_pm_ver:
        return None

    ver = _cached_pm_ver
    size = _cached_pm_size or DEFAULT_TABLE_SIZE

    _update_pm_table(family)

    n = (size + 7) // 8
    with _lock:
        raw = _execute("ioctl_read_pm_table", [], n)

    if not raw:
        resolved = _resolve_pm_table()
        if resolved is not None:
            _cached_pm_ver, _ = resolved
            _cached_pm_size = TABLE_SIZES.get(_cached_pm_ver, DEFAULT_TABLE_SIZE)
            ver = _cached_pm_ver
            size = _cached_pm_size or DEFAULT_TABLE_SIZE
            n = (size + 7) // 8
            _update_pm_table(family)
            with _lock:
                raw = _execute("ioctl_read_pm_table", [], n)

    if not raw:
        return None

    data = struct.pack(f"<{len(raw)}q", *raw)[:size]
    return (data, ver)


def read_pm_table_version(family: str = "") -> int:
    global _cached_pm_ver
    if _cached_pm_ver:
        return _cached_pm_ver
    if _handle:
        resolved = _resolve_pm_table()
        if resolved and resolved[0]:
            _cached_pm_ver = resolved[0]
            return _cached_pm_ver
    if _handle and family in PM_TABLE_CMDS:
        ver_op = PM_TABLE_CMDS[family][0]
        msg, rsp, args_base = RSMU.get(family, RSMU_DEFAULT)
        with _lock:
            with pci_mutex_guard():
                status, out = _mailbox_query(msg, rsp, args_base, ver_op)
        if status == SMU_OK and out[0]:
            return out[0]
    return 0


def read_pm_table(family: str = "") -> bytes | None:
    r = read_pm_table_full(family)
    return r[0] if r else None


def close() -> None:
    global _handle, _k32, _pawnio_info_cache, _cached_pm_ver, _cached_pm_size
    if _handle is not None and _k32 is not None:
        _k32.CloseHandle(ctypes.wintypes.HANDLE(_handle))
    _handle = None
    _k32 = None
    _pawnio_info_cache = _UNSET
    _cached_pm_ver = None
    _cached_pm_size = None

