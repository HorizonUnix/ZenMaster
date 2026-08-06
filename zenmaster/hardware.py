from __future__ import annotations
import os
import platform
from dataclasses import dataclass
from functools import lru_cache


@dataclass
class CpuInfo:
    name: str
    arch: str
    family: str
    type: str
    cpu_family_int: int
    cpu_model_int: int
    cpu_stepping_int: int = 0
    package_type: str = "Unknown"
    ccds: int = 1
    ccxs: int = 1
    cores_per_ccx: int = 8
    physical_cores: int = 8
    logical_cores: int = 16
    svi2_core_address: int = 0x00
    svi2_soc_address: int = 0x00


def _parse_cpuinfo() -> tuple[int, int, int, str]:
    cpu_family = cpu_model = cpu_stepping = 0
    cpu_name = ""
    seen_family = seen_model = seen_stepping = False
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if ":" not in line:
                    continue
                key, _, val = line.partition(":")
                key, val = key.strip(), val.strip()
                if key == "cpu family" and not seen_family:
                    cpu_family = int(val)
                    seen_family = True
                elif key == "model" and not seen_model:
                    cpu_model = int(val)
                    seen_model = True
                elif key == "stepping" and not seen_stepping:
                    cpu_stepping = int(val)
                    seen_stepping = True
                elif key == "model name" and not cpu_name:
                    cpu_name = val
                if seen_family and seen_model and seen_stepping and cpu_name:
                    break
    except OSError:
        pass
    return cpu_family, cpu_model, cpu_stepping, cpu_name


def _parse_processor_identifier() -> tuple[int, int, int, str]:
    identifier = os.environ.get("PROCESSOR_IDENTIFIER", "")
    words = identifier.split()
    cpu_family = cpu_model = cpu_stepping = 0
    try:
        fi = words.index("Family") + 1
        mi = words.index("Model") + 1
        cpu_family = int(words[fi])
        cpu_model = int(words[mi].rstrip(","))
    except (ValueError, IndexError):
        pass
    try:
        si = words.index("Stepping") + 1
        cpu_stepping = int(words[si].rstrip(","))
    except (ValueError, IndexError):
        pass

    cpu_name = ""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
        )
        cpu_name = winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
        winreg.CloseKey(key)
    except Exception:
        pass
    if not cpu_name:
        cpu_name = identifier
    return cpu_family, cpu_model, cpu_stepping, cpu_name


_libc = None


def _libSystem():
    global _libc
    if _libc is None:
        import ctypes
        _libc = ctypes.CDLL("/usr/lib/libSystem.B.dylib")
        fn = getattr(_libc, "sysctlbyname", None)
        if fn and hasattr(fn, "restype"):
            try:
                fn.restype = ctypes.c_int
                fn.argtypes = [
                    ctypes.c_char_p,
                    ctypes.c_void_p,
                    ctypes.POINTER(ctypes.c_size_t),
                    ctypes.c_void_p,
                    ctypes.c_size_t,
                ]
            except AttributeError:
                pass
    return _libc


def _sysctl_str(name: str) -> str:
    import ctypes
    libc = _libSystem()
    size = ctypes.c_size_t(0)
    if libc.sysctlbyname(name.encode(), None, ctypes.byref(size), None, 0) != 0:
        return ""
    buf = ctypes.create_string_buffer(size.value)
    if libc.sysctlbyname(name.encode(), buf, ctypes.byref(size), None, 0) != 0:
        return ""
    return buf.value.decode(errors="replace").strip()


def _sysctl_int(name: str) -> int:
    import ctypes
    libc = _libSystem()
    val  = ctypes.c_uint64(0)
    size = ctypes.c_size_t(ctypes.sizeof(val))
    if libc.sysctlbyname(name.encode(), ctypes.byref(val), ctypes.byref(size), None, 0) != 0:
        return 0
    return int(val.value)


def _parse_sysctl() -> tuple[int, int, int, str]:
    name = _sysctl_str("machdep.cpu.brand_string")
    return (
        _sysctl_int("machdep.cpu.family"),
        _sysctl_int("machdep.cpu.model"),
        _sysctl_int("machdep.cpu.stepping"),
        name,
    )


