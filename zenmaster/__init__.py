import sys
from importlib.metadata import version, PackageNotFoundError

from zenmaster import runner, smu, sensors, iokit
table = sensors
iokitcore = iokit
sys.modules["zenmaster.table"] = sensors
sys.modules["zenmaster.iokitcore"] = iokit
from zenmaster.hardware import CpuInfo, detect, resolve
from zenmaster.apply import apply, ApplyResult
from zenmaster.update import check_update
from zenmaster.sensors import PmSensors, read_sensors, CoreSensors, read_core_sensors
from zenmaster.smu import (
    SmuStatus, ModuleStatus, module_status, module_version, module_version_ok,
    secure_boot_enabled, is_available, init, close, ensure_backend, read_pm_sensors,
    send_arg, unavailable_reason, driver_name, active_backend, pm_table_supported,
    send_mp1, send_rsmu, send_hsmp, query_mp1, query_rsmu, query_hsmp,
    read_pm_table, read_pm_table_version, read_pm_table_full,
    get_bios_if_ver, get_smu_version, format_smu_version, read_pm_core_sensors,
    read_smn, write_smn, get_ccd_count,
)
from zenmaster.errors import (
    ZenMasterError, BackendUnavailable, SMUNotInitialized, UnsupportedCPU,
)

try:
    __version__ = version("zenmaster")
except PackageNotFoundError:
    __version__ = "1.2.1"

__all__ = [
    "CpuInfo", "detect", "resolve", "apply", "ApplyResult", "runner", "smu", "sensors", "table",
    "iokit", "iokitcore",
    "SmuStatus", "PmSensors", "read_sensors", "read_pm_sensors",
    "ModuleStatus", "module_status", "module_version", "module_version_ok",
    "secure_boot_enabled", "is_available", "init", "close", "ensure_backend",
    "send_arg", "unavailable_reason", "driver_name", "active_backend",
    "pm_table_supported", "send_mp1", "send_rsmu", "send_hsmp", "query_mp1",
    "query_rsmu", "query_hsmp", "read_pm_table", "read_pm_table_version",
    "read_pm_table_full", "get_bios_if_ver", "get_smu_version", "format_smu_version",
    "CoreSensors", "read_core_sensors", "read_pm_core_sensors", "check_update",
    "read_smn", "write_smn", "get_ccd_count",
    "ZenMasterError", "BackendUnavailable", "SMUNotInitialized", "UnsupportedCPU",
    "__version__",
]
