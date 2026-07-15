from __future__ import annotations
import math
import struct
from dataclasses import dataclass

_VRM_V1 = {0x001E0001, 0x001E0002, 0x001E0003, 0x001E0004,
            0x001E0005, 0x001E000A, 0x001E0101}
_VRM_V2 = {0x00370000, 0x00370001, 0x00370002, 0x00370003, 0x00370004, 0x00370005,
            0x00400001, 0x00400002, 0x00400003, 0x00400004, 0x00400005,
            0x00450004, 0x00450005,
            0x004C0006, 0x004C0007, 0x004C0008, 0x004C0009}
_VRM_V3 = {0x005D0008, 0x005D0009, 0x005D000B, 0x00650005}

_TCTL_V1 = _VRM_V1 | {0x0064020C}
_TCTL_V2 = {0x00370000, 0x00370001, 0x00370002, 0x00370003, 0x00370004, 0x00370005,
             0x003F0000, 0x00400001, 0x00400002, 0x00400003, 0x00400004, 0x00400005,
             0x00450004, 0x00450005,
             0x004C0006, 0x004C0007, 0x004C0008, 0x004C0009,
             0x005D0008, 0x005D0009, 0x005D000B, 0x00650005}

_APU_SLOW_VERS = _VRM_V2 | {0x003F0000, 0x005D0008, 0x005D0009, 0x005D000B, 0x0064020C, 0x00650005}

_SKIN_APU_VERS = {0x00370000, 0x00370001, 0x00370002, 0x00370003, 0x00370004, 0x00370005,
                  0x003F0000, 0x00400001, 0x00400002, 0x00400003, 0x00400004, 0x00400005,
                  0x00450004, 0x00450005,
                  0x004C0006, 0x004C0007, 0x004C0008, 0x004C0009,
                  0x005D0008, 0x005D0009, 0x005D000B, 0x0064020C}

_SKIN_DGPU_V2 = {0x00370000, 0x00370001, 0x00370002, 0x00370003, 0x00370004, 0x00370005,
                 0x00400001, 0x00400002, 0x00400003, 0x00400004, 0x00400005,
                 0x00450004, 0x00450005,
                 0x004C0006, 0x004C0007, 0x004C0008, 0x004C0009, 0x0064020C}
_SKIN_DGPU_V3 = {0x005D0008, 0x005D0009, 0x005D000B}

_STAPM_TIME: dict[int, int] = {
    0x001E0002: 0x564, 0x001E0003: 0x55C, 0x001E0004: 0x5E0, 0x001E0005: 0x5E0,
    0x001E000A: 0x5E0, 0x001E0101: 0x5E0,
    0x00370000: 0x768, 0x00370001: 0x858, 0x00370002: 0x860,
    0x00370003: 0x880, 0x00370004: 0x880, 0x00370005: 0x89C,
    0x00400001: 0x8E4, 0x00400002: 0x8FC, 0x00400003: 0x920,
    0x00400004: 0x918, 0x00400005: 0x918,
    0x004C0006: 0x918, 0x004C0007: 0x918, 0x004C0008: 0x918, 0x004C0009: 0x918,
    0x005D0008: 0x9BC, 0x005D0009: 0x9BC, 0x005D000B: 0x9BC,
    0x00650005: 0x90C,
}
_SLOW_TIME: dict[int, int] = {
    0x001E0002: 0x568, 0x001E0003: 0x560, 0x001E0004: 0x5E4, 0x001E0005: 0x5E4,
    0x001E000A: 0x5E4, 0x001E0101: 0x5E4,
    0x00370000: 0x76C, 0x00370001: 0x85C, 0x00370002: 0x864,
    0x00370003: 0x884, 0x00370004: 0x884, 0x00370005: 0x8A0,
    0x00400001: 0x8E8, 0x00400002: 0x900, 0x00400003: 0x924,
    0x00400004: 0x91C, 0x00400005: 0x91C,
    0x004C0006: 0x91C, 0x004C0007: 0x91C, 0x004C0008: 0x91C, 0x004C0009: 0x91C,
    0x005D0008: 0x9C0, 0x005D0009: 0x9C0, 0x005D000B: 0x9C0,
    0x00650005: 0x910,
}
_CCLK_SETPOINT: dict[int, int] = {
    0x001E0001: 0x98, 0x001E0002: 0x98, 0x001E0003: 0x98, 0x001E0004: 0x98,
    0x001E0005: 0x98, 0x001E000A: 0x98, 0x001E0101: 0x98,
    0x00370000: 0xFC, 0x00370001: 0xFC, 0x00370002: 0xFC,
    0x00370003: 0xFC, 0x00370004: 0xFC, 0x00370005: 0xFC,
    0x00400001: 0x100, 0x00400002: 0x100, 0x00400003: 0x100,
    0x00400004: 0x100, 0x00400005: 0x100,
    0x005D0008: 0xD0, 0x005D0009: 0xD0, 0x005D000B: 0xD0,
}
_CCLK_BUSY: dict[int, int] = {
    0x001E0001: 0x9C, 0x001E0002: 0x9C, 0x001E0003: 0x9C, 0x001E0004: 0x9C,
    0x001E0005: 0x9C, 0x001E000A: 0x9C, 0x001E0101: 0x9C,
    0x00370000: 0x100, 0x00370001: 0x100, 0x00370002: 0x100,
    0x00370003: 0x100, 0x00370004: 0x100, 0x00370005: 0x100,
    0x00400001: 0x104, 0x00400002: 0x104, 0x00400003: 0x104,
    0x00400004: 0x104, 0x00400005: 0x104,
    0x005D0008: 0xCC, 0x005D0009: 0xCC, 0x005D000B: 0xCC,
}


