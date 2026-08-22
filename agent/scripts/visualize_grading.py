"""DeepEval 채점 결과를 Plotly standalone HTML로 시각화한다.

실행:
    uv run --package agent --group dev python agent/scripts/visualize_grading.py

입력은 `dataset/deepeval-results.json`, 출력은
`dataset/deepeval-results.html`이며 둘 다 gitignore 대상이다.
인터넷 없이 열 수 있도록 첫 번째 그래프에 Plotly JavaScript를 함께 삽입한다.
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Annotated, Any

import plotly.graph_objects as go
import typer
from plotly.colors import qualitative
from plotly.io import to_html

DEFAULT_INPUT = Path("dataset/deepeval-results.json")
DEFAULT_OUTPUT = Path("dataset/deepeval-results.html")


def _label(experiment: dict[str, Any]) -> str:
    return (
        f"{experiment.get('candidate', 'unknown')}"
        f" | t={experiment.get('temperature')}"
        f" | n={experiment.get('replicas')}"
    )


def _candidate(experiment: dict[str, Any]) -> str:
    return str(experiment.get("candidate", "unknown"))


def _number(experiment: dict[str, Any], key: str) -> float | None:
    summary = experiment.get("summary", {})
    value = summary.get(key) if isinstance(summary, dict) else None
    return float(value) if isinstance(value, (int, float)) else None


def _mae_sort_key(experiment: dict[str, Any]) -> tuple[bool, float]:
    value = _number(experiment, "criterion_consensus_mae")
    return value is None, value if value is not None else float("inf")


def _colors(experiments: list[dict[str, Any]]) -> dict[str, str]:
    names = list(dict.fromkeys(_candidate(experiment) for experiment in experiments))
    palette = qualitative.Dark24
    return {name: palette[index % len(palette)] for index, name in enumerate(names)}


def _bar_chart(
    title: str,
    experiments: list[dict[str, Any]],
    metric_key: str,
    colors: dict[str, str],
    *,
    percent: bool = False,
) -> go.Figure:
    entries = [
        (experiment, _number(experiment, metric_key)) for experiment in experiments
    ]
    entries = [
        (experiment, value) for experiment, value in entries if value is not None
    ]
    figure = go.Figure()
    if entries:
        labels = [_label(experiment) for experiment, _ in entries]
        values = [value for _, value in entries]
        figure.add_trace(
            go.Bar(
                x=labels,
                y=values,
                marker_color=[
                    colors[_candidate(experiment)] for experiment, _ in entries
                ],
                customdata=[
                    [
                        _candidate(experiment),
                        experiment.get("temperature"),
                        experiment.get("replicas"),
                    ]
                    for experiment, _ in entries
                ],
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "temperature=%{customdata[1]}<br>"
                    "replicas=%{customdata[2]}<br>"
                    + ("rate=%{y:.1%}" if percent else "value=%{y:.3f}")
                    + "<extra></extra>"
                ),
            )
        )
    figure.update_layout(
        title=title,
        template="plotly_white",
        height=560,
        width=max(1100, len(entries) * 145),
        margin={"l": 70, "r": 30, "t": 70, "b": 190},
        showlegend=False,
        hoverlabel={"namelength": -1},
    )
    figure.update_xaxes(tickangle=-42, automargin=True)
    if percent:
        figure.update_yaxes(range=[0, 1], tickformat=".0%", title="rate")
    else:
        figure.update_yaxes(title="MAE")
    return figure


def _scatter_chart(
    experiments: list[dict[str, Any]], colors: dict[str, str]
) -> go.Figure:
    figure = go.Figure()
    symbols = {1: "circle", 3: "diamond"}
    for experiment in experiments:
        latency = _number(experiment, "mean_latency_ms")
        mae = _number(experiment, "criterion_consensus_mae")
        if latency is None or mae is None:
            continue
        label = _label(experiment)
        replicas = experiment.get("replicas")
        symbol = (
            symbols.get(replicas, "circle") if isinstance(replicas, int) else "circle"
        )
        figure.add_trace(
            go.Scatter(
                x=[latency],
                y=[mae],
                mode="markers",
                name=label,
                marker={
                    "size": 13,
                    "color": colors[_candidate(experiment)],
                    "symbol": symbol,
                    "line": {"color": "white", "width": 1.5},
                },
                hovertemplate=(
                    f"<b>{html.escape(label)}</b><br>"
                    "mean latency=%{x:.1f} ms<br>"
                    "criterion MAE=%{y:.3f}<extra></extra>"
                ),
            )
        )
    figure.update_layout(
        title="정확도와 지연시간",
        template="plotly_white",
        height=620,
        width=1050,
        margin={"l": 80, "r": 30, "t": 70, "b": 80},
        legend={"orientation": "v", "y": 1, "x": 1.02},
        hoverlabel={"namelength": -1},
    )
    figure.update_xaxes(title="mean latency (ms)")
    figure.update_yaxes(title="criterion consensus MAE")
    return figure


def _table_chart(experiments: list[dict[str, Any]]) -> go.Figure:
    ordered = sorted(experiments, key=_mae_sort_key)
    columns: list[list[str]] = [[] for _ in range(8)]
    for experiment in ordered:
        summary = experiment.get("summary", {})
        values: list[object] = [
            _label(experiment),
            summary.get("validity_rate"),
            summary.get("criterion_consensus_mae"),
            summary.get("total_consensus_mae"),
            summary.get("criterion_within_one_rate"),
            summary.get("mean_latency_ms"),
            summary.get("error_count", 0),
            "<br>".join(summary.get("error_examples", [])),
        ]
        formatted = ["-" if value is None else str(value) for value in values]
        for column, value in zip(columns, formatted):
            column.append(value)
    figure = go.Figure(
        data=[
            go.Table(
                header={
                    "values": [
                        "후보 조합",
                        "유효성",
                        "항목 MAE",
                        "총점 MAE",
                        "±1점 일치율",
                        "평균 지연시간(ms)",
                        "실패 수",
                        "실패 원인",
                    ],
                    "fill_color": "#edf1ff",
                    "font": {"color": "#243047", "size": 12},
                    "align": "left",
                    "height": 36,
                },
                cells={
                    "values": columns,
                    "fill_color": [
                        [
                            "white" if index % 2 == 0 else "#f8faff"
                            for index in range(len(ordered))
                        ]
                        for _ in columns
                    ],
                    "align": "left",
                    "font": {"color": "#243047", "size": 11},
                    "height": 32,
                },
            )
        ]
    )
    figure.update_layout(
        title="실험 결과 순위",
        template="plotly_white",
        height=max(300, 120 + len(ordered) * 34),
        width=1450,
        margin={"l": 10, "r": 10, "t": 70, "b": 20},
    )
    return figure


def _plot_div(figure: go.Figure, *, include_plotlyjs: bool) -> str:
    return to_html(
        figure,
        full_html=False,
        include_plotlyjs=include_plotlyjs,
        config={
            "responsive": True,
            "displaylogo": False,
            "toImageButtonOptions": {"format": "svg"},
        },
    )


def _render(experiments: list[dict[str, Any]]) -> str:
    colors = _colors(experiments)
    figures = [
        _bar_chart(
            "항목별 consensus MAE", experiments, "criterion_consensus_mae", colors
        ),
        _bar_chart("총점 consensus MAE", experiments, "total_consensus_mae", colors),
        _bar_chart(
            "구조화 출력 성공률",
            experiments,
            "validity_rate",
            colors,
            percent=True,
        ),
        _scatter_chart(experiments, colors),
        _table_chart(experiments),
    ]
    plot_divs = [
        _plot_div(figure, include_plotlyjs=index == 0)
        for index, figure in enumerate(figures)
    ]
    sections = "\n".join(
        f'<section><div class="plot-scroll">{plot}</div></section>'
        for plot in plot_divs
    )
    generated_at = (
        __import__("datetime").datetime.now().astimezone().isoformat(timespec="seconds")
    )
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Paragraphy grading benchmark</title>
<style>
:root {{ color-scheme: light; --ink: #243047; --muted: #6b7280; --line: #dbe2ec; --background: #f6f8fc; --surface: #fff; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; padding: 32px; color: var(--ink); background: var(--background); font: 14px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }}
main {{ max-width: 1500px; margin: 0 auto; }}
h1 {{ margin: 0 0 4px; font-size: 28px; letter-spacing: -.03em; }}
.subtitle {{ margin-top: 0; color: var(--muted); }}
section {{ margin-top: 24px; padding: 18px; background: var(--surface); border: 1px solid var(--line); border-radius: 16px; box-shadow: 0 5px 18px rgba(36,48,71,.04); }}
.plot-scroll {{ overflow-x: auto; }}
.plotly-graph-div {{ margin: auto; }}
@media (max-width: 640px) {{ body {{ padding: 14px; }} section {{ padding: 10px; border-radius: 12px; }} h1 {{ font-size: 23px; }} }}
</style>
</head>
<body><main>
<h1>Paragraphy grading benchmark</h1>
<p class="subtitle">생성 시각: {html.escape(generated_at)} · DeepEval 결과 요약 · 막대그래프 범례 색상은 모델, 산점도 마커 모양은 replicas를 의미합니다.</p>
{sections}
</main></body>
</html>"""


app = typer.Typer(add_completion=False, no_args_is_help=True)


@app.command()
def main(
    input_path: Annotated[Path, typer.Option("--input")] = DEFAULT_INPUT,
    output: Annotated[Path, typer.Option("--output")] = DEFAULT_OUTPUT,
) -> None:
    if not input_path.exists():
        raise typer.BadParameter(f"결과 파일을 찾지 못했습니다: {input_path}")
    with input_path.open(encoding="utf-8") as file:
        experiments = json.load(file)
    if not isinstance(experiments, list) or not experiments:
        raise typer.BadParameter("결과 파일에 실험 결과가 없습니다.")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(_render(experiments), encoding="utf-8")
    print(f"saved visualization to {output}")


if __name__ == "__main__":
    app()
