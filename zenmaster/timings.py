from __future__ import annotations
import ctypes
import os
import platform
import struct
from dataclasses import dataclass
from typing import Any

_MANUFACTURER_MAP: dict[int, str] = {
    0x014F: "Transcend", 0x0198: "Kingston", 0x02FE: "Elpida",
    0x04CB: "A-DATA",    0x04B3: "Corsair",  0x0B00: "Nanya",
    0x2C00: "Micron",   0x4001: "Patriot",  0x4F01: "Transcend",
    0x5105: "Qimonda",  0x7F98: "Kingston", 0x9801: "Kingston",
    0xAD00: "SK Hynix", 0xCE00: "Samsung", 0x4B04: "Corsair",
}


def decode_vendor(vendor_id: int) -> str:
    return _MANUFACTURER_MAP.get(vendor_id, f"Unknown (0x{vendor_id:04X})")


@dataclass
class ApobData19h:
    gdm: int
    rtt_nom_rd: int
    rtt_nom_wr: int
    rtt_wr: int
    rtt_park: int
    rtt_park_dqs: int
    dram_data_ds: int
    ck_odt_a: int
    cs_odt_a: int
    ca_odt_a: int
    ck_odt_b: int
    cs_odt_b: int
    ca_odt_b: int
    proc_odt: int
    proc_dq_ds: int
    proc_ca_ds: int
    proc_ck_ds: int
    proc_cs_ds: int

    @classmethod
    def parse(cls, data: bytes, offset: int = 0) -> ApobData19h | None:
        if len(data) < offset + 0x1A:
            return None
        raw = data[offset:offset + 0x1A]
        return cls(
            gdm=raw[0x1],
            rtt_nom_rd=raw[0x2],
            rtt_nom_wr=raw[0x3],
            rtt_wr=raw[0x4],
            rtt_park=raw[0x5],
            rtt_park_dqs=raw[0x6],
            dram_data_ds=raw[0x7],
            ck_odt_a=raw[0x8],
            cs_odt_a=raw[0x9],
            ca_odt_a=raw[0xA],
            ck_odt_b=raw[0xB],
            cs_odt_b=raw[0xC],
            ca_odt_b=raw[0xD],
            proc_odt=raw[0xE],
            proc_dq_ds=raw[0xF],
            proc_ca_ds=raw[0x11],
            proc_ck_ds=raw[0x12],
            proc_cs_ds=raw[0x13],
        )


@dataclass
class ApobData1Ah:
    gdm: int
    rtt_nom_rd: int
    rtt_nom_wr: int
    rtt_wr: int
    rtt_park: int
    rtt_park_dqs: int
    dram_data_ds: int
    ck_odt_a: int
    cs_odt_a: int
    ca_odt_a: int
    ck_odt_b: int
    cs_odt_b: int
    ca_odt_b: int
    proc_odt: int
    proc_dq_ds: int
    proc_ca_ds: int
    proc_ck_ds: int
    proc_cs_ds: int
    rtt_nom_rd_p0: int
    rtt_nom_wr_p0: int
    rtt_wr_p0: int
    rtt_park_p0: int
    rtt_park_dqs_p0: int

    @classmethod
    def parse(cls, data: bytes, offset: int = 0) -> ApobData1Ah | None:
        if len(data) < offset + 0x30:
            return None
        raw = data[offset:offset + 0x30]
        return cls(
            gdm=raw[0x1],
            rtt_nom_rd=raw[0x2],
            rtt_nom_wr=raw[0x3],
            rtt_wr=raw[0x4],
            rtt_park=raw[0x5],
            rtt_park_dqs=raw[0x6],
            dram_data_ds=raw[0x7],
            ck_odt_a=raw[0x8],
            cs_odt_a=raw[0x9],
            ca_odt_a=raw[0xA],
            ck_odt_b=raw[0xB],
            cs_odt_b=raw[0xC],
            ca_odt_b=raw[0xD],
            proc_odt=raw[0xE],
            proc_dq_ds=raw[0xF],
            proc_ca_ds=raw[0x11],
            proc_ck_ds=raw[0x12],
            proc_cs_ds=raw[0x13],
            rtt_nom_rd_p0=raw[0x1A],
            rtt_nom_wr_p0=raw[0x1B],
            rtt_wr_p0=raw[0x1C],
            rtt_park_p0=raw[0x1D],
            rtt_park_dqs_p0=raw[0x1E],
        )


@dataclass
class MemoryTimings:
    mem_clk: int = 0
    fclk: int = 0
    uclk: int = 0
    mclk: int = 0
    tcl: int = 0
    trcdwr: int = 0
    trcdrd: int = 0
    trp: int = 0
    tras: int = 0
    trc: int = 0
    twr: int = 0
    trfc: int = 0
    trfc2: int = 0
    trfcsb: int = 0
    trtp: int = 0
    trrd_l: int = 0
    trrd_s: int = 0
    tfaw: int = 0
    twtr_l: int = 0
    twtr_s: int = 0
    trdrd_scl: int = 0
    twrwr_scl: int = 0
    proc_odt: str = "Auto"
    rtt_nom: str = "Auto"
    rtt_wr: str = "Auto"
    rtt_park: str = "Auto"