_SOCKET_POWER: dict[int, int] = {
    0x00370000: 0x98, 0x00370001: 0x98, 0x00370002: 0x98, 0x00370003: 0x98,
    0x00370004: 0x98, 0x00370005: 0x98,
    0x00400001: 0x98, 0x00400002: 0x98, 0x00400003: 0x98,
    0x00400004: 0x98, 0x00400005: 0x98,
    0x003F0000: 0xA8,
    0x005D0008: 0xD0, 0x005D0009: 0xD0, 0x005D000B: 0xD0,
}
_GFX_CLK: dict[int, int] = {
    0x00370000: 0x5B4, 0x00370001: 0x5B4, 0x00370002: 0x5B4, 0x00370003: 0x5B4,
    0x00370004: 0x5B4, 0x00370005: 0x5D0,
    0x00400001: 0x60C, 0x00400002: 0x624, 0x00400003: 0x644,
    0x00400004: 0x648, 0x00400005: 0x648,
    0x003F0000: 0x388,
    0x005D0008: 0x4C0, 0x005D0009: 0x4C0, 0x005D000B: 0x4C0,
    0x00650005: 0x4C0, 0x00650007: 0x4C0,
    0x0064020C: 0x558,
}
_GFX_TEMP: dict[int, int] = {
    0x00370000: 0x5AC, 0x00370001: 0x5AC, 0x00370002: 0x5AC, 0x00370003: 0x5AC,
    0x00370004: 0x5AC, 0x00370005: 0x5C8,
    0x00400001: 0x604, 0x00400002: 0x61C, 0x00400003: 0x63C,
    0x00400004: 0x640, 0x00400005: 0x640,
    0x003F0000: 0x380,
    0x005D0008: 0x4B8, 0x005D0009: 0x4B8, 0x005D000B: 0x4B8,
    0x00650005: 0x4B8, 0x00650007: 0x4B8,
    0x0064020C: 0x550,
}
_MEM_CLK: dict[int, int] = {
    0x00370000: 0x5D4, 0x00370001: 0x5D4, 0x00370002: 0x5D4, 0x00370003: 0x5D4,
    0x00370004: 0x5D4, 0x00370005: 0x5F0,
    0x003F0000: 0x3C4,
    0x00400004: 0x66C, 0x00400005: 0x66C,
    0x005D0008: 0x4EC, 0x005D0009: 0x4EC, 0x005D000B: 0x4EC,
    0x00650005: 0x4EC, 0x00650007: 0x4EC,
}
_GFX_POWER: dict[int, int] = {
    0x00620105: 0x1AC,
    0x005D0008: 0x4B4, 0x005D0009: 0x4B4, 0x005D000B: 0x4B4,
    0x00650005: 0x4B4, 0x00650007: 0x4B4,
    0x0064020C: 0x54C,
}
_GFX_VOLT: dict[int, int] = {
    0x00370000: 0x5A8, 0x00370001: 0x5A8, 0x00370002: 0x5A8, 0x00370003: 0x5A8,
    0x00370004: 0x5A8, 0x00370005: 0x5C4,
    0x00400001: 0x600, 0x00400002: 0x618, 0x00400003: 0x638,
    0x00400004: 0x63C, 0x00400005: 0x63C,
    0x003F0000: 0x37C,
    0x0064020C: 0x54C,
}


