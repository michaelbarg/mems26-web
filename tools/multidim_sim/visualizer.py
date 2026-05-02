"""
MDS-V1.0.3: Visualization module for grid search results.
Renders 5 interactive HTML reports using Plotly.
"""

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import polars as pl
import pandas as pd
from pathlib import Path
from datetime import datetime


def _to_pandas(df: pl.DataFrame) -> pd.DataFrame:
    """Polars -> Pandas for Plotly."""
    return df.to_pandas()


def _filter_valid(df: pl.DataFrame) -> pl.DataFrame:
    """Remove configs with -inf composite score."""
    return df.filter(pl.col("composite_score") > float("-inf"))


def render_top_configs_html(grid_df: pl.DataFrame,
                            output_path: Path,
                            top_n: int = 50) -> Path:
    """
    Interactive sortable table of top N configs.
    Includes color coding for net_pnl (green=positive, red=negative).
    """
    valid = _filter_valid(grid_df).sort("composite_score", descending=True).head(top_n)
    pdf = _to_pandas(valid)

    fig = go.Figure(data=[go.Table(
        header=dict(
            values=list(pdf.columns),
            fill_color="navy",
            font=dict(color="white", size=11),
            align="left"
        ),
        cells=dict(
            values=[pdf[col] for col in pdf.columns],
            fill_color=[
                ["lightgreen" if v > 0 else "lightcoral" for v in pdf["net_pnl_usd"]]
                if col == "net_pnl_usd" else "white"
                for col in pdf.columns
            ],
            align="left",
            font=dict(size=10)
        )
    )])

    fig.update_layout(
        title=f"Top {top_n} Configurations by Composite Score",
        height=800,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(output_path)
    return output_path


def render_heatmap_html(grid_df: pl.DataFrame,
                        output_path: Path,
                        dim_x: str = "cfg_threshold",
                        dim_y: str = "cfg_vegas_weight",
                        metric: str = "net_pnl_usd",
                        n_bins: int = 10) -> Path:
    """
    2D heatmap of metric across two parameter dimensions.
    """
    valid = _filter_valid(grid_df)
    pdf = _to_pandas(valid)

    pdf[f"{dim_x}_bin"] = pd.cut(pdf[dim_x], bins=n_bins)
    pdf[f"{dim_y}_bin"] = pd.cut(pdf[dim_y], bins=n_bins)

    pivot = pdf.pivot_table(
        values=metric,
        index=f"{dim_y}_bin",
        columns=f"{dim_x}_bin",
        aggfunc="mean"
    )
    pivot.index = [str(i) for i in pivot.index]
    pivot.columns = [str(c) for c in pivot.columns]

    fig = px.imshow(
        pivot,
        labels=dict(x=dim_x, y=dim_y, color=metric),
        title=f"Heatmap: {metric} by {dim_x} x {dim_y}",
        color_continuous_scale="RdYlGn",
        aspect="auto"
    )

    fig.update_layout(height=600)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(output_path)
    return output_path


def render_parallel_coords_html(grid_df: pl.DataFrame,
                                output_path: Path,
                                top_n: int = 200) -> Path:
    """
    Parallel coordinates plot -- shows all dims for top N configs.
    Color = composite_score.
    """
    valid = _filter_valid(grid_df).sort("composite_score", descending=True).head(top_n)
    pdf = _to_pandas(valid)

    dimensions = [
        dict(label="Threshold", values=pdf["cfg_threshold"]),
        dict(label="Vegas W", values=pdf["cfg_vegas_weight"]),
        dict(label="TPO W", values=pdf["cfg_tpo_weight"]),
        dict(label="FVG W", values=pdf["cfg_fvg_weight"]),
        dict(label="N Trades", values=pdf["n_trades"]),
        dict(label="Win Rate %", values=pdf["win_rate"] * 100),
        dict(label="Net PnL $", values=pdf["net_pnl_usd"]),
        dict(label="Profit Factor", values=pdf["profit_factor"]),
    ]

    fig = go.Figure(data=go.Parcoords(
        line=dict(
            color=pdf["composite_score"],
            colorscale="Viridis",
            showscale=True,
            colorbar=dict(title="Composite")
        ),
        dimensions=dimensions
    ))

    fig.update_layout(
        title=f"Parallel Coordinates: Top {top_n} Configs",
        height=600
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(output_path)
    return output_path


def render_categorical_breakdown_html(grid_df: pl.DataFrame,
                                      output_path: Path) -> Path:
    """
    4-subplot grid: avg net_pnl by each categorical dimension.
    """
    valid = _filter_valid(grid_df)
    pdf = _to_pandas(valid)

    cat_cols = ["cfg_footprint_logic", "cfg_day_filter",
                "cfg_direction_filter", "cfg_skip_overextended"]

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=cat_cols
    )

    for idx, col in enumerate(cat_cols):
        row = idx // 2 + 1
        c = idx % 2 + 1

        agg = pdf.groupby(col).agg({
            "net_pnl_usd": "mean",
            "win_rate": "mean",
            "config_hash": "count"
        }).reset_index()
        agg.columns = [col, "avg_net_pnl", "avg_wr", "n_configs"]

        fig.add_trace(
            go.Bar(
                x=agg[col].astype(str),
                y=agg["avg_net_pnl"],
                text=[f"${v:.0f}<br>WR {wr:.1%}<br>n={n}"
                      for v, wr, n in zip(agg["avg_net_pnl"], agg["avg_wr"], agg["n_configs"])],
                textposition="auto",
                marker_color=["green" if v > 0 else "red" for v in agg["avg_net_pnl"]],
                showlegend=False
            ),
            row=row, col=c
        )

    fig.update_layout(
        title="Categorical Dimension Impact on Avg Net PnL",
        height=800
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(output_path)
    return output_path


def render_pareto_scatter_html(grid_df: pl.DataFrame,
                               output_path: Path) -> Path:
    """
    Scatter: Net PnL vs Win Rate, colored by n_trades.
    Shows the Pareto frontier of profitable configs.
    """
    valid = _filter_valid(grid_df)
    pdf = _to_pandas(valid)

    fig = px.scatter(
        pdf,
        x="win_rate",
        y="net_pnl_usd",
        color="n_trades",
        size="profit_factor",
        hover_data=["cfg_threshold", "cfg_footprint_logic", "cfg_day_filter",
                     "cfg_skip_overextended"],
        title="Pareto Scatter: Net PnL vs Win Rate",
        labels={"win_rate": "Win Rate", "net_pnl_usd": "Net PnL (USD)"},
        color_continuous_scale="Viridis"
    )

    fig.add_trace(go.Scatter(
        x=[0.4286], y=[-46914],
        mode="markers+text",
        marker=dict(size=20, color="red", symbol="x"),
        text=["V1 Baseline"],
        textposition="top center",
        showlegend=True,
        name="V1 Baseline"
    ))

    fig.update_layout(height=600)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(output_path)
    return output_path


def render_all_reports(grid_df: pl.DataFrame,
                       output_dir: Path = None) -> dict:
    """
    Render all 5 HTML reports. Returns dict of report_name -> path.
    """
    if output_dir is None:
        output_dir = Path(__file__).parent / "results" / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    reports = {
        "top_configs": render_top_configs_html(
            grid_df, output_dir / f"top_configs_{ts}.html"),
        "heatmap_threshold_vegas": render_heatmap_html(
            grid_df, output_dir / f"heatmap_threshold_vegas_{ts}.html",
            "cfg_threshold", "cfg_vegas_weight", "net_pnl_usd"),
        "heatmap_tpo_fvg": render_heatmap_html(
            grid_df, output_dir / f"heatmap_tpo_fvg_{ts}.html",
            "cfg_tpo_weight", "cfg_fvg_weight", "net_pnl_usd"),
        "parallel_coords": render_parallel_coords_html(
            grid_df, output_dir / f"parallel_coords_{ts}.html"),
        "categorical_breakdown": render_categorical_breakdown_html(
            grid_df, output_dir / f"categorical_breakdown_{ts}.html"),
        "pareto_scatter": render_pareto_scatter_html(
            grid_df, output_dir / f"pareto_scatter_{ts}.html"),
    }

    return reports
