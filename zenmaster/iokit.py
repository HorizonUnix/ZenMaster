from __future__ import annotations
import ctypes

from zenmaster import iokitcore

_SERVICE = b"IOPCIBridge"

_kIOPCIDiagnosticsClientType = 0x99000001
_kMethodRead  = 0
_kMethodWrite = 1
_kIOPCIConfigSpace = 0


class _DiagParams(ctypes.Structure):
    _fields_ = [
        ("options",   ctypes.c_uint32),
        ("spaceType", ctypes.c_uint32),
        ("bitWidth",  ctypes.c_uint32),
        ("_resv",     ctypes.c_uint32),
        ("value",     ctypes.c_uint64),
        ("address",   ctypes.c_uint64),
    ]


_connect: int | None = None


def is_available() -> bool:
    return iokitcore.service_available(_SERVICE)


def open() -> bool:
    global _connect
    if _connect is not None:
        return True
    _connect = iokitcore.open_service(_SERVICE, _kIOPCIDiagnosticsClientType)
    return _connect is not None


def close() -> None:
    global _connect
    if _connect is not None:
        iokitcore.close_service(_connect)
        _connect = None


def _pci_address(reg: int, bus: int = 0, dev: int = 0, fn: int = 0) -> int:
    return (reg & 0xFFFF) | ((fn & 0x7) << 16) | ((dev & 0x1F) << 19) | ((bus & 0xFF) << 24)


def read_config(reg: int, width: int = 4) -> int:
    if _connect is None:
        return 0
    param = _DiagParams()
    param.options   = 0
    param.spaceType = _kIOPCIConfigSpace
    param.bitWidth  = width * 8
    param.address   = _pci_address(reg)
    param.value     = 0xFFFFFFFFFFFFFFFF
    if not iokitcore.call_struct_method(_connect, _kMethodRead, param, param):
        return 0
    mask = (1 << (width * 8)) - 1
    return param.value & mask


def write_config(reg: int, width: int, value: int) -> bool:
    if _connect is None:
        return False
    mask  = (1 << (width * 8)) - 1
    param = _DiagParams()
    param.options   = 0
    param.spaceType = _kIOPCIConfigSpace
    param.bitWidth  = width * 8
    param.address   = _pci_address(reg)
    param.value     = value & mask
    return iokitcore.call_struct_method(_connect, _kMethodWrite, param, None)
