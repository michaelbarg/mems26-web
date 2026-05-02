"""
MDS-V1.0.3: Tests for visualizer module.
Uses mock grid data to validate all 5 HTML renderers.
"""

import os
import sys
import pytest
import polars as pl
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from tools.multidim_sim.visualizer import (
    render_top_configs_html,
    render_heatmap_html,
    render_parallel_coords_html,
    render_categorical_breakdown_html,
    render_pareto_scatter_html,
    render_all_reports,
)


def generate_mock_grid_df(n_rows: int = 8000, seed: int = 42) -> pl.DataFrame:
    """
    Generate realistic mock grid results matching expected schema
    from grid_runner.py output.
    """
    rng = np.random.default_rng(seed)

    rows = []
    for i in range(n_rows):
        threshold = rng.uniform(25, 75)
        vegas_w = rng.uniform(0, 45)
        tpo_w = rng.uniform(5, 40)
        fvg_w = rng.uniform(5, 40)
        fp_logic = rng.choice(["weighted", "veto", "off"])
        day_filter = rng.choice(["all_days", "skip_DEVELOPING",
                                  "skip_DEVELOPING_NEUTRAL", "TREND_only"])
        dir_filter = rng.choice(["both", "SHORT_only"])
        skip_over = rng.choice([True, False])

        # Realistic correlated metrics
        base_wr = 0.40
        if threshold < 45: base_wr += 0.05
        if skip_over: base_wr += 0.03
        if fp_logic == "veto": base_wr += 0.04
        if day_filter != "all_days": base_wr += 0.02
        wr = base_wr + rng.normal(0, 0.05)
        wr = max(0.20, min(0.70, wr))

        n_trades = int(rng.uniform(500, 4000))
        if skip_over: n_trades = int(n_trades * 0.5)
        if day_filter != "all_days": n_trades = int(n_trades * 0.6)

        n_wins = int(n_trades * wr)
        n_losses = n_trades - n_wins - int(n_trades * 0.1)  # 10% timeout

        # PnL: $25 per win, -$25 per loss, -$2.75 cost per trade
        net_pnl = (n_wins * 25 - (n_losses * 25)) - (n_trades * 2.75)
        gross_wins = n_wins * 25
        gross_losses = n_losses * 25
        pf = (gross_wins / gross_losses) if gross_losses > 0 else 0
        max_dd = abs(net_pnl) * rng.uniform(0.3, 0.8) if net_pnl < 0 else rng.uniform(100, 500)

        # Composite (mock)
        if wr < 0.50 or pf < 1.20 or n_trades < 50:
            composite = float("-inf")
        else:
            composite = net_pnl - 0.5 * max_dd + 100 * max(0, pf - 1.5)

        rows.append({
            "rank": 0,
            "config_hash": f"cfg_{i:05d}",
            "cfg_threshold": round(threshold, 2),
            "cfg_vegas_weight": round(vegas_w, 2),
            "cfg_tpo_weight": round(tpo_w, 2),
            "cfg_fvg_weight": round(fvg_w, 2),
            "cfg_footprint_logic": str(fp_logic),
            "cfg_day_filter": str(day_filter),
            "cfg_direction_filter": str(dir_filter),
            "cfg_skip_overextended": bool(skip_over),
            "n_trades": n_trades,
            "n_wins": n_wins,
            "n_losses": n_losses,
            "win_rate": round(wr, 4),
            "net_pnl_usd": round(net_pnl, 2),
            "profit_factor": round(pf, 3),
            "max_drawdown_usd": round(max_dd, 2),
            "composite_score": composite if composite != float("-inf") else float("-inf"),
        })

    return pl.DataFrame(rows)


def test_mock_data_generation():
    df = generate_mock_grid_df(n_rows=100)
    assert len(df) == 100
    assert "composite_score" in df.columns
    assert "cfg_threshold" in df.columns


def test_top_configs_renders(tmp_path):
    df = generate_mock_grid_df(n_rows=200)
    out = render_top_configs_html(df, tmp_path / "top.html", top_n=20)
    assert out.exists()
    assert out.stat().st_size > 1000


def test_heatmap_renders(tmp_path):
    df = generate_mock_grid_df(n_rows=500)
    out = render_heatmap_html(
        df, tmp_path / "heat.html",
        "cfg_threshold", "cfg_vegas_weight", "net_pnl_usd")
    assert out.exists()
    assert out.stat().st_size > 1000


def test_parallel_coords_renders(tmp_path):
    df = generate_mock_grid_df(n_rows=300)
    out = render_parallel_coords_html(df, tmp_path / "parcoords.html", top_n=50)
    assert out.exists()


def test_categorical_breakdown_renders(tmp_path):
    df = generate_mock_grid_df(n_rows=500)
    out = render_categorical_breakdown_html(df, tmp_path / "cat.html")
    assert out.exists()


def test_pareto_scatter_renders(tmp_path):
    df = generate_mock_grid_df(n_rows=500)
    out = render_pareto_scatter_html(df, tmp_path / "pareto.html")
    assert out.exists()


def test_render_all_reports(tmp_path):
    df = generate_mock_grid_df(n_rows=1000)
    reports = render_all_reports(df, tmp_path)
    assert len(reports) == 6
    for name, path in reports.items():
        assert path.exists(), f"{name} not generated"
