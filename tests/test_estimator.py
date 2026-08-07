"""
Unit tests for estimator.py
Covers: single requirement estimate math, full build_estimate rollup,
unknown role/complexity errors, empty CSV handling.
"""

import pandas as pd
import pytest

from src.config_manager import RateCard
from src.estimator import (
    estimate_requirement,
    build_estimate,
    load_requirements,
    EstimationError,
)


@pytest.fixture
def rate_card():
    return RateCard(
        currency="INR",
        roles={"Python Developer": 8000, "Business Analyst": 9500},
        complexity_multiplier={"Low": 1.0, "Medium": 1.5, "High": 2.2},
        base_effort_days=2.0,
        risk_buffer_percent=10,
        overhead_percent=5,
        default_role_rate=9000,
        default_complexity="Medium",
    )


@pytest.fixture
def strict_rate_card():
    # No defaults configured -> unknown values should raise, even without --strict
    return RateCard(
        currency="INR",
        roles={"Python Developer": 8000},
        complexity_multiplier={"Low": 1.0, "Medium": 1.5, "High": 2.2},
        base_effort_days=2.0,
        risk_buffer_percent=10,
        overhead_percent=5,
    )


def test_estimate_requirement_basic(rate_card):
    row = pd.Series(
        {
            "requirement_id": "REQ-001",
            "requirement_description": "Build API",
            "role": "Python Developer",
            "complexity": "Medium",
        }
    )
    result = estimate_requirement(row, rate_card)
    # base_effort_days(2.0) * multiplier(1.5) = 3.0 person-days
    assert result.effort_days == 3.0
    # 3.0 days * 8000/day = 24000
    assert result.cost == 24000.0


def test_estimate_requirement_unknown_role_falls_back_to_default(rate_card):
    """With default_role_rate configured, an unrecognized role should not crash —
    it should price at the default rate and flag the estimate as defaulted."""
    row = pd.Series(
        {
            "requirement_id": "REQ-002",
            "requirement_description": "Unknown work",
            "role": "Data Scientist",  # not in rate_card
            "complexity": "Low",
        }
    )
    result = estimate_requirement(row, rate_card)
    assert result.role_was_defaulted is True
    assert result.daily_rate == rate_card.default_role_rate


def test_estimate_requirement_unknown_complexity_falls_back_to_default(rate_card):
    row = pd.Series(
        {
            "requirement_id": "REQ-003",
            "requirement_description": "Some work",
            "role": "Python Developer",
            "complexity": "Extreme",  # not in rate_card
        }
    )
    result = estimate_requirement(row, rate_card)
    assert result.complexity_was_defaulted is True
    assert result.effective_complexity == "Medium"
    # defaulted to "Medium" -> multiplier 1.5 -> 2.0 * 1.5 = 3.0 days
    assert result.effort_days == 3.0


def test_estimate_requirement_unknown_role_strict_mode_raises(rate_card):
    row = pd.Series(
        {
            "requirement_id": "REQ-004",
            "requirement_description": "Unknown work",
            "role": "Data Scientist",
            "complexity": "Low",
        }
    )
    with pytest.raises(EstimationError, match="Unknown role"):
        estimate_requirement(row, rate_card, strict=True)


def test_estimate_requirement_unknown_role_no_default_configured_raises(strict_rate_card):
    """Without default_role_rate set in the rate card at all, unknown roles
    should still raise even in non-strict mode — there's nothing to fall back to."""
    row = pd.Series(
        {
            "requirement_id": "REQ-005",
            "requirement_description": "Unknown work",
            "role": "Data Scientist",
            "complexity": "Low",
        }
    )
    with pytest.raises(EstimationError, match="Unknown role"):
        estimate_requirement(row, strict_rate_card)


def test_estimate_requirement_role_matching_is_case_insensitive(rate_card):
    row = pd.Series(
        {
            "requirement_id": "REQ-006",
            "requirement_description": "Case test",
            "role": "python developer",  # lowercase vs "Python Developer" in rate card
            "complexity": "low",
        }
    )
    result = estimate_requirement(row, rate_card)
    assert result.role_was_defaulted is False
    assert result.daily_rate == 8000


def test_build_estimate_rollup(rate_card):
    df = pd.DataFrame(
        [
            {
                "requirement_id": "REQ-001",
                "requirement_description": "Task A",
                "role": "Python Developer",
                "complexity": "Low",  # 2.0 days * 8000 = 16000
            },
            {
                "requirement_id": "REQ-002",
                "requirement_description": "Task B",
                "role": "Business Analyst",
                "complexity": "Medium",  # 3.0 days * 9500 = 28500
            },
        ]
    )
    summary = build_estimate(df, rate_card)

    assert summary.subtotal_effort_days == 5.0
    assert summary.subtotal_cost == 44500.0

    # risk buffer 10% of 44500 = 4450
    assert summary.risk_buffer_cost == 4450.0

    # cost with risk = 48950; overhead 5% of that = 2447.5
    assert summary.overhead_cost == 2447.5

    # grand total = 48950 + 2447.5 = 51397.5
    assert summary.grand_total == 51397.5
    assert len(summary.line_items) == 2


def test_load_requirements_missing_columns(tmp_path):
    bad_csv = tmp_path / "bad.csv"
    # 'id' auto-detects fine, but description/role/complexity can't be
    # guessed from these column names and no overrides are given.
    bad_csv.write_text("id,desc\n1,test\n")
    with pytest.raises(EstimationError, match="Couldn't auto-detect"):
        load_requirements(str(bad_csv))


def test_load_requirements_empty(tmp_path):
    empty_csv = tmp_path / "empty.csv"
    empty_csv.write_text(
        "requirement_id,requirement_description,role,complexity\n"
    )
    with pytest.raises(EstimationError, match="no rows"):
        load_requirements(str(empty_csv))


def test_load_requirements_valid(tmp_path):
    csv_path = tmp_path / "valid.csv"
    csv_path.write_text(
        "requirement_id,requirement_description,role,complexity\n"
        "REQ-001,Test task,Python Developer,Low\n"
    )
    df = load_requirements(str(csv_path))
    assert len(df) == 1
    assert df.iloc[0]["role"] == "Python Developer"


def test_load_requirements_blank_field_raises(tmp_path):
    csv_path = tmp_path / "blank_role.csv"
    csv_path.write_text(
        "requirement_id,requirement_description,role,complexity\n"
        "REQ-001,Test task,,Low\n",
        encoding="utf-8",
    )
    with pytest.raises(EstimationError, match="blank or missing"):
        load_requirements(str(csv_path))
