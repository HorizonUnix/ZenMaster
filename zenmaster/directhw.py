from __future__ import annotations
import ctypes
import time

from zenmaster import iokitcore

DRIVER_NAME = "DirectHW"
_SERVICE    = b"DirectHWService"

_kReadIO     = 0
_kWriteIO    = 1
_kPrepareMap = 2

_kIOMapAnywhere     = 0x1
_kIOMapInhibitCache = 0x100


class _iomem_t(ctypes.Structure):
    _fields_ = [
        ("offset", ctypes.c_uint32),
        ("width",  ctypes.c_uint32),
        ("data",   ctypes.c_uint32),
    ]


class _map_t(ctypes.Structure):
    _fields_ = [
        ("addr", ctypes.c_uint64),
        ("size", ctypes.c_uint64),
    ]


_connect: int | None = None
_map_memory_bound = False


def _bind_map_memory(iokit) -> None:
    global _map_memory_bound
    if _map_memory_bound:
        return
    iokit.IOConnectMapMemory.restype  = ctypes.c_int
    iokit.IOConnectMapMemory.argtypes = [
        ctypes.c_uint, ctypes.c_uint32, ctypes.c_uint,
        ctypes.POINTER(ctypes.c_uint64), ctypes.POINTER(ctypes.c_uint64),
        ctypes.c_uint32,
    ]
    iokit.IOConnectUnmapMemory.restype  = ctypes.c_int
    iokit.IOConnectUnmapMemory.argtypes = [
        ctypes.c_uint, ctypes.c_uint32, ctypes.c_uint, ctypes.c_uint64,
    ]
    _map_memory_bound = True


def is_loaded() -> bool:
    return iokitcore.service_available(_SERVICE)


def open() -> bool:
    global _connect
    if _connect is not None:
        return True
    _connect = iokitcore.open_service(_SERVICE)
    return _connect is not None


def close() -> None:
    global _connect
    if _connect is not None:
        iokitcore.close_service(_connect)
        _connect = None


def read_io(port: int, width: int = 4) -> int:
    if _connect is None:
        return 0
    inp = _iomem_t(offset=port, width=width, data=0)
    out = _iomem_t()
    if not iokitcore.call_struct_method(_connect, _kReadIO, inp, out):
        return 0
    mask = (1 << (width * 8)) - 1
    return out.data & mask


def write_io(port: int, width: int, data: int) -> bool:
    if _connect is None:
        return False
    inp = _iomem_t(offset=port, width=width, data=data & 0xFFFFFFFF)
    out = _iomem_t()
    return iokitcore.call_struct_method(_connect, _kWriteIO, inp, out)


def read_physical(phys: int, size: int) -> bytes | None:
    if _connect is None:
        return None
    iokit = iokitcore.load()
    _bind_map_memory(iokit)

    inp = _map_t(addr=phys, size=size)
    out = _map_t()
    if not iokitcore.call_struct_method(_connect, _kPrepareMap, inp, out):
        return None

    addr   = ctypes.c_uint64(0)
    mapped = ctypes.c_uint64(0)
    err = iokit.IOConnectMapMemory(
        _connect, 0, iokitcore.task_self(),
        ctypes.byref(addr), ctypes.byref(mapped),
        _kIOMapAnywhere | _kIOMapInhibitCache,
    )
    if err != iokitcore.KERN_SUCCESS or not addr.value:
        return None
    time.sleep(0.001)
    try:
        data = ctypes.string_at(addr.value, size)
    except (ValueError, OSError):
        data = None
    iokit.IOConnectUnmapMemory(_connect, 0, iokitcore.task_self(), addr.value)
    return data
