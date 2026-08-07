"""
Unit tests for chart_generator.py
Covers: each chart function produces a valid, non-empty PNG file, and
generate_all_charts skips the top-cost-drivers chart for tiny datasets.
"""

import os
import pytest

from src.estimator import EstimateSummary, RequirementEstimate
from src.chart_generator import (
    generate_cost_by_role_chart,
    generate_effort_by_complexity_chart,
    generate_top_cost_drivers_chart,
    generate_all_charts,
)


def _make_summary(n_items=5):
    roles = ["Python Developer", "Business Analyst", "QA Engineer"]
    complexities = ["Low", "Medium", "High"]
    line_items = [
        RequirementEstimate(
            requirement_id=f"REQ-{i:03d}",
            description=f"Requirement number {i} description text",
            role=roles[i % len(roles)],
            complexity=complexities[i % len(complexities)],
            effective_complexity=complexities[i % len(complexities)],
            effort_days=2.0 + i,
            daily_rate=8000,
            cost=(2.0 + i) * 8000,
        )
        for i in range(n_items)
    ]
    return EstimateSummary(
        line_items=line_items,
        subtotal_effort_days=sum(i.effort_days for i in line_items),
        subtotal_cost=sum(i.cost for i in line_items),
        risk_buffer_percent=10,
        risk_buffer_cost=1000,
        overhead_percent=5,
        overhead_cost=500,
        grand_total=sum(i.cost for i in line_items) + 1500,
        currency="INR",
    )


def test_generate_cost_by_role_chart_creates_valid_png(tmp_path):
    summary = _make_summary()
    path = generate_cost_by_role_chart(summary, str(tmp_path / "cost_by_role.png"))
    assert os.path.exists(path)
    assert os.path.getsize(path) > 0
    with open(path, "rb") as f:
        assert f.read(8) == b"\x89PNG\r\n\x1a\n"  # PNG magic bytes


def test_generate_effort_by_complexity_chart_creates_valid_png(tmp_path):
    summary = _make_summary()
    path = generate_effort_by_complexity_chart(summary, str(tmp_path / "effort.png"))
    assert os.path.exists(path)
    assert os.path.getsize(path) > 0


def test_generate_top_cost_drivers_chart_creates_valid_png(tmp_path):
    summary = _make_summary(n_items=8)
    path = generate_top_cost_drivers_chart(summary, str(tmp_path / "top_costs.png"), top_n=5)
    assert os.path.exists(path)
    assert os.path.getsize(path) > 0


def test_generate_all_charts_returns_all_three_for_normal_dataset(tmp_path):
    summary = _make_summary(n_items=10)
    charts = generate_all_charts(summary, str(tmp_path))
    assert set(charts.keys()) == {"cost_by_role", "effort_by_complexity", "top_cost_drivers"}
    for path in charts.values():
        assert os.path.exists(path)


def test_generate_all_charts_skips_top_drivers_for_tiny_dataset(tmp_path):
    summary = _make_summary(n_items=2)
    charts = generate_all_charts(summary, str(tmp_path))
    assert "top_cost_drivers" not in charts
    assert "cost_by_role" in charts
    assert "effort_by_complexity" in charts
