from __future__ import annotations
import threading
import time

from zenmaster import directhw, iokit
from zenmaster.hardware import _sysctl_str
from zenmaster.errors import BackendUnavailable, SMUNotInitialized
from zenmaster.pmtable import PM_TABLE_CMDS, TABLE_SIZES, DEFAULT_TABLE_SIZE
from zenmaster.mailbox import MP1, MP1_DEFAULT, RSMU, RSMU_DEFAULT, NARGS
from zenmaster.smu import SMU_OK, SMU_FAILED, SMU_REJECTED_PREREQ, ModuleStatus

DRIVER_NAME = "DirectHW"

NB_ADDR  = 0xB8
NB_DATA  = 0xBC
PCI_ADDR = 0xCF8
PCI_DATA = 0xCFC

_POLL_N     = 100
_FAST_POLL  = 64
_POLL_SLEEP = 0.0005
_lock       = threading.Lock()
_backend: str | None = None
_force: str | None = None

_KEXT_URL = "https://github.com/joevt/directhw"

_IOPCI_DEBUG_MSG = "The IOPCIBridge path requires the debug=0x144 boot-arg."


def force_iopci() -> None:
    global _force
    _force = "iopci"


def secure_boot_enabled() -> bool:
    return False


def _debug_boot_arg_ok() -> bool:
    return "debug=0x144" in _sysctl_str("kern.bootargs")


def module_version() -> str:
    return "loaded" if is_available() else "unknown"


def module_version_ok() -> bool:
    return is_available()


def module_status() -> ModuleStatus:
    if not is_available():
        return ModuleStatus(False, "unknown", "", "not_loaded")
    return ModuleStatus(True, "loaded", "", None)


def is_available() -> bool:
    return directhw.is_loaded() or iokit.is_available()


def init() -> str:
    global _backend, DRIVER_NAME

    if _backend is not None:
        return _backend

    if _force == "iopci":
        if not _debug_boot_arg_ok():
            raise BackendUnavailable(_IOPCI_DEBUG_MSG)
        if not iokit.open():
            raise BackendUnavailable(
                "IOPCIBridge could not be opened for the --iopci path.\n"
                "Run as root (sudo)."
            )
        DRIVER_NAME = "IOKit PCI"
        _backend = "iopci"
        return _backend

    if directhw.is_loaded() and directhw.open():
        DRIVER_NAME = "DirectHW"
        _backend = "directhw"
        return _backend

    if _debug_boot_arg_ok() and iokit.open():
        DRIVER_NAME = "IOKit PCI"
        _backend = "iopci"
        return _backend

    lines = [
        "No SMU access path is available on macOS.",
        "",
        "Options:",
        "1. Install and load DirectHW.kext (enables tuning + sensors):",
    ]
    if _KEXT_URL:
        lines.append(f"   {_KEXT_URL}")
    lines += [
        "   Hackintosh: set SIP csr-active-config to 03080000 to allow kexts.",
        "2. Use the kext-free IOPCIBridge path (tuning only — no PM-table sensors):",
        "   run as root (sudo) and add the boot-arg debug=0x144.",
    ]
    raise BackendUnavailable("\n".join(lines))


def active_backend() -> str | None:
    return _backend


def _cfg_addr(reg: int) -> int:
    return 0x80000000 | (reg & 0xFC)


def _pci_cfg_read(reg: int) -> int:
    if _backend == "iopci":
        return iokit.read_config(reg, 4)
    directhw.write_io(PCI_ADDR, 4, _cfg_addr(reg))
    return directhw.read_io(PCI_DATA, 4)


def _pci_cfg_write(reg: int, value: int) -> None:
    if _backend == "iopci":
        iokit.write_config(reg, 4, value)
        return
    directhw.write_io(PCI_ADDR, 4, _cfg_addr(reg))
    directhw.write_io(PCI_DATA, 4, value)


def _smn_read(addr: int) -> int:
    _pci_cfg_write(NB_ADDR, addr & ~3)
    return _pci_cfg_read(NB_DATA)


def _smn_write(addr: int, value: int) -> None:
    _pci_cfg_write(NB_ADDR, addr)
    _pci_cfg_write(NB_DATA, value)


def _poll_response(rsp: int) -> int:
    for i in range(_POLL_N):
        r = _smn_read(rsp)
        if r:
            return r
        if i >= _FAST_POLL:
            time.sleep(_POLL_SLEEP)
    return 0


