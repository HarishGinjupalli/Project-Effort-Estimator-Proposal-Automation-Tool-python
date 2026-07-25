"""
chart_generator.py
Renders visual summaries of an estimate as PNG images, to be embedded in the
Word proposal: cost by role, effort by complexity, and top cost-driving
requirements. Uses matplotlib's non-interactive 'Agg' backend so it runs
headless (no display needed) — required for CLI/server use.

Charts are saved to a temp directory and returned as file paths; the
proposal generator embeds them, then the caller is responsible for cleanup
(main.py handles this).
"""

import matplotlib
matplotlib.use("Agg")  # headless backend — must be set before importing pyplot

import matplotlib.pyplot as plt
from collections import defaultdict
from typing import List, Dict
import os

from src.estimator import EstimateSummary

# Consulting-friendly palette, consistent with the proposal's navy accent
NAVY = "#1F4E79"
PALETTE = ["#1F4E79", "#2E75B6", "#9DC3E6", "#BDD7EE", "#548235", "#A9D18E", "#C55A11", "#F4B183"]

plt.rcParams.update({
    "font.size": 10,
    "axes.edgecolor": "#CCCCCC",
    "axes.labelcolor": "#333333",
    "text.color": "#333333",
    "xtick.color": "#333333",
    "ytick.color": "#333333",
})


def _aggregate_by(summary: EstimateSummary, key: str) -> Dict[str, float]:
    """Sum cost per distinct value of `key` (role or complexity) across line items."""
    totals = defaultdict(float)
    for item in summary.line_items:
        value = getattr(item, key)
        totals[value] += item.cost
    return dict(sorted(totals.items(), key=lambda kv: kv[1], reverse=True))


def generate_cost_by_role_chart(summary: EstimateSummary, output_path: str) -> str:
    """Horizontal bar chart: total cost per role, largest first."""
    totals = _aggregate_by(summary, "role")
    roles = list(totals.keys())
    costs = list(totals.values())

    fig, ax = plt.subplots(figsize=(7, max(2.5, 0.4 * len(roles))))
    bars = ax.barh(roles, costs, color=PALETTE[0])
    ax.invert_yaxis()
    ax.set_xlabel(f"Cost ({summary.currency})")
    ax.set_title("Cost by Role", fontweight="bold", color=NAVY, pad=12)
    ax.spines[["top", "right"]].set_visible(False)

    max_cost = max(costs) if costs else 1
    for bar, cost in zip(bars, costs):
        ax.text(
            bar.get_width() + max_cost * 0.01,
            bar.get_y() + bar.get_height() / 2,
            f"{cost:,.0f}",
            va="center", fontsize=8,
        )

    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return output_path


def generate_effort_by_complexity_chart(summary: EstimateSummary, output_path: str) -> str:
    """Pie chart: share of total effort (person-days) by complexity level."""
    totals = defaultdict(float)
    for item in summary.line_items:
        totals[item.complexity] += item.effort_days
    # Keep a stable, sensible order when the standard levels are present
    order = ["Low", "Medium", "High"]
    labels = sorted(totals.keys(), key=lambda x: order.index(x) if x in order else 99)
    values = [totals[l] for l in labels]

    fig, ax = plt.subplots(figsize=(5.5, 5))
    wedges, _, autotexts = ax.pie(
        values,
        labels=labels,
        autopct=lambda pct: f"{pct:.0f}%",
        colors=PALETTE[:len(labels)],
        startangle=90,
        textprops={"fontsize": 10},
    )
    for text in autotexts:
        text.set_color("white")
        text.set_fontweight("bold")
    ax.set_title("Effort Distribution by Complexity", fontweight="bold", color=NAVY, pad=12)

    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return output_path


def generate_top_cost_drivers_chart(summary: EstimateSummary, output_path: str, top_n: int = 10) -> str:
    """Horizontal bar chart of the top N individual requirements by cost."""
    sorted_items = sorted(summary.line_items, key=lambda i: i.cost, reverse=True)[:top_n]
    # Truncate long descriptions for axis labels
    labels = [
        f"{item.requirement_id}: {item.description[:40]}{'...' if len(item.description) > 40 else ''}"
        for item in sorted_items
    ]
    costs = [item.cost for item in sorted_items]

    fig, ax = plt.subplots(figsize=(8, max(3, 0.4 * len(labels))))
    bars = ax.barh(labels, costs, color=PALETTE[1])
    ax.invert_yaxis()
    ax.set_xlabel(f"Cost ({summary.currency})")
    ax.set_title(f"Top {len(labels)} Requirements by Cost", fontweight="bold", color=NAVY, pad=12)
    ax.spines[["top", "right"]].set_visible(False)

    max_cost = max(costs) if costs else 1
    for bar, cost in zip(bars, costs):
        ax.text(
            bar.get_width() + max_cost * 0.01,
            bar.get_y() + bar.get_height() / 2,
            f"{cost:,.0f}",
            va="center", fontsize=8,
        )

    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return output_path


def generate_all_charts(summary: EstimateSummary, output_dir: str) -> Dict[str, str]:
    """
    Generate the standard chart set for a proposal and return a dict of
    chart_name -> file_path. Skips the top-cost-drivers chart if there
    are fewer than 3 requirements (not meaningful at that scale).
    """
    os.makedirs(output_dir, exist_ok=True)
    charts = {}

    charts["cost_by_role"] = generate_cost_by_role_chart(
        summary, os.path.join(output_dir, "cost_by_role.png")
    )
    charts["effort_by_complexity"] = generate_effort_by_complexity_chart(
        summary, os.path.join(output_dir, "effort_by_complexity.png")
    )
    if len(summary.line_items) >= 3:
        charts["top_cost_drivers"] = generate_top_cost_drivers_chart(
            summary, os.path.join(output_dir, "top_cost_drivers.png"),
            top_n=min(10, len(summary.line_items)),
        )

    return charts
