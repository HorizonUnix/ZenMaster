from __future__ import annotations
import ctypes
import platform
import struct
from dataclasses import dataclass
from enum import IntEnum
from typing import Any

_IS_WINDOWS = platform.system() == "Windows"
_IS_MACOS   = platform.system() == "Darwin"


@dataclass
class ModuleStatus:
    ok: bool
    version: str
    min_version: str
    reason: str | None


class SmuStatus(IntEnum):
    OK              = 0x01
    FAILED          = 0xFF
    UNKNOWN_CMD     = 0xFE
    REJECTED_PREREQ = 0xFD
    REJECTED_BUSY   = 0xFC


SMU_OK              = SmuStatus.OK
SMU_FAILED          = SmuStatus.FAILED
SMU_UNKNOWN_CMD     = SmuStatus.UNKNOWN_CMD
SMU_REJECTED_PREREQ = SmuStatus.REJECTED_PREREQ
SMU_REJECTED_BUSY   = SmuStatus.REJECTED_BUSY

_STATUS_NAMES = {
    SmuStatus.OK:              "OK",
    SmuStatus.FAILED:          "Failed",
    SmuStatus.UNKNOWN_CMD:     "Unknown command",
    SmuStatus.REJECTED_PREREQ: "Rejected (prerequisite)",
    SmuStatus.REJECTED_BUSY:   "Rejected (busy)",
}


def status_name(code: int) -> str:
    return _STATUS_NAMES.get(code, f"0x{code:02X}")


def _backend() -> Any:
    if _IS_WINDOWS:
        from zenmaster import windows
        return windows
    if _IS_MACOS:
        from zenmaster import macos
        return macos
    from zenmaster import linux
    return linux


def smu_command(msg_id: int, arg: int = 0) -> int:
    b = _backend() if callable(_backend) else _backend
    fn = getattr(b, "smu_command", None)
    if fn is not None:
        return fn(msg_id, arg)
    ensure_backend()
    b = _backend() if callable(_backend) else _backend
    fn = getattr(b, "smu_command", None)
    if fn is not None:
        return fn(msg_id, arg)
    return SMU_FAILED


def init() -> str:
    return _backend().init()


def close() -> None:
    fn = getattr(_backend(), "close", None)
    if fn:
        fn()


def active_backend() -> str | None:
    b = _backend()
    fn = getattr(b, "active_backend", None)
    return fn() if fn else None


def send_mp1(family: str, op: int, arg0: int = 0) -> int:
    return _backend().send_mp1(family, op, arg0)


def send_rsmu(family: str, op: int, arg0: int = 0) -> int:
    return _backend().send_rsmu(family, op, arg0)


def query_mp1(family: str, op: int, arg0: int = 0) -> tuple[int, list[int]]:
    return _backend().query_mp1(family, op, arg0)


def query_rsmu(family: str, op: int, arg0: int = 0) -> tuple[int, list[int]]:
    return _backend().query_rsmu(family, op, arg0)


def send_hsmp(family: str, op: int, arg0: int = 0) -> int:
    return _backend().send_hsmp(family, op, arg0)


def query_hsmp(family: str, op: int, arg0: int = 0) -> tuple[int, list[int]]:
    return _backend().query_hsmp(family, op, arg0)


def pm_table_supported(family: str = "") -> bool:
    b = _backend()
    fn = getattr(b, "pm_table_supported", None)
    return fn(family) if fn else False


def read_pm_table(family: str = "") -> bytes | None:
    ensure_backend()
    b = _backend()
    fn = getattr(b, "read_pm_table", None)
    return fn(family) if fn else None


def read_pm_table_version(family: str = "") -> int:
    ensure_backend()
    b = _backend()
    fn = getattr(b, "read_pm_table_version", None)
    return fn(family) if fn else 0


def read_pm_table_full(family: str = "") -> tuple[bytes, int] | None:
    ensure_backend()
    b = _backend()
    fn = getattr(b, "read_pm_table_full", None)
    if fn:
        return fn(family)
    data = read_pm_table(family)
    if not data:
        return None
    return data, read_pm_table_version(family)


def secure_boot_enabled() -> bool:
    fn = getattr(_backend(), "secure_boot_enabled", None)
    return fn() if fn else False


def is_available() -> bool:
    fn = getattr(_backend(), "is_available", None)
    return fn() if fn else False


def module_version() -> str:
    fn = getattr(_backend(), "module_version", None)
    return fn() if fn else "unknown"


def module_version_ok() -> bool:
    fn = getattr(_backend(), "module_version_ok", None)
    return fn() if fn else False


def module_status() -> ModuleStatus:
    fn = getattr(_backend(), "module_status", None)
    if fn:
        return fn()
    return ModuleStatus(ok=False, version="unknown", min_version="", reason="not_loaded")


