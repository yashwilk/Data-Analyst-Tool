"""Render charts for Research mode, deterministically (no LLM in the loop).

Deliberate trade-off: instead of asking the LLM to write chart-drawing
code (a second, riskier "generate + execute arbitrary code" surface on
top of the SQL one), chart type is picked by a small heuristic over the
already-validated query result -- one categorical/date column + one
numeric column is all that's needed for a bar or line chart. This keeps
the only executed LLM output in the whole app to sandboxed SQL text.
"""

from __future__ import annotations

import base64
import io
import logging
import warnings

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from data_analyst_agent.state import DataAnalystState

logger = logging.getLogger(__name__)

MAX_CHARTS = 3
MAX_BARS = 10


def _pick_axes(df: pd.DataFrame) -> tuple[str, str, bool] | None:
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if not numeric_cols:
        return None
    value_col = numeric_cols[0]

    other_cols = [c for c in df.columns if c != value_col]
    if not other_cols:
        return None
    label_col = other_cols[0]

    is_datelike = False
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            parsed = pd.to_datetime(df[label_col], errors="coerce")
        is_datelike = parsed.notna().mean() > 0.8
    except Exception:  # noqa: BLE001
        is_datelike = False

    return label_col, value_col, is_datelike


def _render_chart(df: pd.DataFrame, label_col: str, value_col: str, is_datelike: bool, title: str) -> str:
    fig, ax = plt.subplots(figsize=(7, 4))
    try:
        if is_datelike:
            plot_df = df.copy()
            plot_df[label_col] = pd.to_datetime(plot_df[label_col], errors="coerce")
            plot_df = plot_df.dropna(subset=[label_col]).sort_values(label_col)
            ax.plot(plot_df[label_col], plot_df[value_col], marker="o")
            ax.set_xlabel(label_col)
            fig.autofmt_xdate()
        else:
            plot_df = df.sort_values(value_col, ascending=False).head(MAX_BARS)
            ax.bar(plot_df[label_col].astype(str), plot_df[value_col])
            ax.set_xlabel(label_col)
            plt.setp(ax.get_xticklabels(), rotation=45, ha="right")

        ax.set_ylabel(value_col)
        ax.set_title(title)
        fig.tight_layout()

        buffer = io.BytesIO()
        fig.savefig(buffer, format="png", dpi=120)
        return base64.b64encode(buffer.getvalue()).decode("ascii")
    finally:
        plt.close(fig)


async def build_charts(state: DataAnalystState) -> dict:
    if state.get("mode") != "research":
        return {}

    charts = []
    for result in state.get("query_results", []):
        if len(charts) >= MAX_CHARTS:
            break
        if result.get("error") or not result.get("rows"):
            continue

        try:
            df = pd.DataFrame(result["rows"])
            axes = _pick_axes(df)
            if axes is None:
                continue
            label_col, value_col, is_datelike = axes
            title = result.get("sub_question") or result["label"]
            image_base64 = _render_chart(df, label_col, value_col, is_datelike, title)
            charts.append(
                {
                    "title": title,
                    "caption": f"From query '{result['label']}' ({result.get('row_count', 0)} rows)",
                    "chart_type": "line" if is_datelike else "bar",
                    "image_base64": image_base64,
                }
            )
        except Exception as exc:  # noqa: BLE001 - nodes never raise
            logger.warning("build_charts skipped result %s: %s", result.get("label"), exc)
            continue

    return {"charts": charts}
