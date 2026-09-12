from __future__ import annotations
import ctypes
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

    @property
    def model_id(self) -> int:
        return self.cpu_model_int

    @property
    def stepping(self) -> int:
        return self.cpu_stepping_int


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
                try:
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
                except ValueError:
                    pass
                if seen_family and seen_model and seen_stepping and cpu_name:
                    break
    except (OSError, ValueError):
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


_libc: ctypes.CDLL | None = None


def _libSystem() -> ctypes.CDLL | None:
    global _libc
    if _libc is None:
        try:
            _libc = ctypes.CDLL("/usr/lib/libSystem.B.dylib")
        except (OSError, Exception):
            return None
    return _libc


def _sysctl_str(name: str) -> str:
    try:
        libc = _libSystem()
        if libc is None:
            return ""
        size = ctypes.c_size_t(0)
        if libc.sysctlbyname(name.encode(), None, ctypes.byref(size), None, 0) != 0:
            return ""
        buf = ctypes.create_string_buffer(size.value)
        if libc.sysctlbyname(name.encode(), buf, ctypes.byref(size), None, 0) != 0:
            return ""
        return buf.value.decode(errors="replace").strip()
    except (OSError, Exception):
        return ""


def _sysctl_int(name: str) -> int:
    try:
        libc = _libSystem()
        if libc is None:
            return 0
        val = ctypes.c_uint64(0)
        size = ctypes.c_size_t(ctypes.sizeof(val))
        if libc.sysctlbyname(name.encode(), ctypes.byref(val), ctypes.byref(size), None, 0) != 0:
            return 0
        return int(val.value)
    except (OSError, Exception):
        return 0


def _parse_sysctl() -> tuple[int, int, int, str]:
    try:
        name = _sysctl_str("machdep.cpu.brand_string")
        return (
            _sysctl_int("machdep.cpu.family"),
            _sysctl_int("machdep.cpu.model"),
            _sysctl_int("machdep.cpu.stepping"),
            name,
        )
    except (OSError, Exception):
        return 0, 0, 0, ""


_ARCH_MAP: dict[int, str] = {
    23: "Zen 1 - Zen 2",
    24: "Zen 1 derivative",
    25: "Zen 3 - Zen 4",
    26: "Zen 5 - Zen 6",
    27: "Zen 6",
}


def _resolve_codename(cpu_name: str, cpu_family: int, cpu_model: int) -> tuple[str, str]:
    if "Intel" in cpu_name:
        return "Intel", "Intel"

    arch = _ARCH_MAP.get(cpu_family, "Unknown")
    family = "Unknown"
    name_lower = cpu_name.lower()

    if cpu_family == 23:
        match cpu_model:
            case 1:
                if "threadripper" in name_lower:
                    family = "Threadripper"
                elif "epyc" in name_lower:
                    family = "Naples"
                else:
                    family = "SummitRidge"
            case 8:
                if "threadripper" in name_lower or "colfax" in name_lower:
                    family = "Colfax"
                else:
                    family = "PinnacleRidge"
            case 17 | 18:
                family = "RavenRidge"
            case 24:
                if "raven" in name_lower:
                    family = "RavenRidge2"
                else:
                    family = "Picasso"
            case 32:
                if any(s in cpu_name for s in ("15e", "15Ce", "20e")):
                    family = "Pollock"
                else:
                    family = "Dali"
            case 48:
                family = "Rome"
            case 49:
                family = "CastlePeak"
            case m if 50 <= m <= 63:
                family = "CastlePeak" if "threadripper" in name_lower else "Rome"
            case 80:
                family = "FireFlight"
            case 96:
                family = "Renoir"
            case 104:
                family = "Lucienne"
            case 113:
                family = "Matisse"
            case 144 | 145:
                family = "VanGogh"
            case 160:
                family = "Mendocino"

    elif cpu_family == 24:
        family = "Dhyana"

    elif cpu_family == 25:
        match cpu_model:
            case 1:
                family = "Milan"
            case 8:
                family = "Chagall"
            case 24 if "threadripper" in name_lower:
                family = "StormPeak"
            case m if 16 <= m <= 31:
                family = "StormPeak" if "threadripper" in name_lower else "Genoa"
            case 32 | 33:
                family = "Vermeer"
            case 63 | 64 | 68:
                family = "Rembrandt"
            case 80:
                family = "Cezanne_Barcelo"
            case 97:
                family = "DragonRange" if "hx" in name_lower else "Raphael"
            case 116:
                family = "PhoenixPoint"
            case 117:
                family = "HawkPoint"
            case 120:
                family = "PhoenixPoint2"
            case 124:
                family = "HawkPoint2"
            case m if 144 <= m <= 159:
                family = "Siena"
            case m if 160 <= m <= 175:
                family = "Bergamo"

    elif cpu_family == 26:
        match cpu_model:
            case m if 0 <= m <= 15:
                family = "Turin"
            case m if 16 <= m <= 31:
                family = "TurinDense"
            case 32 | 36:
                family = "StrixPoint"
            case 68:
                family = "FireRange" if "hx" in name_lower else "GraniteRidge"
            case m if (80 <= m <= 95) or "sonoma" in name_lower:
                family = "SonomaValley"
            case 96:
                family = "KrackanPoint"
            case 104:
                family = "KrackanPoint2"
            case 112:
                family = "StrixHalo"
            case m if 128 <= m <= 135:
                family = "Medusa1"
            case m if 136 <= m <= 143:
                family = "OlympicRidge"
            case m if 224 <= m <= 227:
                family = "Medusa2"

    return arch, family


_DESKTOP_FAMILIES: frozenset[str] = frozenset({
    "SummitRidge",
    "Threadripper",
    "Naples",
    "PinnacleRidge",
    "Colfax",
    "Rome",
    "CastlePeak",
    "Matisse",
    "Milan",
    "Chagall",
    "Genoa",
    "Bergamo",
    "Siena",
    "StormPeak",
    "Vermeer",
    "Raphael",
    "Turin",
    "TurinDense",
    "GraniteRidge",
    "OlympicRidge",
    "Dhyana",
})


def _cpu_type(family: str, arch: str) -> str:
    if family in _DESKTOP_FAMILIES:
        return "Amd_Desktop_Cpu"
    if family == "Unknown" or arch in ("Intel", "Unknown"):
        return arch if arch == "Intel" else "Unknown"
    return "Amd_Apu"


def resolve(name: str, cpu_family_int: int, cpu_model_int: int, cpu_stepping_int: int = 0) -> CpuInfo:
    arch, family = _resolve_codename(name, cpu_family_int, cpu_model_int)
    t = _cpu_type(family, arch)
    return CpuInfo(
        name=name,
        arch=arch,
        family=family,
        type=t,
        cpu_family_int=cpu_family_int,
        cpu_model_int=cpu_model_int,
        cpu_stepping_int=cpu_stepping_int,
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