_SOC_POWER = {
    0x00370000: 0x1A0, 0x00370001: 0x1A0, 0x00370002: 0x1A0, 0x00370003: 0x1A0,
    0x00370004: 0x1A0, 0x00370005: 0x1A0, 0x003F0000: 0x1A8, 0x00400004: 0x1A4,
    0x00400005: 0x1A4, 0x00620105: 0x54,
}
_SOC_VOLT = {
    0x00540104: 0xE0, 0x00540004: 0xE0, 0x00620105: 0x43C, 0x00620205: 0xE8,
    0x00240903: 0xB0, 0x00370000: 0x198, 0x00370001: 0x198, 0x00370002: 0x198,
    0x00370003: 0x198, 0x00370004: 0x198, 0x00370005: 0x198, 0x003F0000: 0x1A0,
    0x00400004: 0x19C, 0x00400005: 0x19C,
}
_FCLK = {
    0x00540104: 0x1A4, 0x00540004: 0x1A4, 0x00620105: 0x11C, 0x00620205: 0x1C4,
    0x00240903: 0xC0, 0x00370000: 0x5CC, 0x00370001: 0x5CC, 0x00370002: 0x5CC,
    0x00370003: 0x5CC, 0x00370004: 0x5CC, 0x00370005: 0x5E8, 0x003F0000: 0x3C5,
    0x00400004: 0x664, 0x00400005: 0x664, 0x005D0008: 0x4E0, 0x005D0009: 0x4E0,
    0x005D000B: 0x4E0, 0x00650005: 0x4E0, 0x00650007: 0x4E0,
}
_L3_CLK = {
    0x00370000: 0x568, 0x00370001: 0x568, 0x00370002: 0x568, 0x00370003: 0x568,
    0x00370004: 0x568, 0x00370005: 0x584, 0x003F0000: 0x35C, 0x00400004: 0x614,
    0x00400005: 0x614,
}
_L3_LOGIC = {
    0x00370000: 0x540, 0x00370001: 0x540, 0x00370002: 0x540, 0x00370003: 0x540,
    0x00370004: 0x540, 0x00370005: 0x55C, 0x003F0000: 0x348, 0x00400004: 0x600,
    0x00400005: 0x600,
}
_L3_VDDM = {
    0x00370000: 0x548, 0x00370001: 0x548, 0x00370002: 0x548, 0x00370003: 0x548,
    0x00370004: 0x548, 0x00370005: 0x564, 0x003F0000: 0x34C, 0x00400004: 0x604,
    0x00400005: 0x604,
}
_L3_TEMP = {
    0x00620105: 0x4A8, 0x00370000: 0x550, 0x00370001: 0x550, 0x00370002: 0x550,
    0x00370003: 0x550, 0x00370004: 0x550, 0x00370005: 0x56C, 0x003F0000: 0x350,
    0x00400004: 0x608, 0x00400005: 0x608,
}
_PSI0_CURRENT = {
    0x001E0001: 0x40, 0x001E0002: 0x40, 0x001E0003: 0x40, 0x001E0004: 0x40,
    0x001E0005: 0x40, 0x001E000A: 0x40, 0x001E0101: 0x40, 0x00370000: 0x78,
    0x00370001: 0x78, 0x00370002: 0x78, 0x00370003: 0x78, 0x00370004: 0x78,
    0x00370005: 0x78, 0x00400001: 0x78, 0x00400002: 0x78, 0x00400003: 0x78,
    0x00400004: 0x78, 0x00400005: 0x78, 0x004C0006: 0x78, 0x004C0007: 0x78,
    0x004C0008: 0x78, 0x004C0009: 0x78,
}
_PSI0_SOC_CURRENT = {
    0x001E0001: 0x48, 0x001E0002: 0x48, 0x001E0003: 0x48, 0x001E0004: 0x48,
    0x001E0005: 0x48, 0x001E000A: 0x48, 0x001E0101: 0x48, 0x00370000: 0x80,
    0x00370001: 0x80, 0x00370002: 0x80, 0x00370003: 0x80, 0x00370004: 0x80,
    0x00370005: 0x80, 0x00400001: 0x80, 0x00400002: 0x80, 0x00400003: 0x80,
    0x00400004: 0x80, 0x00400005: 0x80, 0x004C0006: 0x80, 0x004C0007: 0x80,
    0x004C0008: 0x80, 0x004C0009: 0x80,
}
_UCLK = {
    0x00240903: 0xC4, 0x00620105: 0x12C, 0x00620205: 0x1C8, 0x005D0008: 0x4E4,
    0x005D0009: 0x4E4, 0x005D000B: 0x4E4, 0x00650007: 0x4E4,
}
_MEM_PHY_CLK = {
    0x00240903: 0xC8, 0x00620205: 0x1CC, 0x005D0008: 0x4E8, 0x005D0009: 0x4E8,
    0x005D000B: 0x4E8, 0x00650007: 0x4E8,
}
_VCLK = {
    0x005D0008: 0x4F0, 0x005D0009: 0x4F0, 0x005D000B: 0x4F0, 0x00650007: 0x4F0,
}
_SOCCLK = {
    0x005D0008: 0x4F8, 0x005D0009: 0x4F8, 0x005D000B: 0x4F8, 0x00650007: 0x4F8,
}
_MPIPU_CLK = {
    0x005D0008: 0x50C, 0x005D0009: 0x50C, 0x005D000B: 0x50C, 0x00650007: 0x50C,
}
_IPU_CLK = {
    0x005D0008: 0x510, 0x005D0009: 0x510, 0x005D000B: 0x510, 0x00650007: 0x510,
}


def _f(data: bytes, off: int | None) -> float:
    if off is None or off + 4 > len(data):
        return math.nan
    return struct.unpack_from("<f", data, off)[0]


@dataclass
class PmSensors:
    stapm_limit: float | None = None
    stapm_value: float | None = None
    fast_limit: float | None = None
    fast_value: float | None = None
    slow_limit: float | None = None
    slow_value: float | None = None
    tctl_temp: float | None = None
    cclk_busy: float | None = None
    socket_power: float | None = None
    gfx_clk: float | None = None
    gfx_temp: float | None = None
    gfx_power: float | None = None
    gfx_volt: float | None = None
    mem_clk: float | None = None
    soc_power: float | None = None
    soc_volt: float | None = None
    fclk: float | None = None
    l3_clk: float | None = None
    l3_logic: float | None = None
    l3_vddm: float | None = None
    l3_temp: float | None = None
    psi0_current: float | None = None
    psi0soc_current: float | None = None
    uclk: float | None = None
    mem_phy_clk: float | None = None
    mem_transfer_rate: float | None = None
    vclk: float | None = None
    socclk: float | None = None
    mpipu_clk: float | None = None
    ipu_clk: float | None = None




