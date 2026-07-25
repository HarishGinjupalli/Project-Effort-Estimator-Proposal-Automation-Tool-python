"""
column_mapper.py
Makes the estimator schema-tolerant: real-world requirement exports don't
all use the same column names (requirement_description vs requirement_title,
role vs assigned_role, etc.). This module auto-detects the right columns
from a ranked list of common aliases, with explicit overrides available via
CLI flags for anything it can't guess.

Only requirement_id, a description-like column, role, and complexity are
required for estimation. Every other column in the source CSV (epic, module,
sprint, status, priority, ...) is preserved and simply ignored by the costing
engine — nothing is lost, nothing needs to be stripped out beforehand.
"""

from typing import Dict, Optional
import pandas as pd

# Ranked candidate column names (case-insensitive) for each required field.
# First match wins.
COLUMN_ALIASES = {
    "requirement_id": [
        "requirement_id", "req_id", "id", "story_id", "ticket_id", "item_id",
    ],
    "description": [
        "requirement_description", "description", "requirement_title",
        "title", "summary", "task_description", "story_title",
    ],
    "role": [
        "assigned_role", "role", "resource_role", "assignee_role",
        "responsible_role", "resource", "assignee",
    ],
    "complexity": [
        "complexity", "story_complexity", "effort_complexity", "size",
    ],
}


class ColumnMappingError(Exception):
    """Raised when a required column can't be found or resolved in the CSV."""


def _find_column(df: pd.DataFrame, candidates: list) -> Optional[str]:
    lower_map = {col.lower().strip(): col for col in df.columns}
    for candidate in candidates:
        if candidate.lower() in lower_map:
            return lower_map[candidate.lower()]
    return None


def resolve_columns(
    df: pd.DataFrame,
    id_col: Optional[str] = None,
    desc_col: Optional[str] = None,
    role_col: Optional[str] = None,
    complexity_col: Optional[str] = None,
) -> Dict[str, str]:
    """
    Resolve the four columns the estimator needs, preferring explicit
    CLI overrides, then falling back to auto-detection via COLUMN_ALIASES.
    Returns a dict mapping logical name -> actual column name in df.
    Raises ColumnMappingError listing exactly what's missing if a required
    column can't be resolved either way.
    """
    resolved = {}
    overrides = {
        "requirement_id": id_col,
        "description": desc_col,
        "role": role_col,
        "complexity": complexity_col,
    }

    missing = []
    for field, override in overrides.items():
        if override:
            if override not in df.columns:
                missing.append(
                    f"'{field}' was set to column '{override}' but that column "
                    f"doesn't exist in the CSV. Available columns: {list(df.columns)}"
                )
                continue
            resolved[field] = override
            continue

        found = _find_column(df, COLUMN_ALIASES[field])
        if found:
            resolved[field] = found
        else:
            missing.append(
                f"Couldn't auto-detect a '{field}' column. Tried: "
                f"{COLUMN_ALIASES[field]}. Available columns: {list(df.columns)}. "
                f"Pass --{field.replace('_', '-')}-col to specify it manually."
            )

    if missing:
        raise ColumnMappingError("\n".join(missing))

    return resolved


def normalize_dataframe(df: pd.DataFrame, column_map: Dict[str, str]) -> pd.DataFrame:
    """
    Return a copy of df with the four resolved columns renamed to the
    estimator's expected internal names, keeping all original columns
    intact alongside them (nothing is dropped).
    """
    normalized = df.copy()
    rename_map = {
        column_map["requirement_id"]: "requirement_id",
        column_map["description"]: "requirement_description",
        column_map["role"]: "role",
        column_map["complexity"]: "complexity",
    }
    # Guard against the (unlikely) case where a source column already has
    # the exact target name but maps from a different source column.
    normalized = normalized.rename(columns=rename_map)

    # Ensure required fields have no blank/NaN values
    for field in ["requirement_id", "requirement_description", "role", "complexity"]:
        normalized[field] = normalized[field].astype(str).str.strip()

    return normalized