def _mailbox_send(msg: int, rsp: int, args_addr: int, op: int, arg0: int) -> int:
    _smn_write(rsp, 0)
    _smn_write(args_addr, arg0)
    for i in range(1, NARGS):
        _smn_write(args_addr + i * 4, 0)
    _smn_write(msg, op)
    return _poll_response(rsp) or SMU_FAILED


def _mailbox_query(msg: int, rsp: int, args_base: int, op: int, arg0: int = 0) -> tuple[int, list[int]]:
    _smn_write(rsp, 0)
    for i in range(NARGS):
        _smn_write(args_base + i * 4, 0)
    if arg0:
        _smn_write(args_base, arg0)
    _smn_write(msg, op)
    r = _poll_response(rsp)
    if r:
        return r, [_smn_read(args_base + i * 4) for i in range(NARGS)]
    return SMU_FAILED, [0] * NARGS


def _require_init() -> None:
    if _backend is None:
        raise SMUNotInitialized("SMU not initialized — call smu.init() first")


def _send(table: dict, default: tuple, family: str, op: int, arg0: int) -> int:
    _require_init()
    msg, rsp, args = table.get(family, default)
    with _lock:
        return _mailbox_send(msg, rsp, args, op, arg0)


def _query(table: dict, default: tuple, family: str, op: int, arg0: int) -> tuple[int, list[int]]:
    _require_init()
    msg, rsp, args = table.get(family, default)
    with _lock:
        return _mailbox_query(msg, rsp, args, op, arg0)


def send_mp1(family: str, op: int, arg0: int = 0) -> int:
    return _send(MP1, MP1_DEFAULT, family, op, arg0)


def send_rsmu(family: str, op: int, arg0: int = 0) -> int:
    return _send(RSMU, RSMU_DEFAULT, family, op, arg0)


def query_mp1(family: str, op: int, arg0: int = 0) -> tuple[int, list[int]]:
    return _query(MP1, MP1_DEFAULT, family, op, arg0)


def query_rsmu(family: str, op: int, arg0: int = 0) -> tuple[int, list[int]]:
    return _query(RSMU, RSMU_DEFAULT, family, op, arg0)


def pm_table_supported(family: str = "") -> bool:
    return _backend != "iopci" and family in PM_TABLE_CMDS


def _transfer_with_retry(msg: int, rsp: int, args_base: int, op: int, arg0: int = 0,
                         delays: tuple[float, ...] = (0.01, 0.1)) -> int:
    with _lock:
        status = _mailbox_send(msg, rsp, args_base, op, arg0)
    for delay in delays:
        if status != SMU_REJECTED_PREREQ:
            break
        time.sleep(delay)
        with _lock:
            status = _mailbox_send(msg, rsp, args_base, op, arg0)
    return status


def read_pm_table_version(family: str = "") -> int:
    if _backend in (None, "iopci") or family not in PM_TABLE_CMDS:
        return 0
    ver_op = PM_TABLE_CMDS[family][0]
    msg, rsp, args_base = RSMU.get(family, RSMU_DEFAULT)
    with _lock:
        status, out = _mailbox_query(msg, rsp, args_base, ver_op)
    return out[0] if status == SMU_OK else 0


def read_pm_table(family: str = "") -> bytes | None:
    if _backend in (None, "iopci") or family not in PM_TABLE_CMDS:
        return None
    ver_op, addr_op, transfer_op, addr_64bit, extra = PM_TABLE_CMDS[family]
    msg, rsp, args_base = RSMU.get(family, RSMU_DEFAULT)

    with _lock:
        status, out = _mailbox_query(msg, rsp, args_base, ver_op)
    if status != SMU_OK or not out[0]:
        return None
    size = TABLE_SIZES.get(out[0], DEFAULT_TABLE_SIZE)

    with _lock:
        status, out = _mailbox_query(msg, rsp, args_base, addr_op, extra)
    if status != SMU_OK:
        return None
    phys_addr = (out[1] << 32) | out[0] if addr_64bit else out[0]
    if not phys_addr:
        return None

    status = _transfer_with_retry(msg, rsp, args_base, transfer_op, extra)
    if status != SMU_OK:
        return None
    return directhw.read_physical(phys_addr, size)
