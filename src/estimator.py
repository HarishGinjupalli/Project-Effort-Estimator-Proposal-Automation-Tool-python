"""
estimator.py
Core effort-estimation and costing engine.

Given a list of client requirements (role + complexity per requirement) and
a RateCard, this module calculates:
- person-days per requirement (base effort x complexity multiplier)
- cost per requirement (person-days x daily rate)
- a risk-buffered, overhead-adjusted grand total

This is intentionally pure/stateless: pass in data, get back structured
results. Makes it trivial to unit test and to swap the input source
(CSV today, could be a DB or API later) without touching this logic.
"""

from dataclasses import dataclass, field
from typing import List, Optional
import logging
import pandas as pd

from src.config_manager import RateCard
from src.column_mapper import resolve_columns, normalize_dataframe, ColumnMappingError

logger = logging.getLogger("estimator")


class EstimationError(Exception):
    """Raised when input requirement data can't be estimated against the rate card."""


@dataclass
class RequirementEstimate:
    requirement_id: str
    description: str
    role: str
    complexity: str
    effective_complexity: str
    effort_days: float
    daily_rate: float
    cost: float
    role_was_defaulted: bool = False
    complexity_was_defaulted: bool = False


@dataclass
class EstimateSummary:
    line_items: List[RequirementEstimate]
    subtotal_effort_days: float
    subtotal_cost: float
    risk_buffer_percent: float
    risk_buffer_cost: float
    overhead_percent: float
    overhead_cost: float
    grand_total: float
    currency: str
    unmapped_roles: List[str] = field(default_factory=list)
    unmapped_complexity: List[str] = field(default_factory=list)


def load_requirements(
    csv_path: str,
    id_col: Optional[str] = None,
    desc_col: Optional[str] = None,
    role_col: Optional[str] = None,
    complexity_col: Optional[str] = None,
) -> pd.DataFrame:
    """
    Load any reasonably-shaped requirements CSV. Column names for
    requirement id, description, role, and complexity are auto-detected
    from common aliases (see column_mapper.py); pass the *_col arguments
    to override detection for a specific CSV.
    """
    df = pd.read_csv(csv_path, encoding="utf-8-sig")

    if df.empty:
        raise EstimationError("Requirements CSV has no rows to estimate")

    try:
        column_map = resolve_columns(
            df, id_col=id_col, desc_col=desc_col, role_col=role_col, complexity_col=complexity_col
        )
    except ColumnMappingError as e:
        raise EstimationError(str(e))

    logger.info(
        f"Column mapping resolved -> id: '{column_map['requirement_id']}', "
        f"description: '{column_map['description']}', role: '{column_map['role']}', "
        f"complexity: '{column_map['complexity']}'"
    )

    try:
        return normalize_dataframe(df, column_map)
    except ColumnMappingError as e:
        raise EstimationError(str(e))


def _resolve_role_rate(role: str, rate_card: RateCard, strict: bool) -> tuple:
    """Return (daily_rate, was_defaulted). Case-insensitive match against rate_card.roles."""
    role_lookup = {r.lower(): r for r in rate_card.roles}
    if role.lower() in role_lookup:
        actual_role = role_lookup[role.lower()]
        return rate_card.roles[actual_role], False

    if strict or rate_card.default_role_rate is None:
        raise EstimationError(
            f"Unknown role '{role}'. Add it to rate_card.yaml, or set "
            f"default_role_rate in rate_card.yaml to allow fallback pricing, "
            f"or rerun without --strict."
        )
    return rate_card.default_role_rate, True


def _resolve_complexity_multiplier(complexity: str, rate_card: RateCard, strict: bool) -> tuple:
    """Return (multiplier, effective_complexity, was_defaulted). Case-insensitive match."""
    complexity_lookup = {c.lower(): c for c in rate_card.complexity_multiplier}
    if complexity.lower() in complexity_lookup:
        actual = complexity_lookup[complexity.lower()]
        return rate_card.complexity_multiplier[actual], actual, False

    if strict or rate_card.default_complexity is None:
        raise EstimationError(
            f"Unknown complexity '{complexity}'. Valid values: "
            f"{list(rate_card.complexity_multiplier.keys())}, or set default_complexity "
            f"in rate_card.yaml to allow fallback, or rerun without --strict."
        )
    default = rate_card.default_complexity
    return rate_card.complexity_multiplier[default], default, True


def estimate_requirement(row, rate_card: RateCard, strict: bool = False) -> RequirementEstimate:
    """
    Compute effort (person-days) and cost for a single requirement row.
    Unknown roles/complexity fall back to rate_card.default_role_rate /
    default_complexity (with the estimate flagged) unless strict=True,
    in which case unknown values raise EstimationError.
    """
    role = row["role"]
    complexity = row["complexity"]

    daily_rate, role_defaulted = _resolve_role_rate(role, rate_card, strict)
    multiplier, effective_complexity, complexity_defaulted = _resolve_complexity_multiplier(
        complexity, rate_card, strict
    )

    if role_defaulted:
        logger.warning(
            f"Requirement '{row['requirement_id']}': role '{role}' not found in rate card, "
            f"using default rate {rate_card.default_role_rate}."
        )
    if complexity_defaulted:
        logger.warning(
            f"Requirement '{row['requirement_id']}': complexity '{complexity}' not found, "
            f"defaulting to '{effective_complexity}'."
        )

    effort_days = round(rate_card.base_effort_days * multiplier, 2)
    cost = round(effort_days * daily_rate, 2)

    return RequirementEstimate(
        requirement_id=row["requirement_id"],
        description=row["requirement_description"],
        role=role,
        complexity=complexity,
        effective_complexity=effective_complexity,
        effort_days=effort_days,
        daily_rate=daily_rate,
        cost=cost,
        role_was_defaulted=role_defaulted,
        complexity_was_defaulted=complexity_defaulted,
    )


def build_estimate(df: pd.DataFrame, rate_card: RateCard, strict: bool = False) -> EstimateSummary:
    """Run estimate_requirement across all rows and roll up totals with risk buffer + overhead."""
    line_items = [estimate_requirement(row, rate_card, strict=strict) for _, row in df.iterrows()]

    subtotal_effort_days = round(sum(item.effort_days for item in line_items), 2)
    subtotal_cost = round(sum(item.cost for item in line_items), 2)

    risk_buffer_cost = round(subtotal_cost * (rate_card.risk_buffer_percent / 100), 2)
    cost_with_risk = subtotal_cost + risk_buffer_cost

    overhead_cost = round(cost_with_risk * (rate_card.overhead_percent / 100), 2)
    grand_total = round(cost_with_risk + overhead_cost, 2)

    unmapped_roles = sorted({item.role for item in line_items if item.role_was_defaulted})
    unmapped_complexity = sorted({item.complexity for item in line_items if item.complexity_was_defaulted})

    return EstimateSummary(
        line_items=line_items,
        subtotal_effort_days=subtotal_effort_days,
        subtotal_cost=subtotal_cost,
        risk_buffer_percent=rate_card.risk_buffer_percent,
        risk_buffer_cost=risk_buffer_cost,
        overhead_percent=rate_card.overhead_percent,
        overhead_cost=overhead_cost,
        grand_total=grand_total,
        currency=rate_card.currency,
        unmapped_roles=unmapped_roles,
        unmapped_complexity=unmapped_complexity,
    )