def ensure_backend() -> str | None:
    b = active_backend()
    if b is not None:
        return b
    from zenmaster.errors import ZenMasterError
    try:
        return init()
    except ZenMasterError:
        return None


def read_pm_sensors(family: str = "") -> dict[str, float] | None:
    from zenmaster.sensors import read_sensors
    ensure_backend()
    r = read_pm_table_full(family)
    if not r:
        return None
    data, ver = r
    return read_sensors(data, ver)


def send_arg(family: str, name: str, value: int) -> list[tuple[str, int, int]]:
    from zenmaster import runner
    from zenmaster.errors import UnsupportedCPU
    if not runner.is_supported(family):
        raise UnsupportedCPU(f"'{family}' is not a supported CPU family")
    ensure_backend()
    out: list[tuple[str, int, int]] = []
    use_hsmp = runner.is_hsmp(family)
    for is_mp1, op in runner.lookup(family, name):
        try:
            if use_hsmp:
                status = send_hsmp(family, op, value)
            elif is_mp1:
                status = send_mp1(family, op, value)
            else:
                status = send_rsmu(family, op, value)
        except (OSError, struct.error, ctypes.ArgumentError):
            status = SMU_FAILED
        mb_name = "HSMP" if use_hsmp else ("MP1" if is_mp1 else "RSMU")
        out.append((mb_name, op, status))
    return out


def driver_name() -> str:
    return getattr(_backend(), "DRIVER_NAME", "SMU driver")


def unavailable_reason() -> str | None:
    from zenmaster.errors import BackendUnavailable
    if active_backend() is not None:
        return None
    try:
        init()
        return None
    except BackendUnavailable as e:
        return str(e)


def get_bios_if_ver(family: str) -> int:
    ensure_backend()
    status, out = query_mp1(family, 0x03, 0)
    return out[0] if status == SMU_OK else 0


def get_smu_version(family: str) -> int:
    ensure_backend()
    b = _backend()
    fn = getattr(b, "get_smu_version", None)
    if fn is not None:
        try:
            ver = fn(family)
            if ver:
                return ver
        except Exception:
            pass
    status, out = query_mp1(family, 0x02, 1)
    if status == SMU_OK and out[0]:
        return out[0]
    if platform.system() == "Linux":
        for path in ("/sys/kernel/ryzen_smu_drv/version", "/sys/kernel/ryzen_smu_drv/drv_version"):
            try:
                with open(path, "r") as f:
                    content = f.read().strip()
                parts = [int(x) for x in content.split(".") if x.isdigit()]
                if len(parts) == 4:
                    return (parts[0] << 24) | (parts[1] << 16) | (parts[2] << 8) | parts[3]
                if len(parts) == 3:
                    return (parts[0] << 16) | (parts[1] << 8) | parts[2]
            except OSError:
                pass
    return 0


def format_smu_version(ver: int) -> str:
    if not ver:
        return "0.0.0.0"
    if ver & 0xFF000000:
        return f"{(ver >> 24) & 0xFF}.{(ver >> 16) & 0xFF}.{(ver >> 8) & 0xFF}.{ver & 0xFF}"
    return f"{(ver >> 16) & 0xFF}.{(ver >> 8) & 0xFF}.{ver & 0xFF}"


def read_pm_core_sensors(family: str = "") -> list[dict[str, float]] | None:
    from zenmaster.sensors import read_core_sensors
    ensure_backend()
    r = read_pm_table_full(family)
    if not r:
        return None
    data, ver = r
    return read_core_sensors(data, ver)


def read_smn(addr: int) -> int:
    if not ensure_backend():
        return 0
    fn = getattr(_backend(), "read_smn", None)
    try:
        return fn(addr) if fn else 0
    except OSError:
        return 0


def write_smn(addr: int, value: int) -> None:
    if not ensure_backend():
        return
    fn = getattr(_backend(), "write_smn", None)
    if fn:
        try:
            fn(addr, value)
        except OSError:
            pass


def get_ccd_count(family_int: int = 0, model_int: int = 0) -> int:
    if not ensure_backend():
        return 1
    if not family_int or not model_int:
        from zenmaster import hardware
        info = hardware.detect()
        family_int = info.cpu_family_int
        model_int = info.cpu_model_int
    ccd_fuse1 = 0x5D218
    ccd_fuse2 = 0x5D21C
    if family_int == 23 and model_int != 113:
        ccd_fuse1 += 0x40
        ccd_fuse2 += 0x40
    try:
        present = read_smn(ccd_fuse1)
        down = read_smn(ccd_fuse2)
        disabled = ((down & 0x3F) << 2) | ((present >> 30) & 0x3)
        enabled = ((present >> 22) & 0xFF) & ~disabled
        count = enabled.bit_count()
        return count if count > 0 else 1
    except OSError:
        return 1

