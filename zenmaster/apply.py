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


def _skin_scale(arg_name: str, value: int) -> int:
    return value * 256 if arg_name in _SKIN_ARGS else value


def _error(name: str, msg: str) -> ApplyResult:
    return {"arg": name, "value": 0, "mailbox": "", "opcode": 0,
            "status": 0, "error": msg, "returned": None}


def make_psm_margin_arg(margin: int) -> int:
    offset = 0x100000 if margin < 0 else 0
    return (offset + margin) & 0xFFFF


def make_per_core_co_arg(payload: str | int) -> int:
    if isinstance(payload, int):
        return make_psm_margin_arg(payload)
    parts = [int(p.strip()) for p in str(payload).split(",")]
    if len(parts) == 4:
        ccd, ccx, core, margin = parts
    elif len(parts) == 2:
        ccd, ccx, core, margin = 0, 0, parts[0], parts[1]
    else:
        return 0
    m = make_psm_margin_arg(margin)
    return ((ccd & 0xF) << 28) | ((ccx & 0xF) << 24) | ((core & 0xF) << 20) | m


def make_curve_shaper_arg(payload: str) -> int:
    parts = [int(p.strip()) for p in payload.split(",")]
    if len(parts) < 4:
        return 0
    high, med, low, tier = parts[:4]
    high_b = (256 + high) & 0xFF if high < 0 else high & 0xFF
    med_b = (256 + med) & 0xFF if med < 0 else med & 0xFF
    low_b = (256 + low) & 0xFF if low < 0 else low & 0xFF
    return (high_b << 24) | (med_b << 16) | (low_b << 8) | (1 << 7) | (tier & 0x7F)


def apply(args_str: str, family: str) -> tuple[list[ApplyResult], bool]:
    try:
        tokens = shlex.split(args_str) if args_str.strip() else []
    except ValueError:
        return [_error("", "invalid preset string (unclosed quote)")], True

    results: list[ApplyResult] = []
    had_rejection = False

    for token in tokens:
        raw_name, sep, val_str = token.lstrip("-").partition("=")
        name = raw_name.replace("_", "-").lower()
        if not name:
            continue

        if runner.is_flag_arg(name):
            value = 0
            smu_val = 0
        elif not sep:
            results.append(_error(name, f"--{name} requires a value"))
            had_rejection = True
            continue
        else:
            if name == "set-curveshaper":
                try:
                    smu_val = make_curve_shaper_arg(val_str)
                    value = smu_val
                except Exception:
                    results.append(_error(name, f"invalid curve shaper format '{val_str}' (expected high,med,low,tier)"))
                    had_rejection = True
                    continue
            elif name == "set-coper" and "," in val_str:
                try:
                    smu_val = make_per_core_co_arg(val_str)
                    value = smu_val
                except Exception:
                    results.append(_error(name, f"invalid per-core format '{val_str}' (expected ccd,ccx,core,margin)"))
                    had_rejection = True
                    continue
            else:
                try:
                    value = int(val_str, 0)
                    if name in ("set-coall", "set-coper", "set-cogfx"):
                        smu_val = make_psm_margin_arg(value)
                    else:
                        smu_val = _skin_scale(name, value) & 0xFFFFFFFF
                except ValueError:
                    results.append(_error(name, f"invalid value '{val_str}'"))
                    had_rejection = True
                    continue

        matches = runner.lookup(family, name)
        if not matches:
            results.append(_error(name, f"not supported on {family}"))
            had_rejection = True
            continue

        is_query = name.startswith("get-")

        any_ok = False
        for is_mp1, op in matches:
            returned = None
            if is_query:
                if is_mp1:
                    status, out = smu.query_mp1(family, op)
                else:
                    status, out = smu.query_rsmu(family, op)
                if status == smu.SMU_OK:
                    returned = out[0]
            elif is_mp1:
                status = smu.send_mp1(family, op, smu_val)
            else:
                status = smu.send_rsmu(family, op, smu_val)
            mailbox = "MP1" if is_mp1 else "RSMU"
            if status == smu.SMU_OK:
                any_ok = True
            results.append({"arg": name, "value": value, "mailbox": mailbox,
                             "opcode": op, "status": status, "error": None, "returned": returned})

        if not any_ok:
            had_rejection = True

    return results, had_rejection

