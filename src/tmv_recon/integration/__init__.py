"""Excel → Tally integration: column mapping, row→voucher pipeline, validation."""
from .mapping import ColumnMap, Field, EntryMap, from_dict, from_yaml, load_preset
from .pipeline import build
from .validators import validate, has_errors, Issue

__all__ = [
    "ColumnMap", "Field", "EntryMap",
    "from_dict", "from_yaml", "load_preset",
    "build", "validate", "has_errors", "Issue",
]
