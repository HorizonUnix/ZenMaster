from __future__ import annotations
import ctypes

KERN_SUCCESS = 0

_iokit = None
_task_self = 0


def load():
    global _iokit, _task_self
    if _iokit is not None:
        return _iokit
    try:
        iokit = ctypes.CDLL("/System/Library/Frameworks/IOKit.framework/IOKit")
        libc  = ctypes.CDLL("/usr/lib/libSystem.B.dylib")
    except OSError:
        return None

    iokit.IOServiceMatching.restype  = ctypes.c_void_p
    iokit.IOServiceMatching.argtypes = [ctypes.c_char_p]
    iokit.IOServiceGetMatchingService.restype  = ctypes.c_uint
    iokit.IOServiceGetMatchingService.argtypes = [ctypes.c_uint, ctypes.c_void_p]
    iokit.IOServiceOpen.restype  = ctypes.c_int
    iokit.IOServiceOpen.argtypes = [ctypes.c_uint, ctypes.c_uint, ctypes.c_uint,
                                    ctypes.POINTER(ctypes.c_uint)]
    iokit.IOServiceClose.restype  = ctypes.c_int
    iokit.IOServiceClose.argtypes = [ctypes.c_uint]
    iokit.IOObjectRelease.restype  = ctypes.c_int
    iokit.IOObjectRelease.argtypes = [ctypes.c_uint]
    iokit.IOConnectCallStructMethod.restype  = ctypes.c_int
    iokit.IOConnectCallStructMethod.argtypes = [
        ctypes.c_uint, ctypes.c_uint32,
        ctypes.c_void_p, ctypes.c_size_t,
        ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t),
    ]

    _iokit = iokit
    _task_self = ctypes.c_uint.in_dll(libc, "mach_task_self_").value
    return _iokit


def task_self() -> int:
    return _task_self


def service_available(service: bytes) -> bool:
    iokit = load()
    if iokit is None:
        return False
    matching = iokit.IOServiceMatching(service)
    if not matching:
        return False
    handle = iokit.IOServiceGetMatchingService(0, matching)
    if not handle:
        return False
    iokit.IOObjectRelease(handle)
    return True


def open_service(service: bytes, client_type: int = 0) -> int | None:
    iokit = load()
    if iokit is None:
        return None
    matching = iokit.IOServiceMatching(service)
    if not matching:
        return None
    handle = iokit.IOServiceGetMatchingService(0, matching)
    if not handle:
        return None
    conn = ctypes.c_uint(0)
    err = iokit.IOServiceOpen(handle, _task_self, client_type, ctypes.byref(conn))
    iokit.IOObjectRelease(handle)
    if err != KERN_SUCCESS or not conn.value:
        return None
    return conn.value


def close_service(connect: int) -> None:
    if _iokit is not None:
        _iokit.IOServiceClose(connect)


def call_struct_method(connect: int, selector: int, in_struct, out_struct) -> bool:
    iokit = load()
    if iokit is None:
        return False
    if out_struct is None:
        outlen  = ctypes.c_size_t(0)
        out_ptr = None
    else:
        outlen  = ctypes.c_size_t(ctypes.sizeof(out_struct))
        out_ptr = ctypes.byref(out_struct)
    err = iokit.IOConnectCallStructMethod(
        connect, selector,
        ctypes.byref(in_struct), ctypes.sizeof(in_struct),
        out_ptr, ctypes.byref(outlen),
    )
    return err == KERN_SUCCESS