def read_sensors(data: bytes, ver: int) -> PmSensors:
    def f(off):
        v = _f(data, off)
        return None if math.isnan(v) else v

    tctl_temp_val = None
    if ver in (0x00540104, 0x00540004, 0x00620205):
        if ver == 0x00540104:
            val, alt = f(0x2C), f(0xF0)
            if val is not None and alt is not None:
                tctl_temp_val = alt if alt > val and alt < 130.0 else val
            elif val is not None:
                tctl_temp_val = val
    elif ver == 0x00620105:
        hottest = -1000.0
        for core in range(8):
            ctemp = f(0x4F4 + core * 4)
            if ctemp is not None and 0.0 < ctemp < 130.0:
                hottest = max(hottest, ctemp)
        if hottest > -1000.0:
            tctl_temp_val = hottest
    elif ver == 0x00240903:
        tctl_temp_val = f(0x14)
    elif ver in _TCTL_V1:
        tctl_temp_val = f(0x5C)
    elif ver in _TCTL_V2:
        tctl_temp_val = f(0x44)

    sock_pwr = None
    if ver in (0x00540104, 0x00540004, 0x00620205):
        sock_pwr = f(0x68)
    elif ver == 0x00620105:
        sock_pwr = f(0x50)
    elif ver == 0x00240903:
        sock_pwr = f(0x4)
    else:
        sock_pwr = f(_SOCKET_POWER.get(ver))

    gfx_clk_val = None
    gfx_temp_val = None
    if ver == 0x00540104:
        gclk = f(0x190)
        if gclk is not None and 1.0 <= gclk <= 10000.0:
            gfx_clk_val = gclk
            gtemp = f(0x188)
            if gtemp is not None and 1.0 <= gtemp <= 130.0:
                gfx_temp_val = gtemp
    elif ver == 0x00620105:
        gfx_clk_val = f(0x1B0)
    else:
        gfx_clk_val = f(_GFX_CLK.get(ver))
        gfx_temp_val = f(_GFX_TEMP.get(ver))

    if ver in (0x00540104, 0x00540004):
        mem_clk_val = f(0x1D4)
    elif ver == 0x00620105:
        mem_clk_val = f(0x13C)
    else:
        mem_clk_val = f(_MEM_CLK.get(ver))

    mem_phy_clk_val = f(_MEM_PHY_CLK.get(ver))
    mem_transfer_rate_val = None
    if ver in (0x00240903, 0x00620205):
        if mem_phy_clk_val is not None:
            mem_transfer_rate_val = mem_phy_clk_val * 2.0
    elif ver == 0x00620105:
        if mem_clk_val is not None:
            mem_transfer_rate_val = mem_clk_val * 2.0
    elif ver in (0x005D0008, 0x005D0009, 0x005D000B, 0x00650007):
        raw = f(0x4EC)
        if raw is not None and mem_phy_clk_val is not None and raw >= mem_phy_clk_val and raw <= 20000.0:
            mem_transfer_rate_val = raw
        elif mem_phy_clk_val is not None:
            mem_transfer_rate_val = mem_phy_clk_val * 2.0

    return PmSensors(
        stapm_limit=f(0x00) if ver not in (0x00540104, 0x00540004, 0x00620105, 0x00620205, 0x00240903) else None,
        stapm_value=f(0x04) if ver not in (0x00540104, 0x00540004, 0x00620105, 0x00620205, 0x00240903) else None,
        fast_limit=f(0x08),
        fast_value=f(0x458) if ver == 0x00620105 else f(0x0C),
        slow_limit=f(0x3EC) if ver == 0x00620105 else (f(0x10) if ver not in (0x00540104, 0x00540004, 0x00620205) else None),
        slow_value=f(0x14) if ver not in (0x00540104, 0x00540004, 0x00620105, 0x00620205, 0x00240903) else None,
        tctl_temp=tctl_temp_val,
        cclk_busy=f(_CCLK_BUSY.get(ver)),
        socket_power=sock_pwr,
        gfx_clk=gfx_clk_val,
        gfx_temp=gfx_temp_val,
        gfx_power=f(_GFX_POWER.get(ver)),
        gfx_volt=f(_GFX_VOLT.get(ver)),
        mem_clk=mem_clk_val,
        soc_power=f(_SOC_POWER.get(ver)),
        soc_volt=f(_SOC_VOLT.get(ver)),
        fclk=f(_FCLK.get(ver)),
        l3_clk=f(_L3_CLK.get(ver)),
        l3_logic=f(_L3_LOGIC.get(ver)),
        l3_vddm=f(_L3_VDDM.get(ver)),
        l3_temp=f(_L3_TEMP.get(ver)),
        psi0_current=f(_PSI0_CURRENT.get(ver)),
        psi0soc_current=f(_PSI0_SOC_CURRENT.get(ver)),
        uclk=f(_UCLK.get(ver)),
        mem_phy_clk=mem_phy_clk_val,
        mem_transfer_rate=mem_transfer_rate_val,
        vclk=f(_VCLK.get(ver)),
        socclk=f(_SOCCLK.get(ver)),
        mpipu_clk=f(_MPIPU_CLK.get(ver)),
        ipu_clk=f(_IPU_CLK.get(ver)),
    )


