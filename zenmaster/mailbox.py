from __future__ import annotations
import time
from typing import Any

from zenmaster.smu import SMU_FAILED, SMU_REJECTED_PREREQ

NARGS = 6
DEFAULT_TIMEOUT: float = 5.0

MP1: dict[str, tuple[int, int, int]] = {
    "SummitRidge":   (0x3B10528, 0x3B10564, 0x3B10598),
    "PinnacleRidge": (0x3B10528, 0x3B10564, 0x3B10598),
    "Matisse":       (0x3B10530, 0x3B1057C, 0x3B109C4),
    "Vermeer":       (0x3B10530, 0x3B1057C, 0x3B109C4),
    "VanGogh":       (0x3B10528, 0x3B10578, 0x3B10998),
    "Mendocino":     (0x3B10528, 0x3B10578, 0x3B10998),
    "Rembrandt":     (0x3B10528, 0x3B10578, 0x3B10998),
    "PhoenixPoint":  (0x3B10528, 0x3B10578, 0x3B10998),
    "PhoenixPoint2": (0x3B10528, 0x3B10578, 0x3B10998),
    "HawkPoint":     (0x3B10528, 0x3B10578, 0x3B10998),
    "HawkPoint2":    (0x3B10528, 0x3B10578, 0x3B10998),
    "SonomaValley":  (0x3B10528, 0x3B10578, 0x3B10998),
    "Raphael":       (0x3B10530, 0x3B1057C, 0x3B109C4),
    "DragonRange":   (0x3B10530, 0x3B1057C, 0x3B109C4),
    "GraniteRidge":  (0x3B10530, 0x3B1057C, 0x3B109C4),
    "FireRange":     (0x3B10530, 0x3B1057C, 0x3B109C4),
    "StrixPoint":    (0x3B10928, 0x3B10978, 0x3B10998),
    "KrackanPoint":  (0x3B10928, 0x3B10978, 0x3B10998),
    "KrackanPoint2": (0x3B10928, 0x3B10978, 0x3B10998),
    "StrixHalo":     (0x3B10928, 0x3B10978, 0x3B10998),
}
MP1_DEFAULT = (0x3B10528, 0x3B10564, 0x3B10998)

RSMU: dict[str, tuple[int, int, int]] = {
    "SummitRidge":   (0x3B1051C, 0x3B10568, 0x3B10590),
    "PinnacleRidge": (0x3B1051C, 0x3B10568, 0x3B10590),
    "Matisse":       (0x3B10524, 0x3B10570, 0x3B10A40),
    "Vermeer":       (0x3B10524, 0x3B10570, 0x3B10A40),
    "Raphael":       (0x3B10524, 0x3B10570, 0x3B10A40),
    "DragonRange":   (0x3B10524, 0x3B10570, 0x3B10A40),
    "GraniteRidge":  (0x3B10524, 0x3B10570, 0x3B10A40),
    "FireRange":     (0x3B10524, 0x3B10570, 0x3B10A40),
}
RSMU_DEFAULT = (0x3B10A20, 0x3B10A80, 0x3B10A88)

HSMP: dict[str, tuple[int, int, int]] = {
    "Medusa1":      (0x3B10A8C, 0x3B10A90, 0x3B10A94),
    "OlympicRidge": (0x3B10A8C, 0x3B10A90, 0x3B10A94),
    "Medusa2":      (0x3B10A8C, 0x3B10A90, 0x3B10A94),
}
HSMP_DEFAULT = (0x3B10A8C, 0x3B10A90, 0x3B10A94)


def poll_response(smn_read: Any, rsp: int, fast_poll: int = 64, poll_sleep: float = 0.0005,
                  timeout: float = DEFAULT_TIMEOUT) -> int:
    for _ in range(fast_poll):
        r = smn_read(rsp)
        if r:
            return r
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        time.sleep(poll_sleep)
        r = smn_read(rsp)
        if r:
            return r
    return 0


def mailbox_send(smn_write: Any, smn_read: Any, msg: int, rsp: int, args_addr: int, op: int, arg0: int,
                 fast_poll: int = 64, poll_sleep: float = 0.0005,
                 timeout: float = DEFAULT_TIMEOUT) -> int:
    smn_write(rsp, 0)
    smn_write(args_addr, arg0)
    for i in range(1, NARGS):
        smn_write(args_addr + i * 4, 0)
    smn_write(msg, op)
    return poll_response(smn_read, rsp, fast_poll, poll_sleep, timeout) or SMU_FAILED


def mailbox_query(smn_write: Any, smn_read: Any, msg: int, rsp: int, args_base: int, op: int, arg0: int,
                  fast_poll: int = 64, poll_sleep: float = 0.0005,
                  timeout: float = DEFAULT_TIMEOUT) -> tuple[int, list[int]]:
    smn_write(rsp, 0)
    for i in range(NARGS):
        smn_write(args_base + i * 4, 0)
    if arg0:
        smn_write(args_base, arg0)
    smn_write(msg, op)
    r = poll_response(smn_read, rsp, fast_poll, poll_sleep, timeout)
    if r:
        return r, [smn_read(args_base + i * 4) for i in range(NARGS)]
    return SMU_FAILED, [0] * NARGS


def transfer_with_retry(send_once, delays: tuple[float, ...] = (0.1, 0.5)) -> int:
    status = send_once()
    for delay in delays:
        if status != SMU_REJECTED_PREREQ:
            break
        time.sleep(delay)
        status = send_once()
    return status