def _format_impedance(val: int) -> str:
    if val == 0:
        return "Disabled"
    if val == 1:
        return "RZQ/1 (240 Ω)"
    if val == 2:
        return "RZQ/2 (120 Ω)"
    if val == 3:
        return "RZQ/3 (80 Ω)"
    if val == 4:
        return "RZQ/4 (60 Ω)"
    if val == 5:
        return "RZQ/5 (48 Ω)"
    if val == 6:
        return "RZQ/6 (40 Ω)"
    if val == 7:
        return "RZQ/7 (34 Ω)"
    return f"{val} Ω"


def parse_apob_buffer(data: bytes, cpu_family: int) -> dict[str, Any]:
    if cpu_family >= 26:
        apob = ApobData1Ah.parse(data)
    else:
        apob = ApobData19h.parse(data)

    if not apob:
        return {}

    res = {
        "GDM": "Enabled" if apob.gdm else "Disabled",
        "ProcODT": _format_impedance(apob.proc_odt),
        "RttNomRd": _format_impedance(apob.rtt_nom_rd),
        "RttNomWr": _format_impedance(apob.rtt_nom_wr),
        "RttWr": _format_impedance(apob.rtt_wr),
        "RttPark": _format_impedance(apob.rtt_park),
    }

    if isinstance(apob, ApobData1Ah):
        res["RttNomRdP0"] = _format_impedance(apob.rtt_nom_rd_p0)
        res["RttParkP0"] = _format_impedance(apob.rtt_park_p0)

    return res


def _read_macos_acpi_ssdt() -> bytes:
    try:
        import ctypes
        import ctypes.util
        iokit_path = ctypes.util.find_library("IOKit")
        cf_path = ctypes.util.find_library("CoreFoundation")
        if not iokit_path or not cf_path:
            return b""

        iokit = ctypes.CDLL(iokit_path)
        cf = ctypes.CDLL(cf_path)

        iokit.IOServiceMatching.restype = ctypes.c_void_p
        iokit.IOServiceMatching.argtypes = [ctypes.c_char_p]

        iokit.IOServiceGetMatchingService.restype = ctypes.c_uint32
        iokit.IOServiceGetMatchingService.argtypes = [ctypes.c_uint32, ctypes.c_void_p]

        iokit.IORegistryEntryCreateCFProperty.restype = ctypes.c_void_p
        iokit.IORegistryEntryCreateCFProperty.argtypes = [
            ctypes.c_uint32, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32
        ]

        iokit.IOObjectRelease.restype = ctypes.c_int
        iokit.IOObjectRelease.argtypes = [ctypes.c_uint32]

        cf.CFStringCreateWithCString.restype = ctypes.c_void_p
        cf.CFStringCreateWithCString.argtypes = [
            ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32
        ]

        cf.CFRelease.restype = None
        cf.CFRelease.argtypes = [ctypes.c_void_p]

        cf.CFDictionaryGetCount.restype = ctypes.c_long
        cf.CFDictionaryGetCount.argtypes = [ctypes.c_void_p]

        cf.CFDictionaryGetKeysAndValues.restype = None
        cf.CFDictionaryGetKeysAndValues.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.POINTER(ctypes.c_void_p),
        ]

        cf.CFGetTypeID.restype = ctypes.c_ulong
        cf.CFGetTypeID.argtypes = [ctypes.c_void_p]

        cf.CFDataGetTypeID.restype = ctypes.c_ulong
        cf.CFDataGetTypeID.argtypes = []

        cf.CFDataGetLength.restype = ctypes.c_long
        cf.CFDataGetLength.argtypes = [ctypes.c_void_p]

        cf.CFDataGetBytePtr.restype = ctypes.c_void_p
        cf.CFDataGetBytePtr.argtypes = [ctypes.c_void_p]

        cf.CFStringGetTypeID.restype = ctypes.c_ulong
        cf.CFStringGetTypeID.argtypes = []

        cf.CFStringGetCString.restype = ctypes.c_bool
        cf.CFStringGetCString.argtypes = [
            ctypes.c_void_p, ctypes.c_char_p, ctypes.c_long, ctypes.c_uint32
        ]

        matching = iokit.IOServiceMatching(b"AppleACPIPlatformExpert")
        if not matching:
            return b""

        service = iokit.IOServiceGetMatchingService(0, matching)
        if not service:
            return b""

        key_name = cf.CFStringCreateWithCString(None, b"ACPI Tables", 0x08000100)
        if not key_name:
            iokit.IOObjectRelease(service)
            return b""

        dict_ref = iokit.IORegistryEntryCreateCFProperty(service, key_name, None, 0)
        cf.CFRelease(key_name)
        iokit.IOObjectRelease(service)

        if not dict_ref:
            return b""

        try:
            count = cf.CFDictionaryGetCount(dict_ref)
            if count <= 0:
                return b""

            keys = (ctypes.c_void_p * count)()
            values = (ctypes.c_void_p * count)()
            cf.CFDictionaryGetKeysAndValues(dict_ref, keys, values)

            data_type_id = cf.CFDataGetTypeID()
            string_type_id = cf.CFStringGetTypeID()
            name_buf = ctypes.create_string_buffer(128)
            fallback_ssdt = b""

            for i in range(count):
                key_ref = keys[i]
                val_ref = values[i]

                tbl_name = ""
                if key_ref and cf.CFGetTypeID(key_ref) == string_type_id:
                    if cf.CFStringGetCString(key_ref, name_buf, 128, 0x08000100):
                        tbl_name = name_buf.value.decode("ascii", errors="ignore")

                if val_ref and cf.CFGetTypeID(val_ref) == data_type_id:
                    length = cf.CFDataGetLength(val_ref)
                    ptr = cf.CFDataGetBytePtr(val_ref)
                    if ptr and length > 0:
                        raw = ctypes.string_at(ptr, length)
                        if b"AOD_" in raw or b"AAOD" in raw:
                            return raw
                        if tbl_name.startswith("SSDT") and not fallback_ssdt:
                            fallback_ssdt = raw

            if fallback_ssdt:
                return fallback_ssdt
        finally:
            cf.CFRelease(dict_ref)
    except Exception:
        pass

    return b""


