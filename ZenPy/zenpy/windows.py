from __future__ import annotations
import os
import struct
import threading

SMU_OK              = 0x01
SMU_FAILED          = 0xFF
SMU_UNKNOWN_CMD     = 0xFE
SMU_REJECTED_PREREQ = 0xFD
SMU_REJECTED_BUSY   = 0xFC

_DEVICE_PATHS = [
    r"\\?\GLOBALROOT\Device\PawnIO",
    r"\\.\PawnIO",
]
_FN_NAME_LEN = 32
_IOCTL_LOAD  = 0xA1722084
_IOCTL_EXEC  = 0xA1722104
_NARGS       = 6
_POLL_N      = 8192
_lock        = threading.Lock()
_handle      = None

_MP1: dict[str, tuple[int, int, int]] = {
    "SummitRidge":   (0x3B10528, 0x3B10564, 0x3B10598),
    "PinnacleRidge": (0x3B10528, 0x3B10564, 0x3B10598),
    "Matisse":       (0x3B10530, 0x3B1057C, 0x3B109C4),
    "Vermeer":       (0x3B10530, 0x3B1057C, 0x3B109C4),
    "VanGogh":       (0x3B10528, 0x3B10578, 0x3B10998),
    "Mendocino":     (0x3B10528, 0x3B10578, 0x3B10998),
    "Rembrandt":     (0x3B10528, 0x3B10578, 0x3B10998),
    "PhoenixPoint":  (0x3B10528, 0x3B10578, 0x3B10998),
    "PhoenixPoint2": (0x3B10528, 0x3B10578, 0x3B10998),
    "HawkPoint":     (0x3B10528, 0x3B10578, 0x3B10998),
    "HawkPoint2":    (0x3B10528, 0x3B10578, 0x3B10998),
    "SonomaValley":  (0x3B10528, 0x3B10578, 0x3B10998),
    "Raphael":       (0x3B10530, 0x3B1057C, 0x3B109C4),
    "DragonRange":   (0x3B10530, 0x3B1057C, 0x3B109C4),
    "GraniteRidge":  (0x3B10530, 0x3B1057C, 0x3B109C4),
    "FireRange":     (0x3B10530, 0x3B1057C, 0x3B109C4),
    "StrixPoint":    (0x3B10928, 0x3B10978, 0x3B10998),
    "KrackanPoint":  (0x3B10928, 0x3B10978, 0x3B10998),
    "KrackanPoint2": (0x3B10928, 0x3B10978, 0x3B10998),
    "StrixHalo":     (0x3B10928, 0x3B10978, 0x3B10998),
}
_MP1_DEFAULT = (0x3B10528, 0x3B10564, 0x3B10998)

_RSMU: dict[str, tuple[int, int, int]] = {
    "SummitRidge":   (0x3B1051C, 0x3B10568, 0x3B10590),
    "PinnacleRidge": (0x3B1051C, 0x3B10568, 0x3B10590),
    "Matisse":       (0x3B10524, 0x3B10570, 0x3B10A40),
    "Vermeer":       (0x3B10524, 0x3B10570, 0x3B10A40),
    "Raphael":       (0x3B10524, 0x3B10570, 0x3B10A40),
    "DragonRange":   (0x3B10524, 0x3B10570, 0x3B10A40),
    "GraniteRidge":  (0x3B10524, 0x3B10570, 0x3B10A40),
    "FireRange":     (0x3B10524, 0x3B10570, 0x3B10A40),
}
_RSMU_DEFAULT = (0x3B10A20, 0x3B10A80, 0x3B10A88)


def _assets_dir() -> str:
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")


def init() -> str:
    global _handle
    import ctypes

    module_path = os.path.join(_assets_dir(), "AMD", "PawnIO", "RyzenSMU.bin")
    if not os.path.exists(module_path):
        raise RuntimeError(f"PawnIO module not found: {module_path}")

    k32 = ctypes.windll.kernel32
    k32.CreateFileW.restype = ctypes.c_void_p

    handle = None
    for path in _DEVICE_PATHS:
        h = k32.CreateFileW(path, 0xC0000000, 0x3, None, 3, 0, None)
        invalid = ctypes.c_void_p(-1).value
        if h is not None and h != 0 and h != invalid:
            handle = h
            break

    if handle is None:
        raise RuntimeError(
            "PawnIO device not found. Install PawnIO: https://github.com/zorggn/PawnIO"
        )

    data = open(module_path, "rb").read()
    buf = (ctypes.c_uint8 * len(data))(*data)
    ret = ctypes.c_uint32(0)
    ok = k32.DeviceIoControl(handle, _IOCTL_LOAD, buf, len(data), None, 0, ctypes.byref(ret), None)
    if not ok:
        k32.CloseHandle(handle)
        raise RuntimeError(f"PawnIO LoadBinary failed (error {k32.GetLastError()})")

    _handle = handle
    return "pawnio"


def active_backend() -> str | None:
    return "pawnio" if _handle is not None else None


def _execute(fn_name: str, in_args: list[int], out_count: int) -> list[int]:
    import ctypes
    name_buf = struct.pack("32s", fn_name.encode("ascii")[:31])
    args_buf = struct.pack(f"<{len(in_args)}q", *in_args) if in_args else b""
    in_buf   = name_buf + args_buf

    out_buf = (ctypes.c_uint8 * (out_count * 8))() if out_count else None
    out_sz  = (out_count * 8) if out_count else 0
    ret     = ctypes.c_uint32(0)
    k32     = ctypes.windll.kernel32

    ok = k32.DeviceIoControl(
        _handle, _IOCTL_EXEC,
        (ctypes.c_uint8 * len(in_buf))(*in_buf), len(in_buf),
        out_buf, out_sz,
        ctypes.byref(ret), None,
    )
    if not ok or ret.value == 0 or out_count == 0:
        return []
    count = min(ret.value // 8, out_count)
    return list(struct.unpack(f"<{count}q", bytes(out_buf[: count * 8]))) + [0] * (out_count - count)


def _smn_read(addr: int) -> int:
    result = _execute("ioctl_read_smu_register", [addr], 1)
    return result[0] & 0xFFFFFFFF if result else 0


def _smn_write(addr: int, value: int) -> None:
    _execute("ioctl_write_smu_register", [addr, value], 0)


def _mailbox_send(msg: int, rsp: int, args_addr: int, op: int, arg0: int) -> int:
    _smn_write(rsp, 0)
    _smn_write(args_addr, arg0)
    for i in range(1, _NARGS):
        _smn_write(args_addr + i * 4, 0)
    _smn_write(msg, op)
    for _ in range(_POLL_N):
        r = _smn_read(rsp)
        if r:
            return r
    return SMU_FAILED


def _send(table: dict, default: tuple, family: str, op: int, arg0: int) -> int:
    msg, rsp, args = table.get(family, default)
    with _lock:
        return _mailbox_send(msg, rsp, args, op, arg0)


def send_mp1(family: str, op: int, arg0: int = 0) -> int:
    return _send(_MP1, _MP1_DEFAULT, family, op, arg0)


def send_rsmu(family: str, op: int, arg0: int = 0) -> int:
    return _send(_RSMU, _RSMU_DEFAULT, family, op, arg0)


def pm_table_supported() -> bool:
    return False
