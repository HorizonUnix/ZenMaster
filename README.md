# ZenMaster

[![PyPI](https://img.shields.io/pypi/v/zenmaster?style=flat-square&color=blue)](https://pypi.org/project/zenmaster/)
[![Python](https://img.shields.io/pypi/pyversions/zenmaster?style=flat-square&color=yellow)](https://pypi.org/project/zenmaster/)
[![License](https://img.shields.io/badge/License-GPLv3-blue?style=flat-square)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20Windows%20%7C%20macOS-lightgrey?style=flat-square)](https://pypi.org/project/zenmaster/)

## Overview

ZenMaster adjusts power management settings for AMD Ryzen CPUs and APUs on Linux, Windows, and macOS (AMD Hackintosh). It speaks the same CLI as [RyzenAdj](https://github.com/FlyGoat/RyzenAdj), so your existing commands and presets keep working, but you install it with `pip` and never touch a compiler. Set power limits, temperature limits, VRM currents, clocks, voltages and Curve Optimizer offsets without going near the BIOS.

```bash
pip install zenmaster
```

Reasons to reach for this instead of RyzenAdj:

- Installs with `pip` — no cmake, libpci, or building from source
- Same `--name=value` syntax, so scripts and presets carry over unchanged
- Uses [PawnIO](https://github.com/namazso/PawnIO) on Windows instead of WinRing0, which has known CVEs
- `--help` lists only the arguments your CPU supports, not every possible option
- `--table` shows a labeled sensor table; `--json` makes the output scriptable
- `--reapply=N` keeps your settings applied so other software can't undo them
- Works as a Python library — `import zenmaster` — on Linux, Windows, and macOS
- No mandatory third-party dependencies on any platform

---

## Documentation

Full documentation lives in the [**Wiki**](https://github.com/HorizonUnix/ZenMaster/wiki):

| Page | What's in it |
|---|---|
| [Installation](https://github.com/HorizonUnix/ZenMaster/wiki/Installation) | Linux, Windows, and macOS setup — `ryzen_smu`, PawnIO, DirectHW |
| [CLI Usage](https://github.com/HorizonUnix/ZenMaster/wiki/CLI-Usage) | Every option, examples, JSON output |
| [Tuning Arguments](https://github.com/HorizonUnix/ZenMaster/wiki/Tuning-Arguments) | Full argument reference with units |
| [PM Table and Monitoring](https://github.com/HorizonUnix/ZenMaster/wiki/PM-Table-and-Monitoring) | `--table` / `--dump-table` |
| [Library API](https://github.com/HorizonUnix/ZenMaster/wiki/Library-API) | Embedding ZenMaster in Python |
| [Architecture](https://github.com/HorizonUnix/ZenMaster/wiki/Architecture) | Internals, SMU protocol, opcode tables |
| [Troubleshooting](https://github.com/HorizonUnix/ZenMaster/wiki/Troubleshooting) | Fixes for the common problems |
| [FAQ](https://github.com/HorizonUnix/ZenMaster/wiki/FAQ) | Short answers |

---

## Compatibility

| Platform | Status |
|----------|--------|
| Linux, Python 3.10+, root | Supported — `ryzen_smu` module or PCI direct access |
| Windows, Python 3.10+, Administrator | Supported — PawnIO driver |
| macOS (AMD Hackintosh), Python 3.10+, root | Supported — DirectHW.kext, or IOPCIBridge for tuning only |
| Intel | Not supported |

> [!NOTE]
> On Linux, PCI direct access works on most systems without any kernel module. **`ryzen_smu` is only required when Secure Boot is enabled**, since kernel lockdown blocks raw PCI access. Install [ryzen_smu](https://github.com/amkillam/ryzen_smu) ≥ 0.1.7 and enroll the signing key in that case.

> [!WARNING]
> This tool writes directly to the CPU's System Management Unit. Wrong values can cause instability, throttling, or a hard lock. Use at your own risk.

---

## How it compares to RyzenAdj

ZenMaster keeps RyzenAdj's argument names and SMU opcode semantics, so it's a drop-in replacement for most use cases, minus the build step and the WinRing0 driver.

| | RyzenAdj | ZenMaster |
|---|---|---|
| Install | Build from source (cmake, pkg-config, libpci) | `pip install zenmaster` |
| Language | C | Pure Python 3.10+ |
| Windows driver | WinRing0 ⚠️ | PawnIO ✅ |
| `--help` | Static — lists every argument | Dynamic — only your CPU's arguments |
| Output | Plain text | Plain text or `--json` |
| PM table | Raw float dump | Labeled fields with units (`--table`) |
| Use as a library | Link the C `libryzenadj` / shell out | `import zenmaster` |
| Build dependencies | cmake, make, libpci | None |
| Focus | "Ryzen Mobile Processors" | Ryzen mobile **and** desktop |

### On WinRing0

RyzenAdj's Windows backend uses WinRing0 (`OlsApi` / OpenLibSys), a driver with well-documented vulnerabilities ([CVE-2020-14979](https://nvd.nist.gov/vuln/detail/CVE-2020-14979), [CVE-2021-41285](https://nvd.nist.gov/vuln/detail/CVE-2021-41285)). It hands any unprivileged process full read/write access to physical memory, PCI config space, and I/O ports, and several AV vendors flag it outright.

ZenMaster uses [PawnIO](https://github.com/namazso/PawnIO) instead — a purpose-built, Microsoft-signed kernel driver with a narrow IOCTL interface. No raw physical-memory access, no known CVEs.

---

## Installation

### Linux

```bash
pip install zenmaster
```

Requires root, and either the `ryzen_smu` kernel module or PCI direct access (used automatically when available).

Install `ryzen_smu` (only needed when Secure Boot is on):

```bash
git clone https://github.com/amkillam/ryzen_smu
cd ryzen_smu && make && sudo make install
sudo modprobe ryzen_smu
```

Apply a preset:

```bash
sudo zenmaster --stapm-limit=15000 --fast-limit=20000 --tctl-temp=90
```

Re-apply every 30 seconds:

```bash
sudo zenmaster --stapm-limit=15000 --reapply=30
```

### Windows

1. Install [PawnIO](https://github.com/namazso/PawnIO.Setup/releases/latest/download/PawnIO_setup.exe) and reboot.
2. Open an **Administrator** terminal.

```bat
pip install zenmaster
zenmaster --stapm-limit=15000 --fast-limit=20000 --tctl-temp=90
```

### macOS (AMD Hackintosh)

Requires root, and one of two access paths:

- **[DirectHW.kext](https://github.com/joevt/directhw)** — full support, including `--table`/`--sensors`. Needs SIP set to allow unsigned kexts (`csr-active-config=03080000` in Clover/OpenCore).
- **IOPCIBridge (`--iopci`)** — no kext, but tuning only, no PM table. Needs the `debug=0x144` boot-arg.

```bash
pip3 install zenmaster
sudo python3 -m zenmaster --stapm-limit=15000 --fast-limit=20000 --tctl-temp=90
```

If neither access path is set up, ZenMaster's error tells you which one to add.

`sudo zenmaster` can fail with "command not found" if the `zenmaster` script lands somewhere root's `PATH` doesn't reach (common with `pip3 install --user` or Homebrew Python). `sudo python3 -m zenmaster` sidesteps that by going straight through the interpreter.

---

## CLI

```
zenmaster [OPTIONS] [TUNING ARGS...]
```

| Option | Description |
|---|---|
| `--help` | Show the tuning arguments supported by your CPU |
| `--info` | Detected CPU name, family, socket, active backend, and driver status |
| `--table` | Live PM table with labeled values |
| `--sensors` | Key live sensors only — temp, load, power, clocks (compact; structured under `--json`) |
| `--dump-table` | Raw PM table floats with hex offsets |
| `--json` | Machine-readable JSON output |
| `--reapply=N` | Re-apply settings every N seconds |
| `--version` | Show the installed version and check PyPI for a newer release |
| `--iopci` | macOS only: force the kext-free IOPCIBridge path (tuning only) |

Tuning arguments use the same `--name=value` form as RyzenAdj. Arguments that take no value (`--enable-oc`, `--power-saving`, `--get-*`, …) are passed as bare flags. The `--get-*` query commands print the value the SMU returns:

```
$ sudo zenmaster --get-pbo-scalar
get-pbo-scalar [RSMU 0x6D] -> OK = 42 (0x0000002A)
```

Check what your CPU supports:

```
$ zenmaster --help

ZenMaster — Ryzen Power Management Tool

Usage: zenmaster [OPTIONS] [TUNING ARGS...]

Tuning arguments for AMD Ryzen 9 7950X (Raphael, AM5_V1):

  Power limits:
    --stapm-limit=<mW>                 Sustained Power Limit — STAPM LIMIT
    --fast-limit=<mW>                  Actual Power Limit — PPT LIMIT FAST
    --slow-limit=<mW>                  Average Power Limit — PPT LIMIT SLOW
    ...
```

Live PM table (APU / mobile):

```
$ sudo zenmaster --table

PM Table Version: 0x00450005
+-------------------------+-----------+------------------------+
| STAPM LIMIT             |    15.000 | stapm-limit            |
| STAPM VALUE             |    12.441 |                        |
| PPT LIMIT FAST          |    20.000 | fast-limit             |
| THM LIMIT CORE          |    90.000 | tctl-temp              |
| THM VALUE CORE          |    67.125 |                        |
+-------------------------+-----------+------------------------+
```

Compact live sensors — `--sensors` (add `--json` for a structured object a monitoring script can read directly):

```
$ sudo zenmaster --sensors
CPU Temp    :     64.0 °C
CPU Load    :     38.5 %
Socket Power:     41.2 W
iGPU Clock  :   2400.0 MHz
Mem Clock   :   2400.0 MHz
```

---

## Library usage

ZenMaster is built to be embedded in tuning utilities, dashboards, and automation tools — including from non-Python apps via the `--json` CLI.

```python
import zenmaster
from zenmaster import detect, apply, smu

print(zenmaster.__version__)

info = detect()
print(info.name, info.family)

try:
    backend = smu.init()
    print(backend)
except RuntimeError as e:
    print(f"SMU unavailable: {e}")
    raise SystemExit(1)

results, rejected = apply("--stapm-limit=15000 --tctl-temp=90", info.family)
for r in results:
    print(r["arg"], smu.status_name(r["status"]))

apply("--enable-oc", info.family)

if smu.pm_table_supported(info.family):
    data = smu.read_pm_table(info.family)
    ver  = smu.read_pm_table_version(info.family)

smu.send_mp1(info.family, 0x05, 15000)
smu.send_rsmu(info.family, 0x31, 90)
```

Checking backend readiness or reading sensors doesn't require hand-rolling PM table decoding:

```python
from zenmaster import smu

smu.ensure_backend()           # init(), but returns the backend str or None — never raises
smu.unavailable_reason()       # None if usable, else a ready-to-show "why not" message
smu.module_status()            # driver verdict: .ok / .version / .min_version / .reason

s = smu.read_pm_sensors(info.family)   # read + decode the PM table -> PmSensors | None
if s:
    print(s.tctl_temp, s.cclk_busy, s.socket_power, s.gfx_clk)
```

All of this works the same on Linux, Windows, and macOS, and is re-exported at the top level (`from zenmaster import module_status, read_pm_sensors, ...`) so apps never need to import from `zenmaster.linux` directly.

Looking up supported args for a CPU needs no privileges:

```python
from zenmaster import runner

print(runner.get_supported_args("Renoir"))
print(runner.lookup("Renoir", "stapm-limit"))
print(runner.is_flag_arg("enable-oc"))
print(runner.is_flag_arg("stapm-limit"))
```

Runnable examples live in [`examples/`](examples/):

- [`demo.py`](examples/demo.py) — a tour of detection, apply, queries, and raw SMU access
- [`monitor_pmtable.py`](examples/monitor_pmtable.py) — live PM-table dump (ported from RyzenAdj's `get_table_values`)
- [`reapply_loop.py`](examples/reapply_loop.py) — hold a preset against drift via `read_pm_sensors` + `apply` (ported from RyzenAdj's `get_fast_limit` loop)

A few things worth knowing if you're integrating this into your own tool:

- The package ships type hints (`py.typed`), so your type checker sees the full API
- `smu.init()` raises `BackendUnavailable` on failure; SMU calls before init raise `SMUNotInitialized`. Both subclass `ZenMasterError`, which subclasses `RuntimeError`, so you can catch as narrowly or broadly as you like
- `apply()` returns `list[ApplyResult]` — each result is a dict with the stable keys `arg, value, mailbox, opcode, status, error, returned`. `error` is `None` on success; `returned` holds the value from a `get-*` query
- SMU status codes are `smu.SmuStatus` (an `IntEnum`); `smu.status_name(code)` gives you a label

```python
from zenmaster import smu, BackendUnavailable

try:
    smu.init()
except BackendUnavailable as e:
    ...  # no driver / not root / Secure Boot — the message explains which
```

---

## Updating

ZenMaster updates through pip:

```bash
pip install -U zenmaster
```

To check whether a newer release is on PyPI without updating:

```bash
zenmaster --version
```

From code, `zenmaster.check_update()` returns the newer version string, or `None` if you're already current.

---

## Supported CPUs

Covers first-gen Ryzen (Summit Ridge / Zen 1) through Ryzen 9000 and Strix Halo. Run `zenmaster --info` to confirm detection and socket mapping.

PM table support (`--table`): Raven Ridge, Picasso, Dali, Pollock, Renoir, Lucienne, Cezanne/Barcelo, Van Gogh (Steam Deck), Mendocino, Rembrandt, Phoenix Point, Hawk Point, Strix Point, Krackan Point, Strix Halo. On Linux it's read through the `ryzen_smu` module when loaded, otherwise over PCI direct (`/dev/mem`, subject to kernel `CONFIG_STRICT_DEVMEM`). On macOS it needs DirectHW.kext — the kext-free `--iopci` path can tune but can't read the table.

---

## Requirements

| | Linux | Windows | macOS |
|---|---|---|---|
| Python | 3.10+ | 3.10+ | 3.10+ |
| Privileges | root | Administrator | root (sudo) |
| Driver | `ryzen_smu` module or PCI direct | [PawnIO](https://github.com/namazso/PawnIO.Setup) | [DirectHW.kext](https://github.com/joevt/directhw), or IOPCIBridge (`--iopci`, tuning only) |
| Extra deps | None | None | None |

---

## Acknowledgments

| Project | Contribution |
|---------|-------------|
| [RyzenAdj](https://github.com/FlyGoat/RyzenAdj) | Canonical argument names and SMU opcode semantics |
| [UXTU4Linux](https://github.com/HorizonUnix/UXTU4Linux) | SMU opcode tables and Linux backend reference |
| [Universal x86 Tuning Utility](https://github.com/JamesCJ60/Universal-x86-Tuning-Utility) | Windows PawnIO path and CPU detection approach |
| [ryzen_smu](https://github.com/amkillam/ryzen_smu) | Linux kernel module for SMU access |
| [PawnIO](https://github.com/namazso/PawnIO) | Modern signed Windows kernel driver |
| [DirectHW](https://github.com/joevt/directhw) | macOS kext for PCI config and physical memory access (joevt) |
| [pciutils](https://github.com/joevt/pciutils) | The `darwin2` IOPCIBridge method behind the kext-free `--iopci` path (joevt) |
