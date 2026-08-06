from importlib.metadata import version, PackageNotFoundError

from zenmaster import runner, smu, table
from zenmaster.hardware import CpuInfo, detect, resolve
from zenmaster.apply import apply, ApplyResult, make_psm_margin_arg, make_per_core_co_arg, make_curve_shaper_arg
from zenmaster.update import check_update
from zenmaster.table import PmSensors, read_sensors, CoreSensors, read_core_sensors
from zenmaster.timings import read_timings, decode_vendor, parse_apob_buffer
from zenmaster.smu import (
    SmuStatus, ModuleStatus, module_status, module_version, module_version_ok,
    secure_boot_enabled, is_available, init, close, ensure_backend, read_pm_sensors,
    send_arg, unavailable_reason, driver_name, active_backend, pm_table_supported,
    send_mp1, send_rsmu, query_mp1, query_rsmu,
    read_pm_table, read_pm_table_version, read_pm_table_full,
    get_bios_if_ver, get_smu_version, format_smu_version, read_pm_core_sensors,
)
from zenmaster.errors import (
    ZenMasterError, BackendUnavailable, SMUNotInitialized, UnsupportedCPU,
)

try:
    __version__ = version("zenmaster")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = [
    "CpuInfo", "detect", "resolve", "apply", "ApplyResult", "runner", "smu", "table",
    "SmuStatus", "PmSensors", "read_sensors", "read_pm_sensors", "ModuleStatus",
    "module_status", "module_version", "module_version_ok", "secure_boot_enabled",
    "is_available", "init", "close", "ensure_backend", "send_arg", "unavailable_reason",
    "driver_name", "active_backend", "pm_table_supported", "send_mp1", "send_rsmu",
    "query_mp1", "query_rsmu", "read_pm_table", "read_pm_table_version", "read_pm_table_full",
    "get_bios_if_ver", "get_smu_version", "format_smu_version",
    "CoreSensors", "read_core_sensors", "read_pm_core_sensors",
    "read_timings", "decode_vendor", "parse_apob_buffer",
    "make_psm_margin_arg", "make_per_core_co_arg", "make_curve_shaper_arg",
    "check_update", "ZenMasterError", "BackendUnavailable", "SMUNotInitialized",
    "UnsupportedCPU", "__version__",
]
