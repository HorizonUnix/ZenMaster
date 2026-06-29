# Changelog

## [0.1.1] - 2026-06-29

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