def read_table(data: bytes, ver: int) -> list[tuple[str, float, str]]:
    def f(off): return _f(data, off)

    if ver in (0x00540104, 0x00540004):
        limit_val = f(0x20)
        vrm_cur = 0x20 if limit_val is not None and 0.0 < limit_val <= 500.0 else None
        vrm_cur_val = 0x50
        vrmsoc_cur = vrmsoc_cur_val = None
        edc_val = f(0xF4)
        vrmmax_cur = 0xF4 if edc_val is not None and 0.0 < edc_val <= 500.0 else None
        vrmmax_cur_val = None
        vrmsocmax_cur = vrmsocmax_cur_val = None
    elif ver == 0x00620105:
        limit_val = f(0x28)
        vrm_cur = 0x28 if limit_val is not None and 0.0 < limit_val <= 500.0 else None
        vrm_cur_val = 0x438
        vrmsoc_cur = vrmsoc_cur_val = None
        edc_val = f(0x20)
        vrmmax_cur = 0x20 if edc_val is not None and 0.0 < edc_val <= 500.0 else None
        vrmmax_cur_val = None
        vrmsocmax_cur = vrmsocmax_cur_val = None
    elif ver == 0x00620205:
        limit_val = f(0x20)
        vrm_cur = 0x20 if limit_val is not None and 0.0 < limit_val <= 500.0 else None
        vrm_cur_val = 0x24
        vrmsoc_cur = vrmsoc_cur_val = None
        edc_val = f(0xFC)
        vrmmax_cur = 0xFC if edc_val is not None and 0.0 < edc_val <= 500.0 else None
        vrmmax_cur_val = 0x100
        vrmsocmax_cur = vrmsocmax_cur_val = None
    elif ver == 0x00240903:
        limit_val = f(0x8)
        vrm_cur = 0x8 if limit_val is not None and 0.0 < limit_val <= 500.0 else None
        vrm_cur_val = 0xC
        vrmsoc_cur = vrmsoc_cur_val = None
        edc_val = f(0x20)
        vrmmax_cur = 0x20 if edc_val is not None and 0.0 < edc_val <= 500.0 else None
        vrmmax_cur_val = 0x24
        vrmsocmax_cur = vrmsocmax_cur_val = None
    elif ver in _VRM_V1:
        vrm_cur, vrm_cur_val = 0x18, 0x1C
        vrmsoc_cur, vrmsoc_cur_val = 0x20, 0x24
        vrmmax_cur, vrmmax_cur_val = 0x28, 0x2C
        vrmsocmax_cur, vrmsocmax_cur_val = 0x34, 0x38
    elif ver in _VRM_V2:
        vrm_cur, vrm_cur_val = 0x20, 0x24
        vrmsoc_cur, vrmsoc_cur_val = 0x28, 0x2C
        vrmmax_cur, vrmmax_cur_val = 0x30, 0x34
        vrmsocmax_cur, vrmsocmax_cur_val = 0x38, 0x3C
    elif ver in _VRM_V3:
        vrm_cur, vrm_cur_val = 0x30, 0x34
        vrmsoc_cur, vrmsoc_cur_val = 0x38, 0x3C
        vrmmax_cur = vrmmax_cur_val = vrmsocmax_cur = vrmsocmax_cur_val = None
    else:
        vrm_cur = vrm_cur_val = vrmsoc_cur = vrmsoc_cur_val = None
        vrmmax_cur = vrmmax_cur_val = vrmsocmax_cur = vrmsocmax_cur_val = None

    tctl_val_metric = None
    if ver in (0x00540104, 0x00540004, 0x00620205):
        tctl = 0x28
        if ver == 0x00540104:
            val, alt = f(0x2C), f(0xF0)
            if val is not None and alt is not None:
                tctl_val_metric = alt if alt > val and alt < 130.0 else val
            elif val is not None:
                tctl_val_metric = val
    elif ver == 0x00620105:
        tctl = 0x344
        hottest = -1000.0
        for core in range(8):
            ctemp = f(0x4F4 + core * 4)
            if ctemp is not None and 0.0 < ctemp < 130.0:
                hottest = max(hottest, ctemp)
        if hottest > -1000.0:
            tctl_val_metric = hottest
    elif ver == 0x00240903:
        tctl = None
        tctl_val_metric = f(0x14)
    elif ver in _TCTL_V1:
        tctl, tctl_val = 0x58, 0x5C
        tctl_val_metric = f(tctl_val)
    elif ver in _TCTL_V2:
        tctl, tctl_val = 0x40, 0x44
        tctl_val_metric = f(tctl_val)
    else:
        tctl = None
        tctl_val_metric = None

    if ver in (0x00540104, 0x00540004, 0x00620205):
        sock_pwr = f(0x68)
    elif ver == 0x00620105:
        sock_pwr = f(0x50)
    elif ver == 0x00240903:
        sock_pwr = f(0x4)
    else:
        sock_pwr = f(_SOCKET_POWER.get(ver))

    gfx_clk_val = None
    gfx_temp_val = None
    if ver == 0x00540104:
        gclk = f(0x190)
        if gclk is not None and 1.0 <= gclk <= 10000.0:
            gfx_clk_val = gclk
            gtemp = f(0x188)
            if gtemp is not None and 1.0 <= gtemp <= 130.0:
                gfx_temp_val = gtemp
    elif ver == 0x00620105:
        gfx_clk_val = f(0x1B0)
    else:
        gfx_clk_val = f(_GFX_CLK.get(ver))
        gfx_temp_val = f(_GFX_TEMP.get(ver))

    if ver in (0x00540104, 0x00540004):
        mem_clk_val = f(0x1D4)
    elif ver == 0x00620105:
        mem_clk_val = f(0x13C)
    else:
        mem_clk_val = f(_MEM_CLK.get(ver))

    mem_phy_clk_val = f(_MEM_PHY_CLK.get(ver))
    mem_transfer_rate_val = None
    if ver in (0x00240903, 0x00620205):
        if mem_phy_clk_val is not None:
            mem_transfer_rate_val = mem_phy_clk_val * 2.0
    elif ver == 0x00620105:
        if mem_clk_val is not None:
            mem_transfer_rate_val = mem_clk_val * 2.0
    elif ver in (0x005D0008, 0x005D0009, 0x005D000B, 0x00650007):
        raw = f(0x4EC)
        if raw is not None and mem_phy_clk_val is not None and raw >= mem_phy_clk_val and raw <= 20000.0:
            mem_transfer_rate_val = raw
        elif mem_phy_clk_val is not None:
            mem_transfer_rate_val = mem_phy_clk_val * 2.0

    ppt_fast_val = f(0x458) if ver == 0x00620105 else f(0x0C)
    ppt_slow_lim = f(0x3EC) if ver == 0x00620105 else (f(0x10) if ver not in (0x00540104, 0x00540004, 0x00620205) else None)

    apu_slow_lim  = 0x18 if ver in _APU_SLOW_VERS else None
    apu_slow_val  = 0x1C if ver in _APU_SLOW_VERS else None
    skin_apu_lim  = 0x58 if ver in _SKIN_APU_VERS else None
    skin_apu_val  = 0x5C if ver in _SKIN_APU_VERS else None

    if ver in _SKIN_DGPU_V2:
        skin_dgpu_lim, skin_dgpu_val = 0x60, 0x64
    elif ver in _SKIN_DGPU_V3:
        skin_dgpu_lim, skin_dgpu_val = 0x68, 0x6C
    else:
        skin_dgpu_lim = skin_dgpu_val = None

    rows: list[tuple[str, float, str]] = [
        ("STAPM LIMIT",        f(0x00) if ver not in (0x00540104, 0x00540004, 0x00620105, 0x00620205, 0x00240903) else None, "stapm-limit"),
        ("STAPM VALUE",        f(0x04) if ver not in (0x00540104, 0x00540004, 0x00620105, 0x00620205, 0x00240903) else None, ""),
        ("PPT LIMIT FAST",     f(0x08), "fast-limit"),
        ("PPT VALUE FAST",     ppt_fast_val, ""),
        ("PPT LIMIT SLOW",     ppt_slow_lim, "slow-limit"),
        ("PPT VALUE SLOW",     f(0x14) if ver not in (0x00540104, 0x00540004, 0x00620105, 0x00620205, 0x00240903) else None, ""),
        ("StapmTimeConst",     f(_STAPM_TIME.get(ver)), "stapm-time"),
        ("SlowPPTTimeConst",   f(_SLOW_TIME.get(ver)),  "slow-time"),
        ("PPT LIMIT APU",      f(apu_slow_lim),  "apu-slow-limit"),
        ("PPT VALUE APU",      f(apu_slow_val),  ""),
        ("TDC LIMIT VDD",      f(vrm_cur),       "vrm-current"),
        ("TDC VALUE VDD",      f(vrm_cur_val),   ""),
        ("TDC LIMIT SOC",      f(vrmsoc_cur),    "vrmsoc-current"),
        ("TDC VALUE SOC",      f(vrmsoc_cur_val),""),
        ("EDC LIMIT VDD",      f(vrmmax_cur),    "vrmmax-current"),
        ("EDC VALUE VDD",      f(vrmmax_cur_val),""),
        ("EDC LIMIT SOC",      f(vrmsocmax_cur), "vrmsocmax-current"),
        ("EDC VALUE SOC",      f(vrmsocmax_cur_val), ""),
        ("PSI0 CURRENT",       f(_PSI0_CURRENT.get(ver)),    "psi0-current"),
        ("PSI0 SOC CURRENT",   f(_PSI0_SOC_CURRENT.get(ver)),"psi0soc-current"),
        ("THM LIMIT CORE",     f(tctl),          "tctl-temp"),
        ("THM VALUE CORE",     tctl_val_metric,  ""),
        ("STT LIMIT APU",      f(skin_apu_lim),  "apu-skin-temp"),
        ("STT VALUE APU",      f(skin_apu_val),  ""),
        ("STT LIMIT dGPU",     f(skin_dgpu_lim), "dgpu-skin-temp"),
        ("STT VALUE dGPU",     f(skin_dgpu_val), ""),
        ("CCLK Boost SETPOINT",f(_CCLK_SETPOINT.get(ver)), "power-saving /"),
        ("CCLK BUSY VALUE",    f(_CCLK_BUSY.get(ver)),     "max-performance"),
        ("SOCKET POWER",       sock_pwr,                    ""),
        ("SOC POWER",          f(_SOC_POWER.get(ver)),      ""),
        ("SOC VOLT",           f(_SOC_VOLT.get(ver)),       ""),
        ("GFX POWER",          f(_GFX_POWER.get(ver)),      ""),
        ("GFX CLK (MHz)",      gfx_clk_val,                 ""),
        ("GFX VOLT",           f(_GFX_VOLT.get(ver)),       ""),
        ("GFX TEMP",           gfx_temp_val,                ""),
        ("L3 CLK (MHz)",       f(_L3_CLK.get(ver)),         ""),
        ("L3 LOGIC",           f(_L3_LOGIC.get(ver)),       ""),
        ("L3 VDDM",            f(_L3_VDDM.get(ver)),        ""),
        ("L3 TEMP",            f(_L3_TEMP.get(ver)),        ""),
        ("FCLK (MHz)",         f(_FCLK.get(ver)),           ""),
        ("UCLK (MHz)",         f(_UCLK.get(ver)),           ""),
        ("MEM CLK (MHz)",      mem_clk_val,                 ""),
        ("MEM PHY CLK (MHz)",  mem_phy_clk_val,             ""),
        ("MEM RATE (MT/s)",    mem_transfer_rate_val,       ""),
        ("VCLK (MHz)",         f(_VCLK.get(ver)),           ""),
        ("SOCCLK (MHz)",       f(_SOCCLK.get(ver)),         ""),
        ("MPIPU CLK (MHz)",    f(_MPIPU_CLK.get(ver)),      ""),
        ("IPU CLK (MHz)",      f(_IPU_CLK.get(ver)),        ""),
    ]
    return [(label, val, flag) for label, val, flag in rows if val is not None and not math.isnan(val)]


