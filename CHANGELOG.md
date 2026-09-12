# Changelog

## [1.2.0] - 2026-09-12

Most changes in this release originate from UXTU v26.3.x & [ryzen_smu](https://github.com/amkillam/ryzen_smu)

### Added
- New CPU family and architecture support:
  - Enterprise, server, and workstation: Naples, Rome, Milan, Genoa, Bergamo, Siena, Turin, TurinDense (EPYC), Threadripper (1000/2000), Colfax (2990WX), CastlePeak (TR 3000), Chagall (TR 5000), and StormPeak (TR 7000).
  - Mobile and embedded APUs: FireFlight, RavenRidge2, Pollock (distinguished from Dali via brand string), SonomaValley, Medusa1, OlympicRidge, and Medusa2.
  - Licensed Zen 1 derivative: Hygon Dhyana (CPUID Family 24 / `0x18`) mapped to `SOCKET_AM4_V1`.
- Dynamic CCD count detection (`smu.get_ccd_count()`): reads SMN fuse registers (`0x5D218` / `0x5D21C`) to detect active CCD count on multi-CCD chips.
- Cross-process PCI mutex synchronization to prevent race conditions with external tools.
- HSMP mailbox interface (`SOCKET_FP10_AM5`): added mailbox registers (`0x3B10A8C`, `0x3B10A90`, `0x3B10A94`) and `send_hsmp()` / `query_hsmp()`
- New SMU tuning arguments and controls:
  - HSMP power and frequency limits: `fast-spm-limit`, `slow-spm-limit`, `core-power-limit-offset`, `fclk-overclock-on-the-fly`, `cclk-fmax-offset`, `extra-psm-guardband`, `extra-psm-guardband-gfx`, `fit-limit-scalar`, `disable-gpuclockoverdrive`.
  - HSMP and SMU mailbox queries: `get-smu-version`, `get-interface-version`, `get-metrics-table-version`, `get-metrics-table`, `get-metrics-table-dram-address`, `get-coper`, `get-cogfx`, `get-core-performance-order`, and `test`.
  - Dedicated socket command tables for `SOCKET_AM5_MOBILE` (Dragon Range) and `SOCKET_AM5_FIRERANGE` (Fire Range).
- Expanded PM table coverage:
  - Populated `PM_TABLE_CMDS` for 26 additional CPU families across desktop, server, and APUs.
  - Added 28 new PM table struct sizes in `TABLE_SIZES`
- CLI improvements:
  - `--info` and `--info --json` show active CCD count, decoded CPUID (family/model/stepping in decimal and hex), PM table version and buffer size, Secure Boot state, supported tuning commands count, and active mailbox protocol.
  - Added `tctl-limit` alias to `tctl-temp`.

### Changed
- Renamed `zenmaster/table.py` to `zenmaster/sensors.py`. Aliased in `sys.modules["zenmaster.table"]` and top-level `table = sensors` for backward compatibility.
- macOS backend: replaced `iokitcore.py` with modular `iopci.py` and `iokit.py` (w/ `sys.modules["zenmaster.iokitcore"]` backward-compatible alias).
- Updated bundled Windows `RyzenSMU.bin` driver binary.
- Curve Optimizer argument encoding:
  - Negative `--set-coall` offsets are converted to 20-bit two's complement automatically.
  - `--set-coper` supports `core:val`, `ccd:core:val`, and `ccd:ccx:core:val` notation, packing the CCD/CCX/core bitfields directly into SMU Arg0.
  - HSMP Curve Optimizer offsets automatically map to signed 16-bit PSM margin and APIC ID routing.
  - `--oc-clk-per-core` packs core, CCX, CCD, and frequency into SMU Arg0.
- Automatic unit scaling in `apply()`: `tctl-temp` millidegrees (values >= 1000 divided by 1000) and HSMP `pbo-scalar` (values >= 100 divided by 10).

### Fixed
- Dragon Range and Fire Range command tables: removed unsupported `vrmsoc-current` and `vrmsocmax-current` opcodes to prevent SMU rejection errors.
- Guarded `apu-skin-temp` execution in `apply()` to only run on APU families that expose the skin temperature mailbox, preventing timeouts on desktop and unsupported chips.

## [1.1.1] - 2026-07-15

- The `Rembrandt` codename should be model `64` or `68` (previously it was `63` or `68`).
- Added additional implementation from [FlyGoat/RyzenAdj PR #408](https://github.com/FlyGoat/RyzenAdj/pull/408).

## [1.1.0] - 2026-07-14

Most changes in this release originate from [FlyGoat/RyzenAdj PR #408](https://github.com/FlyGoat/RyzenAdj/pull/408).

### Added
- Direct `/dev/mem` fallback read path when `ryzen_smu` driver is loaded but `pm_table` sysfs nodes are unavailable on Linux.
- SMU BIOS Interface and Firmware Version mailbox queries (`0x03` and `0x02` respectively), with Linux sysfs version checking fallback. These versions are included in `--info` and `--info --json` output.
- Per-core metrics decoding from the PM table (power, voltage, temp, clock, effective clock, and C0/CC1/CC6 residencies) and exposed in a new tabular readout under `zenmaster --sensors` and as a `cores` array in JSON output.
- Custom iGPU/GFX telemetry registers (`gfx_power` and `gfx_volt`) and aligned Strix Point temperature offsets (`0x4B8`) in table decoding.

### Changed
- Renamed parameter `per-core-oc-clk` to `oc-clk-per-core` across command tables.

### Fixed
- Reverted Curve Optimizer encoding logic for Strix Point APU mobile curve to legacy 16-bit format, fixing mobile curve application errors.
- Removed invalid RSMU `apu-skin-temp` command definitions on FT5/FT6 families to avoid RSMU response delays.

## [1.0.0] - 2026-07-04

ZenMaster is stable. The public API is frozen going forward. Here's everything it does at this point.

### Cross-platform SMU access
- Linux: PCI direct access with no kernel module needed on most systems; `ryzen_smu` when Secure Boot is on, with version checking (`>= 0.1.7`) and Secure Boot detection
- Windows: PawnIO, a modern Microsoft-signed driver, instead of RyzenAdj's WinRing0 (which has known CVEs)
- macOS (AMD Hackintosh): DirectHW.kext, or a kext-free fallback through IOKit's `IOPCIBridge` (tuning only, no PM table), forced with `--iopci`
- One shared mailbox protocol (`mailbox.py`) underneath all three: MP1 and RSMU channels, per-family register addresses, retry-on-busy handling

### CPU support
- Summit Ridge (Zen 1) through Ryzen 9000 and Strix Halo, APU and desktop
- `detect()` reads the real CPU (`/proc/cpuinfo`, `PROCESSOR_IDENTIFIER`, or `sysctl`) into a `CpuInfo`; `resolve()` builds one from explicit family/model values without touching hardware
- Family-to-socket-to-opcode-table dispatch, so `--help` and `runner.get_supported_args()` only ever show what your specific CPU actually has

### CLI
- Same `--name=value` argument names and semantics as RyzenAdj, existing scripts and presets work unmodified
- `--info` / `--info --json`: CPU, socket, backend, and driver status
- `--table` / `--dump-table`: labeled or raw PM table dump
- `--sensors`: compact live readout (temp, load, socket power, iGPU clock/temp, memory clock)
- `--reapply=N`: keep re-applying a preset every N seconds in the foreground
- `--version`: installed version, plus a PyPI check for a newer release
- `--iopci` (macOS only): force the kext-free path
- `--json` on every read-oriented flag, for scripting

### Library API
- `apply()` / `ApplyResult`, `detect()` / `resolve()` / `CpuInfo`, and the full `smu` surface (`init`, `close`, `ensure_backend`, `send_mp1`/`send_rsmu`/`query_mp1`/`query_rsmu`, `read_pm_table`/`read_pm_table_version`/`read_pm_table_full`, `module_status`, `secure_boot_enabled`, `is_available`, `driver_name`, `active_backend`, `unavailable_reason`, `send_arg`) are all re-exported at the top level, `import zenmaster` gets you everything without reaching into submodules
- `table.read_sensors()` / `PmSensors` for decoding PM table bytes you already have; `check_update()` for the same version check the CLI does
- Typed exception hierarchy: `ZenMasterError` (a `RuntimeError`) with `BackendUnavailable`, `SMUNotInitialized`, `UnsupportedCPU`; `BackendUnavailable` messages link straight to the wiki's Installation guide
- `py.typed` ships in the package, so type checkers see real signatures

### PM table and sensors
- Labeled table decoding across every VRM (v1/v2/v3) and Tctl (v1/v2) layout AMD has shipped, covering Raven/Picasso-era APUs through current parts
- One mailbox round trip per read: `read_pm_table_full()` fetches version, address, and data together, and `read_pm_table()` / `read_pm_table_version()` / `read_pm_sensors()` all call into it instead of each redoing the sequence

### Packaging and quality
- Zero mandatory third-party dependencies, on any platform
- `pip install zenmaster`, no cmake, no libpci, no build step
- Test suite covering every backend (Linux, Windows, macOS) and module
- GPL-3.0 licensed; full wiki documentation (Installation, CLI Usage, Tuning Arguments, PM Table and Monitoring, Library API, architecture, troubleshooting, FAQ)

## [0.6.0] - 2026-07-02

### Added
- `CpuInfo.cpu_stepping_int` (defaults to `0`). `resolve()` takes it as an optional arg and `detect()` fills it in on all three platforms
- `zenmaster.init()` re-exported at top level.
- `smu.read_pm_table_full(family)`. Every backend was running the full mailbox sequence twice per `read_pm_sensors()` call: once for `read_pm_table()`, once again for `read_pm_table_version()`, because they were written as two separate functions that each redid the same version/address/transfer round trip. Now there's one fetch, and both older functions call into it.
- Linux `ModuleStatus.reason` can be `not_installed` or `unsigned` now, not just `not_loaded`. Previously "never installed," "installed but unsigned," and "installed but idle" all collapsed into the same reason, so anyone consuming this had to shell out to `modinfo` themselves to tell them apart.
- `smu.close()` (also at top level as `zenmaster.close()`) releases whatever the active backend is holding: the Windows PawnIO handle, macOS's DirectHW/IOKit connection, or the Linux SMU file descriptor. Nothing closed these before; a long-running process (a daemon that wants to drop and reacquire access) had no way to let go of them.
- More of `smu`'s surface is re-exported at the top level: `active_backend`, `pm_table_supported`, `send_mp1`, `send_rsmu`, `query_mp1`, `query_rsmu`, `read_pm_table`, `read_pm_table_version`, `read_pm_table_full`. The CLI already needed all of these; now `import zenmaster` gets you the same surface without dropping down to `zenmaster.smu`.
- `BackendUnavailable` now appends a link to the wiki's Installation guide to whatever message it's raised with. Every "PawnIO isn't installed" / "ryzen_smu is too old" / "DirectHW isn't loaded" error now points somewhere with the actual setup steps, instead of leaving you to go find them.

### Removed
- `AMDFamily0F.bin`, `AMDFamily10.bin`, `AMDFamily17.bin`, `AMDReset.bin`.

### Changed
- `send_arg()` raises `UnsupportedCPU` for a family with no SMU support.
- `send_arg()` no longer swallows every exception as a hardware rejection. Only `OSError`, `struct.error`, and `ctypes.ArgumentError` count as SMU_FAILED now. A real bug in a backend used to look identical to the SMU just saying no.
- CLI shows help instead of doing nothing when you run it with no action flag and no tuning args. `zenmaster --json` by itself used to just exit 0 silently.
- `hardware.detect()` caches its result for the life of the process. It used to re-parse `/proc/cpuinfo`, `PROCESSOR_IDENTIFIER`, or `sysctl` and recompute the codename on every single call, which is why callers (U4L included) kept building their own memoization around it. `resolve()` is untouched and still takes whatever you pass it every time, since that's the one meant for feeding in values you didn't read off the real CPU.
- The mailbox send/query/poll/retry logic that macOS and Windows each had their own near-identical copy of now lives once in `zenmaster/mailbox.py`. Linux already shared its two backends this way; the other two platforms didn't.
- All three backends now check "has `init()` run yet" the same way: a bare `_require_init()` guard called at the top of `send_mp1`/`send_rsmu`/`query_mp1`/`query_rsmu`, raising `SMUNotInitialized` before any hardware I/O happens.

### Fixed
- Windows: the PawnIO registry lookup (`_pawnio_info`) was a separate registry read for `module_version()`, `module_version_ok()`, `module_status()`, and `is_available()` each. It's read once and cached now.
- Windows: `read_pm_table_full` didn't check for a zero table version, unlike Linux and macOS, so a rejected version query could fall through and read from a garbage address instead of returning `None`.
- `apply()` now counts an unparseable value (`--stapm-limit=notanumber`) as a rejection. It already returned an error result for this case, but `had_rejection` stayed `False`, so a caller only checking that flag would think the preset applied cleanly.

## [0.5.0] - 2026-07-01

### Added
- macOS backend (AMD Hackintosh): CPU detection via `sysctl`, and SMU access through DirectHW.kext, with a kext-free fallback over IOPCIBridge (tuning only, no PM table)
- CLI `--iopci` (macOS only) forces the IOPCIBridge path instead of DirectHW
- `zenmaster.hardware.detect()` reads `machdep.cpu.family` / `machdep.cpu.model` / `machdep.cpu.brand_string` on macOS instead of `/proc/cpuinfo`

### Changed
- `--info` (text and `--json`) omits the `Backend`/`Driver` fields entirely when the SMU hasn't been initialized, instead of printing "not initialized"
- `--table`, `--dump-table`, and `--sensors` point to DirectHW.kext specifically when they fail on the IOPCIBridge path, instead of a generic "not available" message

## [0.4.0] - 2026-06-30

### Added
- CLI `--sensors` (and `--sensors --json`): compact live readout of temp, load, socket power, iGPU clock/temp, and memory clock
- CLI `--info` now shows a `Driver` line with the driver name, version, and status (or `PCI direct access`); same data under `--info --json`
- `smu.read_pm_sensors(family)` reads and decodes the PM table in one call, returning a `PmSensors` (or `None`). `table.read_sensors(data, ver)` decodes raw bytes you already have
- `smu.module_status()` returns one `ModuleStatus` verdict for the driver (`ok`, `version`, `min_version`, `reason`). Helpers: `module_version()`, `module_version_ok()`, `is_available()`, `secure_boot_enabled()`, `driver_name()`
- `smu.ensure_backend()`: like `init()` but returns the backend or `None` instead of raising
- `smu.unavailable_reason()`: the message explaining why the SMU can't be used, or `None` when it can
- `smu.send_arg(family, name, value)` sends one value to every mailbox the arg maps to, returning `[(mailbox, opcode, status), ...]`
- `resolve(name, cpu_family, cpu_model)` builds a `CpuInfo` from explicit values without reading `/proc/cpuinfo`
- `runner.is_supported(family)`
- All of the above are re-exported at the top level, so apps don't import from `zenmaster.linux`

### Changed
- Linux now checks the `ryzen_smu` version (`drv_version`) and requires `>= 0.1.7`, with the installed version in the error
- Backend selection follows Secure Boot: off uses PCI direct access, on uses `ryzen_smu`. A loaded module is no longer preferred over PCI when Secure Boot is off
- On Windows, the driver is PawnIO with no version requirement, and Secure Boot does not apply

## [0.3.0] - 2026-06-30

### Added
- `get-*` query commands now return the value the SMU reports, shown in the CLI and in `--json` as a `returned` field; `smu.query_mp1()` / `smu.query_rsmu()` expose the raw read-back for library users
- `--version` flag, which prints the installed version and checks PyPI for a newer release; `zenmaster.check_update()` exposes the same check to library users
- Exception hierarchy for library users: `ZenMasterError` (base) with `BackendUnavailable`, `SMUNotInitialized`, `UnsupportedCPU`, all still subclass `RuntimeError`, so existing `except RuntimeError` keeps working
- `smu.SmuStatus` IntEnum for SMU status codes (`SMU_OK` etc. now alias it)
- `ApplyResult` TypedDict documenting the `apply()` result contract
- `py.typed` marker so downstream type-checkers use the bundled type hints
- PM-table support for the Raven/Picasso-era APUs (RavenRidge, Picasso, Dali, Pollock), which use a distinct table opcode set
- Linux can now read the PM table over PCI direct access (via `/dev/mem`) when `ryzen_smu` is not loaded

### Changed
- `tdc-limit` and `edc-limit` now have descriptions and appear under "VRM & Currents" in `--help` instead of "Unknown command"
- Moved the MP1/RSMU mailbox tables, SMU status codes, and PM-table metadata into shared modules (`mailbox.py`, `pmtable.py`)
- Unified the Linux register send/poll path into one routine shared by the `ryzen_smu` and PCI backends; simplified `apply()` token parsing
- Removed unused `runner` helpers (`get_socket_short`, `has_smu_support`, `get_commands`)

### Fixed
- Windows `--table` / `--dump-table` now work on VanGogh (Steam Deck) and Mendocino, which were missing from the PM-table family list

## [0.2.0] - 2026-06-30

### Added
- Public library API: `from zenmaster import detect, apply, runner, smu, CpuInfo`
- `runner.is_flag_arg()` to query args that take no value
- `vrmcvip-current` (VanGogh) for full RyzenAdj arg parity

### Changed
- Linux PCI backend now probes writability with a `0x47` register round-trip
  (like UXTU4Linux) instead of only checking that the config file exists, so a
  non-writable bus (no root, lockdown) fails at init with a clear message
- Unified project description to "Adjust power management settings for Ryzen
  CPUs on Linux and Windows"
- Rewrote README with a fuller overview, compatibility table, and an accurate
  RyzenAdj comparison
- Args that require a value now report an error (or show help on the CLI)
  when passed without `=value`, instead of silently sending 0
- `apply()` results always include a consistent set of keys (`error` is
  `None` on success), making the return shape stable for consumers
- Argument names are normalized to lowercase/hyphen form in `apply()` results
- Modernized packaging to PEP 639 SPDX license metadata

### Fixed
- Windows PM table read now aborts if the final table-transfer retry is still
  rejected, instead of reading stale/garbage physical memory
- Windows SMU polling sleeps briefly after a fast initial spin, avoiding a busy
  loop that pinned a core while waiting for the mailbox
- `--skin-temp-limit` (a power limit in mW) is no longer multiplied by 256;
  only the temperature args `apu-skin-temp` and `dgpu-skin-temp` are scaled,
  matching RyzenAdj
- Negative values (e.g. Curve Optimizer `--set-coall=-20`) now wrap to
  unsigned 32-bit like RyzenAdj, instead of being clamped to 0
- Flag args (`--max-performance`, `--enable-oc`, …) always send 0, ignoring any
  value passed, matching RyzenAdj's boolean handling
- `smu.send_*` now raise a clear error if called before `smu.init()`
- `smu.init()` is idempotent and no longer leaks the Windows PawnIO handle
- CLI shows help for a malformed argument before requiring root
- `apply()` handles malformed preset strings (unclosed quotes) gracefully
- `--table` no longer shows duplicate TDC values in EDC rows on Zen 5 tables

## [0.1.1] - 2026-06-30

### Fixed
- Workflow and packaging fixes for initial PyPI release

## [0.1.0] - 2026-06-29

### Added
- Initial release
- Cross-platform AMD Ryzen SMU power management for Linux and Windows
- Dynamic `--help` showing only args supported by the detected CPU
- `--table` for labeled live PM table (temps, power, currents)
- `--json` for machine-readable output
- `--reapply=N` to continuously re-apply a preset
- `--info` to show CPU family, socket, and active backend
- Linux backends: `ryzen_smu` kernel module and PCI direct access
- Windows backend: PawnIO (replaces WinRing0 used by RyzenAdj)
- Embeddable Python library — `import zenmaster`
- Zero mandatory dependencies
