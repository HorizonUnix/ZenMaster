from __future__ import annotations
import shlex
from typing import TypedDict
from zenmaster import runner, smu


class ApplyResult(TypedDict):
    arg: str
    value: int
    mailbox: str
    opcode: int
    status: int
    error: str | None
    returned: int | None


_SKIN_ARGS = {"apu-skin-temp", "dgpu-skin-temp"}

_APU_SKIN_FAMILIES = {
    "Renoir", "Lucienne", "Cezanne_Barcelo", "VanGogh",
    "Rembrandt", "Mendocino", "PhoenixPoint", "PhoenixPoint2",
    "HawkPoint", "HawkPoint2",
    "StrixPoint", "KrackanPoint", "KrackanPoint2",
}


def _skin_scale(arg_name: str, value: int) -> int:
    return value * 256 if arg_name in _SKIN_ARGS else value


def _co_scale(value: int) -> int:
    if value < 0:
        return (0x100000 - abs(int(value))) & 0xFFFFF
    return int(value) & 0xFFFFF


def _convert_hsmp_psm_margin(value: int) -> int:
    if value < 0:
        margin = value
    elif value & 0x80000:
        margin = value - 0x100000
    else:
        margin = value
    clamped = max(-32768, min(32767, margin))
    return clamped & 0xFFFF


def _pack_coper(val_str: str, use_hsmp: bool = False) -> int:
    delims = (":", ",")
    delim = next((d for d in delims if d in val_str), None)
    if delim is not None:
        parts = [int(p.strip(), 0) for p in val_str.split(delim)]
        if len(parts) == 2:
            core, offset = parts[0], parts[1]
            ccd = 0
        elif len(parts) == 3:
            ccd, core, offset = parts[0], parts[1], parts[2]
        elif len(parts) >= 4:
            ccd, _, core, offset = parts[0], parts[1], parts[2], parts[3]
        else:
            offset = parts[0]
            core = 0
            ccd = 0
        if use_hsmp:
            apic_id = ((ccd << 4) | core) << 1
            margin = _convert_hsmp_psm_margin(offset)
            return ((apic_id & 0xFFFF) << 16) | (margin & 0xFFFF)
        enc20 = _co_scale(offset)
        ccx = core // 8
        c = core % 8
        prefix = ((((ccd & 0xF) << 4 | (ccx & 0xF)) << 4) | (c & 0xF)) << 20
        return prefix | enc20
    val = int(val_str, 0)
    if use_hsmp:
        return _convert_hsmp_psm_margin(val)
    if val < 0:
        return _co_scale(val)
    return val & 0xFFFFFFFF


def _pack_oc_clk_per_core(val_str: str) -> int:
    delims = (":", ",")
    delim = next((d for d in delims if d in val_str), None)
    if delim is not None:
        parts = [int(p.strip(), 0) for p in val_str.split(delim)]
        if len(parts) == 2:
            core, freq = parts[0], parts[1]
            ccd = 0
            ccx = core // 8
        elif len(parts) == 3:
            ccd, core, freq = parts[0], parts[1], parts[2]
            ccx = core // 8
        elif len(parts) >= 4:
            ccd, ccx, core, freq = parts[0], parts[1], parts[2], parts[3]
        else:
            return parts[0] & 0xFFFFFFFF
        freq_enc = min(freq, 8000) & 0xFFFFF
        c = core % 8
        prefix = ((c & 0xF) | ((ccx & 0xF) << 4) | ((ccd & 0xF) << 8)) << 20
        return prefix | freq_enc
    return int(val_str, 0) & 0xFFFFFFFF


def _error(name: str, msg: str) -> ApplyResult:
    return {
        "arg": name,
        "value": 0,
        "mailbox": "",
        "opcode": 0,
        "status": 0,
        "error": msg,
        "returned": None,
    }


def apply(args_str: str, family: str) -> tuple[list[ApplyResult], bool]:
    try:
        tokens = shlex.split(args_str) if args_str.strip() else []
    except ValueError:
        return [_error("", "invalid preset string (unclosed quote)")], True

    results: list[ApplyResult] = []
    had_rejection = False
    use_hsmp = runner.is_hsmp(family)

    for token in tokens:
        raw_name, sep, val_str = token.lstrip("-").partition("=")
        name = raw_name.replace("_", "-").lower()
        if not name:
            continue

        if name == "tctl-limit":
            name = "tctl-temp"

        if runner.is_flag_arg(name):
            value = 0
        elif not sep:
            results.append(_error(name, f"--{name} requires a value"))
            had_rejection = True
            continue
        elif name == "set-coper":
            try:
                value = _pack_coper(val_str, use_hsmp)
            except ValueError:
                results.append(_error(name, f"invalid value '{val_str}'"))
                had_rejection = True
                continue
        elif name == "oc-clk-per-core":
            try:
                value = _pack_oc_clk_per_core(val_str)
            except ValueError:
                results.append(_error(name, f"invalid value '{val_str}'"))
                had_rejection = True
                continue
        else:
            try:
                value = int(val_str, 0)
            except ValueError:
                results.append(_error(name, f"invalid value '{val_str}'"))
                had_rejection = True
                continue

        if name == "tctl-temp" and value >= 1000:
            value //= 1000

        if name == "apu-skin-temp" and family not in _APU_SKIN_FAMILIES:
            results.append(_error(name, f"apu-skin-temp is not supported on {family}"))
            had_rejection = True
            continue

        matches = runner.lookup(family, name)
        if not matches:
            results.append(_error(name, f"not supported on {family}"))
            had_rejection = True
            continue

        if use_hsmp:
            if name == "pbo-scalar" and value >= 100:
                value //= 10
            if name in ("set-coall", "set-cogfx"):
                smu_val = _convert_hsmp_psm_margin(value)
            elif name in ("set-coper", "oc-clk-per-core"):
                smu_val = value & 0xFFFFFFFF
            else:
                smu_val = _skin_scale(name, value) & 0xFFFFFFFF
        else:
            if name in ("set-coall", "set-cogfx"):
                smu_val = _co_scale(value)
            elif name in ("set-coper", "oc-clk-per-core"):
                smu_val = value & 0xFFFFFFFF
            else:
                smu_val = _skin_scale(name, value) & 0xFFFFFFFF

        is_query = name.startswith("get-")
        any_ok = False

        for is_mp1, op in matches:
            returned = None
            if is_query:
                if use_hsmp:
                    status, out = smu.query_hsmp(family, op)
                elif is_mp1:
                    status, out = smu.query_mp1(family, op)
                else:
                    status, out = smu.query_rsmu(family, op)
                if status == smu.SMU_OK:
                    returned = out[0]
            elif use_hsmp:
                status = smu.send_hsmp(family, op, smu_val)
            elif is_mp1:
                status = smu.send_mp1(family, op, smu_val)
            else:
                status = smu.send_rsmu(family, op, smu_val)

            mailbox = "HSMP" if use_hsmp else ("MP1" if is_mp1 else "RSMU")
            if status == smu.SMU_OK:
                any_ok = True

            results.append({
                "arg": name,
                "value": value,
                "mailbox": mailbox,
                "opcode": op,
                "status": status,
                "error": None,
                "returned": returned,
            })

        if not any_ok:
            had_rejection = True

    return results, had_rejection
