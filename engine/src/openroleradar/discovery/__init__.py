"""Source discovery pipeline."""

from openroleradar.discovery.ats_detect import detect_ats, load_ats_hosts
from openroleradar.discovery.registry import SeedSource, load_seed_sources, seed_to_source
from openroleradar.discovery.validate import ValidationResult, validate_candidate

__all__ = [
    "SeedSource",
    "ValidationResult",
    "detect_ats",
    "load_ats_hosts",
    "load_seed_sources",
    "seed_to_source",
    "validate_candidate",
]