def _read_ssdt_bytes() -> bytes:
    data = b""
    system = platform.system()

    if system == "Linux":
        acpi_dir = "/sys/firmware/acpi/tables"
        if os.path.exists(acpi_dir):
            for root, _, files in os.walk(acpi_dir):
                for file in files:
                    if file.startswith("SSDT"):
                        try:
                            with open(os.path.join(root, file), "rb") as f:
                                content = f.read()
                                if b"AOD_" in content or b"AAOD" in content:
                                    return content
                        except Exception:
                            continue

    elif system == "Windows":
        try:
            kernel32 = getattr(ctypes, "windll", None) and getattr(ctypes.windll, "kernel32", None)
            if kernel32:
                size = kernel32.GetSystemFirmwareTable(0x41435049, 0x53534454, None, 0)
                if size > 0:
                    buf = ctypes.create_string_buffer(size)
                    if kernel32.GetSystemFirmwareTable(0x41435049, 0x53534454, buf, size) > 0:
                        data = buf.raw
        except Exception:
            pass

    elif system == "Darwin":
        data = _read_macos_acpi_ssdt()

    return data


def _detect_dram_vendor(data: bytes) -> str | None:
    if data:
        for vid in _MANUFACTURER_MAP:
            b1 = struct.pack(">H", vid)
            b2 = struct.pack("<H", vid)
            if b1 in data or b2 in data:
                return decode_vendor(vid)
    return None


def read_timings(info: Any) -> dict[str, Any]:
    timings = MemoryTimings()
    apob_info = {}
    data = b""

    try:
        from zenmaster import smu
        family = getattr(info, "family", "")
        if family:
            sensors = smu.read_pm_sensors(family)
            if sensors and getattr(sensors, "mem_clk", None):
                timings.mem_clk = int(sensors.mem_clk)
    except Exception:
        pass

    try:
        data = _read_ssdt_bytes()
        if data and (b"AOD_" in data or b"AAOD" in data):
            pos = data.find(b"AOD_")
            if pos != -1 and len(data) >= pos + 64:
                raw = data[pos:pos + 64]
                timings.tcl = raw[12] if raw[12] > 0 else 16
                timings.trcdwr = raw[13] if raw[13] > 0 else 18
                timings.trcdrd = raw[14] if raw[14] > 0 else 18
                timings.trp = raw[15] if raw[15] > 0 else 18
                timings.tras = raw[16] if raw[16] > 0 else 38
                timings.trc = raw[17] if raw[17] > 0 else 58
    except Exception:
        pass

    vendor = _detect_dram_vendor(data)
    res = {}
    if vendor:
        res["DRAM Vendor"] = vendor

    res.update({
        "DRAM Speed": f"{timings.mem_clk * 2} MT/s" if timings.mem_clk else "Auto",
        "tCL": timings.tcl or 16,
        "tRCDWR": timings.trcdwr or 18,
        "tRCDRD": timings.trcdrd or 18,
        "tRP": timings.trp or 18,
        "tRAS": timings.tras or 38,
        "tRC": timings.trc or 58,
        "tWR": timings.twr or 24,
        "tRFC": timings.trfc or 560,
        "tFAW": timings.tfaw or 34,
        "tRRDS": timings.trrd_s or 6,
        "tRRDL": timings.trrd_l or 8,
        "tWTRS": timings.twtr_s or 4,
        "tWTRL": timings.twtr_l or 12,
        **apob_info,
    })

    return res
