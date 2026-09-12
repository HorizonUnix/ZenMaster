# ZenMaster

[![PyPI](https://img.shields.io/pypi/v/zenmaster?style=flat-square&color=blue)](https://pypi.org/project/zenmaster/)
[![Python](https://img.shields.io/pypi/pyversions/zenmaster?style=flat-square&color=yellow)](https://pypi.org/project/zenmaster/)
[![License](https://img.shields.io/badge/License-GPLv3-blue?style=flat-square)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20Windows%20%7C%20macOS-lightgrey?style=flat-square)](https://pypi.org/project/zenmaster/)

## Overview

ZenMaster configures power limits, thermal thresholds, VRM current limits, clocks, voltages, and Curve Optimizer offsets on AMD Zen processors via the System Management Unit (SMU). It operates across Linux, Windows, and macOS (AMD Hackintosh) without requiring BIOS configuration.

ZenMaster uses the same CLI options and argument naming conventions as [RyzenAdj](https://github.com/FlyGoat/RyzenAdj), serving as a drop-in replacement that installs via `pip` with zero compilation steps.

```bash
pip install zenmaster
sudo zenmaster --stapm-limit=15000 --fast-limit=20000 --tctl-temp=90
```

> [!NOTE]
> A graphical frontend for ZenMaster is available in [ZenTune](https://github.com/HorizonUnix/ZenTune) for Linux and macOS.

### Key Capabilities

- **Broad CPU Coverage**: Supports 44 AMD Zen CPU families spanning Zen 1 through Zen 5/6, including mobile APUs, desktop processors, Threadripper workstations, server EPYC platforms (via HSMP), and Hygon Dhyana.
- **Pure Python Delivery**: Pure Python 3.10+ package with no C compiler, cmake, or libpci dependencies.
- **Safe Windows Driver**: Uses Microsoft-signed [PawnIO](https://github.com/namazso/PawnIO) instead of WinRing0. PawnIO enforces restricted IOCTL dispatch and lacks arbitrary physical-memory mapping primitives.
- **Cross-Process Synchronization**: Uses named system mutexes (`/run/lock/access_pci.lock` on Linux, `Global\Access_PCI` on Windows) to serialize SMN bus access across concurrent processes and daemons.
- **Hardware-Filtered CLI**: `zenmaster --help` dynamically queries CPUID and displays only the arguments implemented for the detected CPU family.
- **Curve Optimizer Engine**: `--set-coper` supports individual core, CCD, and CCX targeting (`core:val`, `ccd:core:val`, `ccd:ccx:core:val`) with 20-bit two's complement sign-magnitude encoding.
- **Telemetry and Monitoring**: Parses SMU Power Management (PM) tables across 28 hardware table structures. Supports formatted table output (`--table`), live curses per-core monitoring (`--sensors`), raw binary extraction (`--dump-table`), and machine-readable JSON (`--json`).
- **Persistence Support**: `--reapply=N` runs an integrated background reapply loop to preserve parameters against OEM thermal daemon overrides.
- **Embeddable Library**: `import zenmaster` exports typed primitives (`detect`, `apply`, `smu`, `read_smn`, `write_smn`, `get_ccd_count`) under `py.typed`.

Detailed technical documentation is available in the [ZenMaster Wiki](https://github.com/HorizonUnix/ZenMaster/wiki).

---

## Documentation

| Page | Description |
|---|---|
| [Installation](https://github.com/HorizonUnix/ZenMaster/wiki/Installation) | Setup instructions for Linux (`ryzen_smu` / direct PCI), Windows (PawnIO), and macOS (DirectHW / IOPCIBridge) |
| [CLI Usage](https://github.com/HorizonUnix/ZenMaster/wiki/CLI-Usage) | Command-line reference, query flags, JSON output, and reapply loops |
| [Tuning Arguments](https://github.com/HorizonUnix/ZenMaster/wiki/Tuning-Arguments) | Complete SMU argument index, units, opcode mappings, and Curve Optimizer syntax |
| [PM Table and Monitoring](https://github.com/HorizonUnix/ZenMaster/wiki/PM-Table-and-Monitoring) | Real-time monitoring (`--sensors`), PM table decoding (`--table`), and binary dumps |
| [Library API](https://github.com/HorizonUnix/ZenMaster/wiki/Library-API) | Python integration, low-level SMN operations, and typed exception hierarchies |
| [How ZenMaster Talks to the SMU](https://github.com/HorizonUnix/ZenMaster/wiki/How-ZenMaster-Talks-to-the-SMU) | SMU mailbox protocols (MP1, RSMU, HSMP), PCI config space, and OS driver layers |
| [Architecture](https://github.com/HorizonUnix/ZenMaster/wiki/Architecture) | Subsystem design, family dispatching, opcode tables, and lock mechanisms |
| [Troubleshooting](https://github.com/HorizonUnix/ZenMaster/wiki/Troubleshooting) | Root causes and solutions for permission errors, driver conflicts, and rejected opcodes |
| [FAQ](https://github.com/HorizonUnix/ZenMaster/wiki/FAQ) | Common questions on safety, persistence, hardware support, and limitations |

---

## Compatibility

| Platform | Privileges | Driver Requirements | Access Mechanism |
|----------|------------|---------------------|------------------|
| Linux, Python 3.10+ | root | None (direct PCI), or `ryzen_smu` (>= 0.1.7) | Direct PCI config via `/dev/mem` / `/dev/port`, or `/sys/kernel/ryzen_smu/` sysfs |
| Windows, Python 3.10+ | Administrator | [PawnIO](https://github.com/namazso/PawnIO.Setup) | `\\.\PawnIO` driver handle (`IOCTL_READ_PCI_CONFIG`, `IOCTL_WRITE_PCI_CONFIG`) |
| macOS (AMD Hackintosh), Python 3.10+ | root | [DirectHW.kext](https://github.com/joevt/directhw), or kext-free | `DirectHW` user-client, or `IOPCIBridge` Mach service (`--iopci`, tuning only) |
| Intel | n/a | Not supported | None |

> [!NOTE]
> On Linux, direct PCI config space access works without external kernel modules on standard configurations. If kernel lockdown is active (such as under UEFI Secure Boot), the Linux kernel blocks raw PCI access from userspace; installing the signed [ryzen_smu](https://github.com/amkillam/ryzen_smu) driver provides the required sysfs communication path.

> [!WARNING]
> ZenMaster communicates directly with the processor System Management Unit. Specifying voltages, currents, or power limits outside the operating parameters of your cooling subsystem or silicon can trigger thermal throttling, system resets, or hardware instability.

---

## Quick Start

### Linux

```bash
pip install zenmaster

# Display detected processor family, CCD count, mailbox type, and supported tuning count
sudo zenmaster --info

# Apply power limits and thermal limits
sudo zenmaster --stapm-limit=15000 --fast-limit=20000 --slow-limit=18000 --tctl-temp=90

# Monitor live per-core clocks and power table telemetry
sudo zenmaster --sensors
```

### Windows

Install [PawnIO](https://github.com/namazso/PawnIO.Setup/releases/latest/download/PawnIO_setup.exe), restart the system, and execute commands from an Administrator terminal:

```bat
pip install zenmaster

zenmaster --info
zenmaster --stapm-limit=15000 --fast-limit=20000 --slow-limit=18000 --tctl-temp=90
zenmaster --table
```

### macOS (AMD Hackintosh)

Requires `DirectHW.kext` for full features, or `--iopci` for kext-free tuning:

```bash
pip3 install zenmaster

sudo zenmaster --info
sudo zenmaster --stapm-limit=15000 --fast-limit=20000 --slow-limit=18000 --tctl-temp=90

# Kext-free tuning mode via IOPCIBridge
sudo zenmaster --iopci --stapm-limit=15000 --fast-limit=20000
```

---

## Library Usage

ZenMaster is structured as an importable Python library with typed interfaces (`py.typed`).

```python
import zenmaster
from zenmaster import detect, apply, smu, read_smn, write_smn, get_ccd_count
from zenmaster.exceptions import ZenMasterError, BackendUnavailable, SMUNotInitialized

# Detect CPU family, CPUID, CCD topology, and SMU mailbox protocol
info = detect()
print(f"Family: {info.family.name}")
print(f"Mailbox: {info.family.mailbox_type}")
print(f"Physical CCDs: {get_ccd_count()}")
print(f"Available tuning args: {len(info.family.args)}")

# Initialize the platform hardware driver
try:
    smu.init()
except BackendUnavailable as exc:
    print(f"Initialization failed: {exc}")
    raise SystemExit(1)

# Apply SMU settings
results, rejected = apply("--stapm-limit=15000 --fast-limit=20000 --tctl-temp=90", info.family)

for r in results:
    status_str = smu.status_name(r["status"])
    print(f"{r['arg']}: {status_str} (0x{r['status']:02X})")

if rejected:
    print(f"Rejected unsupported arguments: {rejected}")

# Low-level direct SMN access (synchronized via named PCI lock)
value = read_smn(0x0005A380)
print(f"SMN 0x0005A380 = 0x{value:08X}")
```

### Library Architecture Highlights

- **Typed Exceptions**: Root exception `ZenMasterError` (subclass of `RuntimeError`) with derived types `BackendUnavailable`, `SMUNotInitialized`, `UnsupportedCPU`, `SMUTimeoutError`, and `PMTableError`.
- **Direct SMN Operations**: `read_smn(address)` and `write_smn(address, value)` expose serialized access to the System Management Network bus.
- **Hardware Introspection**: `detect()` returns a `CpuInfo` object containing CPUID model, stepping, package socket, and the detected `CpuFamily`.
- **Top-Level Exports**: 53 functions and classes exported from `zenmaster`, with specialized submodules available in `zenmaster.sensors` (alias `zenmaster.table`) and `zenmaster.iopci` (aliases `zenmaster.iokit`, `zenmaster.iokitcore`).

---

## Technical Comparison: ZenMaster vs. RyzenAdj

| Feature | RyzenAdj | ZenMaster v1.2.0 |
|---|---|---|
| **Installation** | Compilation from source (`cmake`, `make`, `libpci-dev`) | `pip install zenmaster` (pure Python package) |
| **Supported Families** | ~15 APU and desktop families | 44 families (Zen 1 to Zen 5/6, Desktop, Mobile, Threadripper, Server EPYC via HSMP) |
| **Windows Driver** | WinRing0 (`OlsApi.dll`) ⚠️ | PawnIO (`PawnIO.sys`) ✅ |
| **Windows Driver Security** | Known vulnerabilities ([CVE-2020-14979](https://nvd.nist.gov/vuln/detail/CVE-2020-14979), [CVE-2021-41285](https://nvd.nist.gov/vuln/detail/CVE-2021-41285)); unprivileged physical memory read/write | Microsoft-signed, IOCTL boundary validation, zero arbitrary physical memory access |
| **Process Synchronization** | None; uncoordinated concurrent PCI config space access | Named cross-process mutex (`/run/lock/access_pci.lock` on Linux, `Global\Access_PCI` on Windows) |
| **CLI `--help`** | Static output listing all arguments across all generations | Dynamic; queries CPUID and displays only arguments implemented for detected CPU |
| **Curve Optimizer** | Basic per-core integer pass-through | Multi-token per-core/CCD targeting (`--set-coper=core:val`, `ccd:core:val`, `ccd:ccx:core:val`) with 20-bit encoding |
| **Server Support** | None | AMD EPYC 7002/7003/9004/9005 series via Host System Management Port (HSMP, `0x3B10A8C`) |
| **PM Table Telemetry** | Unlabeled floating-point array dump | Labeled field decoder (`--table`), curses live monitor (`--sensors`), and binary export (`--dump-table`) across 28 structs |
| **macOS Support** | Partial (DirectHW only) | Full DirectHW support plus kext-free `IOPCIBridge` user-client fallback (`--iopci`) |
| **Library Embedding** | Link C shared library or fork subprocess | `import zenmaster` with full type annotations (`py.typed`) |

---

## Supported Processor Families

ZenMaster supports 44 AMD Zen CPU architectures spanning client, mobile, workstation, and enterprise platforms:

- **Zen 1 / Zen+**: Summit Ridge, Pinnacle Ridge, Raven Ridge, Picasso
- **Zen 2**: Matisse, Castle Peak (Threadripper), Rome (EPYC), Renoir, Lucienne, Van Gogh (Steam Deck), Mendocino
- **Zen 3 / Zen 3+**: Vermeer, Chagall (Threadripper), Milan (EPYC), Cezanne, Barcelo, Rembrandt, Rembrandt+, Dragon Crest
- **Zen 4 / Zen 4c**: Raphael, Genoa / Bergamo (EPYC), Storm Peak (Threadripper), Phoenix, Phoenix 2, Hawk Point, Dragon Range
- **Zen 5 / Zen 5c / Zen 6**: Granite Ridge, Turin (EPYC), Strix Point, Strix Halo, Fire Range, Krackan Point, Medusa, Olympic Ridge
- **Hygon Dhyana**: Chinese x86 Zen 1 derivative architecture

Run `zenmaster --info` to determine the detected family, mailbox architecture, CCD configuration, and PM table version of your system.

---

## Updating

```bash
pip install -U zenmaster
```

To check PyPI for a newer release without upgrading:

```bash
zenmaster --version
```

Programmatic version checks can be executed via `zenmaster.check_update()`.

---

## Acknowledgments

| Project | Contribution |
|---|---|
| [RyzenAdj](https://github.com/FlyGoat/RyzenAdj) | Originating project for AMD SMU parameter naming and opcode semantics |
| [Universal x86 Tuning Utility](https://github.com/JamesCJ60/Universal-x86-Tuning-Utility) | SMU opcode references, PawnIO driver integration architecture, and family detection patterns |
| [ZenTune](https://github.com/HorizonUnix/ZenTune) | Reference Linux backend implementation, hardware detection matrices, and sysfs interfaces |
| [ryzen_smu](https://github.com/amkillam/ryzen_smu) | Linux kernel driver module for out-of-tree SMU mailbox communication |
| [PawnIO](https://github.com/namazso/PawnIO) | Modern Microsoft-signed Windows kernel driver interface |
| [DirectHW](https://github.com/joevt/directhw) | macOS kernel extension for physical memory and PCI config space operations (joevt) |
| [pciutils](https://github.com/joevt/pciutils) | Implementation of the `darwin2` IOPCIBridge user-client method enabling kext-free macOS access (joevt) |