def _resolve_codename(cpu_name: str, cpu_family: int, cpu_model: int) -> tuple[str, str]:
    if "Intel" in cpu_name:
        return "Intel", "Intel"

    arch = family = "Unknown"

    if cpu_family == 23:
        arch = "Zen 1 - Zen 2"
        match cpu_model:
            case 1:         family = "Naples" if "EPYC" in cpu_name else ("Whitehaven" if "Threadripper" in cpu_name else "SummitRidge")
            case 8:         family = "Colfax" if ("EPYC" in cpu_name or "Threadripper" in cpu_name) else "PinnacleRidge"
            case 17 | 18:   family = "RavenRidge"
            case 24:        family = "Picasso"
            case 32:        family = "Pollock" if any(s in cpu_name for s in ("15e", "15Ce", "20e", "3015e", "3020e", "3150e", "3050e", "Pollock")) else "Dali"
            case 49:        family = "Rome" if "EPYC" in cpu_name else "CastlePeak"
            case 80:        family = "FireFlight"
            case 96:        family = "Renoir"
            case 104:       family = "Lucienne"
            case 113:       family = "Matisse"
            case 144 | 145: family = "VanGogh"
            case 152:       family = "Mero"
            case 160:       family = "Mendocino"

    elif cpu_family == 25:
        arch = "Zen 3 - Zen 4"
        match cpu_model:
            case 1:         family = "Milan"
            case 8:         family = "Chagall"
            case 17:        family = "Genoa"
            case 24:        family = "StormPeak"
            case 33:        family = "Vermeer"
            case 64 | 68:   family = "Rembrandt"
            case 80:        family = "Cezanne_Barcelo"
            case 97:        family = "DragonRange" if "HX" in cpu_name else "Raphael"
            case 116:       family = "PhoenixPoint"
            case 120:       family = "PhoenixPoint2"
            case 117:       family = "HawkPoint"
            case 124:       family = "HawkPoint2"
            case 160:       family = "Bergamo"

    elif cpu_family == 26:
        arch = "Zen 5 - Zen 6"
        match cpu_model:
            case 2:         family = "Turin"
            case 8:         family = "ShimadaPeak"
            case 17:        family = "TurinD"
            case 32 | 36:   family = "StrixPoint"
            case 68:        family = "FireRange" if "HX" in cpu_name else "GraniteRidge"
            case 96:        family = "KrackanPoint"
            case 104:       family = "KrackanPoint2"
            case 112:       family = "StrixHalo"

    return arch, family


_DESKTOP_FAMILIES = {
    "SummitRidge", "PinnacleRidge", "Matisse",
    "Vermeer", "Raphael", "GraniteRidge", "ShimadaPeak",
    "Whitehaven", "Colfax", "CastlePeak", "Chagall", "StormPeak",
}

_SERVER_FAMILIES = {
    "Naples", "Rome", "Milan", "Genoa", "Bergamo", "Turin", "TurinD",
}


def _cpu_type(family: str, arch: str) -> str:
    if family in _SERVER_FAMILIES:
        return "Amd_Server_Cpu"
    if family in _DESKTOP_FAMILIES:
        return "Amd_Desktop_Cpu"
    if arch in ("Intel", "Unknown"):
        return arch
    return "Amd_Apu"


def _infer_topology(family: str) -> tuple[str, int, int, int, int, int]:
    try:
        threads = os.cpu_count() or 16
    except Exception:
        threads = 16
    cores = max(1, threads // 2)

    if family in ("SummitRidge", "PinnacleRidge", "Matisse", "Vermeer", "Whitehaven", "Colfax"):
        pkg = "AM4/TRX"
        ccds = max(1, cores // 8)
        ccxs = ccds * (2 if family in ("SummitRidge", "PinnacleRidge", "Whitehaven", "Colfax") else 1)
        cores_per_ccx = max(1, cores // ccxs)
    elif family in ("Raphael", "GraniteRidge"):
        pkg = "AM5"
        ccds = max(1, cores // 8)
        ccxs = ccds
        cores_per_ccx = max(1, cores // ccxs)
    elif family in _SERVER_FAMILIES or family in ("CastlePeak", "Chagall", "StormPeak", "ShimadaPeak"):
        pkg = "SP3/SP5/SP6/TRX"
        ccds = max(1, cores // 8)
        ccxs = ccds
        cores_per_ccx = 8
    else:
        pkg = "FP6/FP7/FP8/AM5"
        ccds = 1
        ccxs = 1
        cores_per_ccx = cores

    return pkg, ccds, ccxs, cores_per_ccx, cores, threads


def resolve(name: str, cpu_family_int: int, cpu_model_int: int, cpu_stepping_int: int = 0) -> CpuInfo:
    arch, family = _resolve_codename(name, cpu_family_int, cpu_model_int)
    t = _cpu_type(family, arch)
    pkg, ccds, ccxs, c_per_ccx, p_cores, l_cores = _infer_topology(family)

    svi2_core = 0x00
    svi2_soc = 0x01
    if family in ("Raphael", "GraniteRidge", "PhoenixPoint", "StrixPoint"):
        svi2_core = 0x20
        svi2_soc = 0x21

    return CpuInfo(
        name=name,
        arch=arch,
        family=family,
        type=t,
        cpu_family_int=cpu_family_int,
        cpu_model_int=cpu_model_int,
        cpu_stepping_int=cpu_stepping_int,
        package_type=pkg,
        ccds=ccds,
        ccxs=ccxs,
        cores_per_ccx=c_per_ccx,
        physical_cores=p_cores,
        logical_cores=l_cores,
        svi2_core_address=svi2_core,
        svi2_soc_address=svi2_soc,
    )


@lru_cache(maxsize=1)
def detect() -> CpuInfo:
    system = platform.system()
    if system == "Windows":
        cpu_family_int, cpu_model_int, cpu_stepping_int, name = _parse_processor_identifier()
    elif system == "Darwin":
        cpu_family_int, cpu_model_int, cpu_stepping_int, name = _parse_sysctl()
    else:
        cpu_family_int, cpu_model_int, cpu_stepping_int, name = _parse_cpuinfo()
    return resolve(name, cpu_family_int, cpu_model_int, cpu_stepping_int)