@dataclass
class CoreSensors:
    core: int
    power: float | None = None
    volt: float | None = None
    temp: float | None = None
    clk: float | None = None
    freqeff: float | None = None
    c0: float | None = None
    cc1: float | None = None
    cc6: float | None = None


def read_core_sensors(data: bytes, ver: int) -> list[CoreSensors]:
    def f(off):
        if off is None or off + 4 > len(data):
            return None
        v = struct.unpack_from("<f", data, off)[0]
        return None if math.isnan(v) else v

    if ver in (0x00540004, 0x00620205, 0x0064020C):
        core_count = 16
    elif ver == 0x00620105:
        core_count = 8
    elif ver in (0x005D0008, 0x005D0009, 0x005D000A, 0x005D000B, 0x00650005, 0x00650007):
        core_count = 12
    else:
        core_count = 8

    out = []
    for c in range(core_count):
        p_base = None
        if ver in (0x00370000, 0x00370001, 0x00370002, 0x00370003, 0x00370004): p_base = 0x300
        elif ver == 0x00370005: p_base = 0x31C
        elif ver == 0x003F0000 and c < 4: p_base = 0x238
        elif ver == 0x00400001: p_base = 0x304
        elif ver in (0x00400004, 0x00400005): p_base = 0x320
        elif ver == 0x001E0004 and c < 4: p_base = 0x180
        elif ver in (0x005D0008, 0x005D0009, 0x005D000B, 0x00650007): p_base = 0x9D4
        elif ver == 0x0064020C: p_base = 0xB90
        elif ver == 0x00620105 and c < 8: p_base = 0x534
        elif ver in (0x00540004, 0x00540104): p_base = 0x494
        elif ver == 0x00620205: p_base = 0x4B4
        elif ver == 0x00240903: p_base = 0x24C
        power = f(p_base + c * 4) if p_base is not None else None

        if power is None or power <= 0.0:
            continue

        v_base = None
        if ver in (0x00370000, 0x00370001, 0x00370002, 0x00370003, 0x00370004): v_base = 0x320
        elif ver == 0x00370005: v_base = 0x33C
        elif ver == 0x003F0000 and c < 4: v_base = 0x248
        elif ver in (0x00400004, 0x00400005): v_base = 0x340
        elif ver == 0x001E0004 and c < 4: v_base = 0x1A0
        elif ver in (0x005D0008, 0x005D0009, 0x005D000B, 0x00650007): v_base = 0xA04
        elif ver == 0x0064020C: v_base = 0xBD0
        elif ver == 0x00620105 and c < 8: v_base = 0x4D4
        elif ver == 0x00540004: v_base = 0x4D4
        elif ver == 0x00540104: v_base = 0x4B4
        elif ver == 0x00620205: v_base = 0x4F4
        elif ver == 0x00240903: v_base = 0x26C
        volt = f(v_base + c * 4) if v_base is not None else None

        t_base = None
        if ver in (0x00370000, 0x00370001, 0x00370002, 0x00370003, 0x00370004): t_base = 0x340
        elif ver == 0x00370005: t_base = 0x35C
        elif ver == 0x003F0000 and c < 4: t_base = 0x258
        elif ver in (0x00400004, 0x00400005): t_base = 0x360
        elif ver == 0x001E0004 and c < 4: t_base = 0x624
        elif ver in (0x005D0008, 0x005D0009, 0x005D000B, 0x00650007): t_base = 0xA34
        elif ver == 0x0064020C: t_base = 0xC10
        elif ver == 0x00620105 and c < 8: t_base = 0x4F4
        elif ver == 0x00540004: t_base = 0x514
        elif ver == 0x00540104: t_base = 0x4D4
        elif ver == 0x00620205: t_base = 0x534
        elif ver == 0x00240903: t_base = 0x28C
        temp = f(t_base + c * 4) if t_base is not None else None

        clk = None
        if ver == 0x001E0004 and c < 4:
            val = f(0x1C0 + c * 4)
            if val is not None:
                clk = val / 1000.0
        else:
            clk_base = None
            if ver in (0x00370000, 0x00370001, 0x00370002, 0x00370003, 0x00370004): clk_base = 0x3A0
            elif ver == 0x00370005: clk_base = 0x3BC
            elif ver == 0x003F0000 and c < 4: clk_base = 0x288
            elif ver in (0x00400004, 0x00400005): clk_base = 0x3c0
            elif ver in (0x005D0008, 0x005D0009, 0x005D000B, 0x00650007): clk_base = 0xA64
            elif ver == 0x0064020C: clk_base = 0xc50
            elif ver == 0x00620105 and c < 8: clk_base = 0x514
            elif ver == 0x00540004: clk_base = 0x554
            elif ver == 0x00540104: clk_base = 0x4F4
            elif ver == 0x00620205: clk_base = 0x574
            elif ver == 0x00240903: clk_base = 0x2EC
            clk = f(clk_base + c * 4) if clk_base is not None else None

        if volt is None or volt <= 0.0 or volt >= 2.0: continue
        if temp is None or temp <= 0.0 or temp >= 130.0: continue
        if clk is None or clk <= 0.0 or clk >= 10.0: continue

        fe_base = None
        if ver in (0x005D0008, 0x005D0009, 0x005D000B, 0x00650007): fe_base = 0xA94
        elif ver == 0x0064020C: fe_base = 0xC90
        elif ver == 0x00540004: fe_base = 0x594
        elif ver == 0x00540104: fe_base = 0x514
        elif ver == 0x00620205: fe_base = 0x5B4
        elif ver == 0x00240903: fe_base = 0x30C
        freqeff = f(fe_base + c * 4) if fe_base is not None else None

        c0_base = None
        if ver in (0x005D0008, 0x005D0009, 0x005D000B, 0x00650007): c0_base = 0xAB4
        elif ver == 0x0064020C: c0_base = 0xCD0
        elif ver == 0x00620105 and c < 8: c0_base = 0x594
        elif ver == 0x00540004: c0_base = 0x5D4
        elif ver == 0x00540104: c0_base = 0x534
        elif ver == 0x00620205: c0_base = 0x5F4
        elif ver == 0x00240903: c0_base = 0x32C
        c0 = f(c0_base + c * 4) if c0_base is not None else None

        cc1_base = None
        if ver in (0x005D0008, 0x005D0009, 0x005D000B, 0x00650007): cc1_base = 0xAD4
        elif ver == 0x0064020C: cc1_base = 0xD10
        elif ver == 0x00620105 and c < 8: cc1_base = 0x5B4
        elif ver == 0x00540004: cc1_base = 0x614
        elif ver == 0x00540104: cc1_base = 0x554
        elif ver == 0x00620205: cc1_base = 0x634
        elif ver == 0x00240903: cc1_base = 0x34C
        cc1 = f(cc1_base + c * 4) if cc1_base is not None else None

        cc6_base = None
        if ver in (0x005D0008, 0x005D0009, 0x005D000B, 0x00650007): cc6_base = 0xAF4
        elif ver == 0x0064020C: cc6_base = 0xD50
        elif ver == 0x00620105 and c < 8: cc6_base = 0x574
        elif ver == 0x00540004: cc6_base = 0x654
        elif ver == 0x00540104: cc6_base = 0x574
        elif ver == 0x00620205: cc6_base = 0x674
        elif ver == 0x00240903: cc6_base = 0x36C
        cc6 = f(cc6_base + c * 4) if cc6_base is not None else None

        out.append(CoreSensors(
            core=c, power=power, volt=volt, temp=temp, clk=clk,
            freqeff=freqeff, c0=c0, cc1=cc1, cc6=cc6
        ))
    return out
