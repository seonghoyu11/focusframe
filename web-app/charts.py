"""Chart generation for the dashboard."""

import base64
import io

import matplotlib

matplotlib.use("Agg")  # must come before pyplot import; headless Docker

import matplotlib.pyplot as plt  # pylint: disable=wrong-import-position

_SLICE_ORDER = ("focused", "distracted")
_COLORS = {
    "focused": "#10b981",
    "distracted": "#f59e0b",
}
_LABELS = {
    "focused": "Focused",
    "distracted": "Distracted",
}
_TEXT_COLOR = "#f8fafc"


def generate_focus_chart(totals):
    """Render a donut chart of focused vs distracted time as a base64 PNG."""
    values = [int(totals.get(k, 0)) for k in _SLICE_ORDER]
    if sum(values) == 0:
        return None

    colors = [_COLORS[k] for k in _SLICE_ORDER]
    labels = [_LABELS[k] for k in _SLICE_ORDER]

    fig, ax = plt.subplots(figsize=(5, 4), dpi=100)
    fig.patch.set_alpha(0)
    ax.set_facecolor("none")

    wedges, _texts, autotexts = ax.pie(
        values,
        colors=colors,
        startangle=90,
        counterclock=False,
        wedgeprops={"width": 0.35, "edgecolor": "none"},
        autopct=lambda pct: f"{pct:.0f}%" if pct >= 5 else "",
        pctdistance=0.82,
    )

    for txt in autotexts:
        txt.set_color("white")
        txt.set_fontsize(11)
        txt.set_fontweight("bold")

    legend = ax.legend(
        wedges,
        labels,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.05),
        ncol=2,
        frameon=False,
        fontsize=10,
    )

    for text in legend.get_texts():
        text.set_color(_TEXT_COLOR)

    ax.set_aspect("equal")
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", transparent=True, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.getvalue()).decode("utf-8")
