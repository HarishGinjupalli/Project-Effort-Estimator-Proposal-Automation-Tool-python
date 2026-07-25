"""
Unit tests for column_mapper.py
Covers: auto-detection across differently-named CSVs, explicit overrides,
missing-column error reporting, and normalization.
"""

import pandas as pd
import pytest

from src.column_mapper import resolve_columns, normalize_dataframe, ColumnMappingError


def test_resolve_columns_auto_detect_standard_schema():
    df = pd.DataFrame(columns=["requirement_id", "requirement_description", "role", "complexity"])
    resolved = resolve_columns(df)
    assert resolved == {
        "requirement_id": "requirement_id",
        "description": "requirement_description",
        "role": "role",
        "complexity": "complexity",
    }


def test_resolve_columns_auto_detect_alternate_schema():
    # Mirrors the enterprise digital-transformation dataset's column names
    df = pd.DataFrame(
        columns=[
            "requirement_id", "epic", "module", "requirement_title",
            "requirement_description", "business_priority", "complexity",
            "estimated_story_points", "assigned_role", "technology",
        ]
    )
    resolved = resolve_columns(df)
    assert resolved["requirement_id"] == "requirement_id"
    assert resolved["description"] == "requirement_description"
    assert resolved["role"] == "assigned_role"
    assert resolved["complexity"] == "complexity"


def test_resolve_columns_case_insensitive():
    df = pd.DataFrame(columns=["Requirement_ID", "Requirement_Title", "Role", "Complexity"])
    resolved = resolve_columns(df)
    assert resolved["requirement_id"] == "Requirement_ID"
    assert resolved["description"] == "Requirement_Title"


def test_resolve_columns_explicit_override():
    df = pd.DataFrame(columns=["req_num", "notes", "owner", "size_tier"])
    resolved = resolve_columns(
        df, id_col="req_num", desc_col="notes", role_col="owner", complexity_col="size_tier"
    )
    assert resolved == {
        "requirement_id": "req_num",
        "description": "notes",
        "role": "owner",
        "complexity": "size_tier",
    }


def test_resolve_columns_override_column_not_found():
    df = pd.DataFrame(columns=["requirement_id", "requirement_description", "role", "complexity"])
    with pytest.raises(ColumnMappingError, match="doesn't exist"):
        resolve_columns(df, role_col="nonexistent_column")


def test_resolve_columns_missing_required_field():
    df = pd.DataFrame(columns=["requirement_id", "description"])  # no role/complexity
    with pytest.raises(ColumnMappingError, match="role"):
        resolve_columns(df)


def test_normalize_dataframe_renames_and_preserves_extra_columns():
    df = pd.DataFrame(
        {
            "requirement_id": ["REQ-001"],
            "epic": ["Customer 360"],
            "requirement_title": ["Do the thing"],
            "assigned_role": ["Python Developer"],
            "complexity": ["High"],
        }
    )
    column_map = resolve_columns(df)
    normalized = normalize_dataframe(df, column_map)

    assert list(normalized["requirement_description"]) == ["Do the thing"]
    assert list(normalized["role"]) == ["Python Developer"]
    # Original columns not part of the mapping stay intact
    assert "epic" in normalized.columns
