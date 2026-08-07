"""Unit tests for proposal_generator.py"""

import os

from src.estimator import EstimateSummary, RequirementEstimate
from src.config_manager import ProjectConfig
from src.proposal_generator import generate_proposal


def _make_summary():
    item = RequirementEstimate(
        requirement_id="REQ-001",
        description="Build API",
        role="Python Developer",
        complexity="Extreme",
        effective_complexity="Medium",
        effort_days=3.0,
        daily_rate=8000,
        cost=24000.0,
        complexity_was_defaulted=True,
    )
    return EstimateSummary(
        line_items=[item],
        subtotal_effort_days=3.0,
        subtotal_cost=24000.0,
        risk_buffer_percent=10,
        risk_buffer_cost=2400.0,
        overhead_percent=5,
        overhead_cost=1320.0,
        grand_total=27720.0,
        currency="INR",
        unmapped_complexity=["Extreme"],
    )


def _project_config():
    return ProjectConfig(
        company_name="Test Co",
        prepared_by="Tester",
        proposal_validity_days=30,
        proposal_terms=["Term 1"],
    )


def test_generate_proposal_creates_docx(tmp_path):
    output = tmp_path / "subdir" / "proposal.docx"
    path = generate_proposal(
        _make_summary(), _project_config(), "Acme Corp", str(output), include_charts=False
    )
    assert os.path.exists(path)
    assert os.path.getsize(path) > 0


def test_generate_proposal_flat_output_path(tmp_path, monkeypatch):
    """Output path with no directory component should not crash."""
    monkeypatch.chdir(tmp_path)
    path = generate_proposal(
        _make_summary(), _project_config(), "Acme Corp", "proposal.docx", include_charts=False
    )
    assert os.path.exists(path)
