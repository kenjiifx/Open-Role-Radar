"""ATS adapter registry and exports."""

from openroleradar.adapters.ashby import AshbyAdapter, ashby_adapter
from openroleradar.adapters.base import (
    AdapterFetchResult,
    ATSAdapter,
    clear_adapter_registry,
    get_adapter,
    list_adapters,
    register_adapter,
)
from openroleradar.adapters.greenhouse import GreenhouseAdapter, greenhouse_adapter
from openroleradar.adapters.json_ld import JsonLdAdapter, json_ld_adapter
from openroleradar.adapters.lever import LeverAdapter, lever_adapter
from openroleradar.adapters.smartrecruiters import (
    SmartRecruitersAdapter,
    smartrecruiters_adapter,
)
from openroleradar.adapters.workday import WorkdayAdapter, workday_adapter

__all__ = [
    "ATSAdapter",
    "AdapterFetchResult",
    "AshbyAdapter",
    "GreenhouseAdapter",
    "JsonLdAdapter",
    "LeverAdapter",
    "SmartRecruitersAdapter",
    "WorkdayAdapter",
    "ashby_adapter",
    "clear_adapter_registry",
    "get_adapter",
    "greenhouse_adapter",
    "json_ld_adapter",
    "lever_adapter",
    "list_adapters",
    "register_adapter",
    "smartrecruiters_adapter",
    "workday_adapter",
]
