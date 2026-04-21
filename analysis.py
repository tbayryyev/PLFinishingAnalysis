"""
Premier League 2025/26 Forwards — Finishing Quality Analysis.

Compares actual goals against Expected Goals (xG) for Premier League forwards
to separate clinical finishers from statistical outliers. Generates five
publication-quality charts from a single CSV input.

Usage:
    python analysis.py

Output:
    charts/01_top_scorers.png
    charts/02_goals_vs_xg.png
    charts/03_conversion_rate.png
    charts/04_goal_contributions.png
    charts/05_efficiency_quadrant.png
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch


# ---------- Paths ----------
CSV_PATH = Path("premier_league_2025_26_forwards.csv")
OUT_DIR = Path("charts")

# ---------- Theme ----------
ACCENT = "#00ff85"      # Premier League green — overperformers
WARN = "#ff2882"        # hot pink — underperformers
HIGHLIGHT = "#ffd700"   # gold — leader
SECONDARY = "#00b8ff"   # blue — assists / secondary bars
NEUTRAL = "#cccccc"
DARK_BG = "#0a0a0a"
LIGHT_TXT = "#f5f5f5"

PLOT_STYLE = {
    "figure.facecolor": DARK_BG,
    "axes.facecolor":   DARK_BG,
    "axes.edgecolor":   LIGHT_TXT,
    "axes.labelcolor":  LIGHT_TXT,
    "xtick.color":      LIGHT_TXT,
    "ytick.color":      LIGHT_TXT,
    "text.color":       LIGHT_TXT,
    "font.family":      "DejaVu Sans",
    "font.size":        11,
    "axes.titlesize":   16,
    "axes.titleweight": "bold",
}

# Expected conversion rate for a Premier League penalty, used to strip
# penalty xG from non-penalty xG differentials.
PENALTY_XG = 0.79


# ---------- Data ----------
def load_and_enrich(path: Path) -> pd.DataFrame:
    """Load the forwards CSV and compute derived performance metrics."""
    df = pd.read_csv(path)

    df["goal_contributions"] = df["goals"] + df["assists"]
    df["xG_diff"]            = df["goals"] - df["xG"]
    df["conversion_rate"]    = df["goals"] / df["shots"] * 100
    df["xG_per_shot"]        = df["xG"] / df["shots"]
    df["mins_per_goal"]      = df["minutes"] / df["goals"].replace(0, np.nan)
    df["non_pen_goals"]      = df["goals"] - df["penalties_scored"]
    df["non_pen_xG_diff"]    = df["non_pen_goals"] - (df["xG"] - df["penalties_scored"] * PENALTY_XG)

    return df


# ---------- Charts ----------
def plot_top_scorers(df: pd.DataFrame, out: Path) -> None:
    top10 = df.nlargest(10, "goals").iloc[::-1]

    fig, ax = plt.subplots(figsize=(12, 7))
    bars = ax.barh(top10["player"], top10["goals"],
                   color=ACCENT, edgecolor="white", linewidth=0.5)
    bars[-1].set_color(HIGHLIGHT)

    for bar, val in zip(bars, top10["goals"]):
        ax.text(val + 0.3, bar.get_y() + bar.get_height() / 2,
                str(int(val)), va="center", fontsize=11, fontweight="bold")

    ax.set_title("PREMIER LEAGUE 2025/26 — TOP 10 GOAL SCORERS", pad=20)
    ax.set_xlabel("Goals")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_xlim(0, top10["goals"].max() * 1.15)

    plt.tight_layout()
    plt.savefig(out, dpi=150, facecolor=DARK_BG)
    plt.close(fig)


def plot_goals_vs_xg(df: pd.DataFrame, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(13, 8))

    lim = max(df["goals"].max(), df["xG"].max()) + 2
    ax.plot([0, lim], [0, lim], color=NEUTRAL, linestyle="--", linewidth=1.5,
            label="Goals = xG (expected performance)", alpha=0.6)

    colors = [
        ACCENT if d > 2 else WARN if d < -2 else "#888888"
        for d in df["xG_diff"]
    ]
    sizes = np.clip(df["shots"] * 3, 40, 400)

    ax.scatter(df["xG"], df["goals"], c=colors, s=sizes, alpha=0.75,
               edgecolors="white", linewidth=0.8)

    notable = pd.concat([
        df.nlargest(5, "xG_diff"),
        df.nsmallest(4, "xG_diff"),
        df.nlargest(3, "goals"),
    ]).drop_duplicates()

    for _, row in notable.iterrows():
        ax.annotate(row["player"], (row["xG"], row["goals"]),
                    xytext=(7, 5), textcoords="offset points",
                    fontsize=9, fontweight="bold", color="white")

    ax.set_xlabel("Expected Goals (xG)", fontsize=12)
    ax.set_ylabel("Actual Goals", fontsize=12)
    ax.set_title("CLINICAL FINISHERS — GOALS vs EXPECTED GOALS", pad=20)

    legend_elements = [
        Patch(facecolor=ACCENT,    label="Overperforming xG (+2 or more)"),
        Patch(facecolor=WARN,      label="Underperforming xG (-2 or less)"),
        Patch(facecolor="#888888", label="Near expectation"),
    ]
    ax.legend(handles=legend_elements, loc="upper left", framealpha=0.2)

    ax.grid(True, alpha=0.15)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    plt.savefig(out, dpi=150, facecolor=DARK_BG)
    plt.close(fig)


def plot_conversion_rate(df: pd.DataFrame, out: Path, min_shots: int = 40) -> None:
    qualified = df[df["shots"] >= min_shots]
    top_conv = qualified.nlargest(12, "conversion_rate").iloc[::-1]

    fig, ax = plt.subplots(figsize=(12, 8))
    bars = ax.barh(top_conv["player"], top_conv["conversion_rate"],
                   color=SECONDARY, edgecolor="white", linewidth=0.5)
    bars[-1].set_color(HIGHLIGHT)

    for bar, val, shots in zip(bars, top_conv["conversion_rate"], top_conv["shots"]):
        ax.text(val + 0.3, bar.get_y() + bar.get_height() / 2,
                f"{val:.1f}%  ({int(shots)} shots)",
                va="center", fontsize=10)

    ax.set_title(f"MOST CLINICAL STRIKERS — SHOT CONVERSION RATE\n(minimum {min_shots} shots)", pad=20)
    ax.set_xlabel("% of shots converted into goals")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_xlim(0, top_conv["conversion_rate"].max() * 1.25)

    plt.tight_layout()
    plt.savefig(out, dpi=150, facecolor=DARK_BG)
    plt.close(fig)


def plot_goal_contributions(df: pd.DataFrame, out: Path) -> None:
    top_ga = df.nlargest(10, "goal_contributions").iloc[::-1]

    fig, ax = plt.subplots(figsize=(12, 7))
    width = 0.4
    y = np.arange(len(top_ga))

    ax.barh(y + width / 2, top_ga["goals"],   width,
            color=ACCENT,    label="Goals",   edgecolor="white", linewidth=0.4)
    ax.barh(y - width / 2, top_ga["assists"], width,
            color=SECONDARY, label="Assists", edgecolor="white", linewidth=0.4)

    ax.set_yticks(y)
    ax.set_yticklabels(top_ga["player"])

    for i, (g, a) in enumerate(zip(top_ga["goals"], top_ga["assists"])):
        ax.text(g + 0.2, i + width / 2, str(int(g)), va="center", fontsize=9)
        ax.text(a + 0.2, i - width / 2, str(int(a)), va="center", fontsize=9)

    ax.set_title("GOAL CONTRIBUTIONS LEADERS (GOALS + ASSISTS)", pad=20)
    ax.set_xlabel("Count")
    ax.legend(loc="lower right")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    plt.savefig(out, dpi=150, facecolor=DARK_BG)
    plt.close(fig)


def plot_efficiency_quadrant(df: pd.DataFrame, out: Path, min_minutes: int = 2000) -> None:
    q = df[df["minutes"] >= min_minutes].copy()

    fig, ax = plt.subplots(figsize=(13, 8))

    x_med = q["xG_per_shot"].median()
    y_med = q["mins_per_goal"].median()

    ax.axvspan(x_med, q["xG_per_shot"].max() * 1.1, alpha=0.04, color=ACCENT)
    ax.axvspan(0, x_med, alpha=0.04, color=WARN)

    ax.scatter(q["xG_per_shot"], q["mins_per_goal"],
               s=q["goals"] * 25 + 40, c=q["goals"], cmap="viridis",
               edgecolors="white", alpha=0.85, linewidth=0.8)

    ax.axvline(x_med, color=NEUTRAL, linestyle=":", alpha=0.5)
    ax.axhline(y_med, color=NEUTRAL, linestyle=":", alpha=0.5)

    for _, row in q.nlargest(8, "goals").iterrows():
        ax.annotate(row["player"], (row["xG_per_shot"], row["mins_per_goal"]),
                    xytext=(7, 5), textcoords="offset points",
                    fontsize=9, fontweight="bold")

    ax.invert_yaxis()  # lower mins/goal = more prolific, so flip for intuition
    ax.set_xlabel("xG per Shot  (higher = better chance quality)")
    ax.set_ylabel("Minutes per Goal  (lower = more prolific)")
    ax.set_title("STRIKER EFFICIENCY MAP — CHANCE QUALITY vs OUTPUT", pad=20)
    ax.grid(True, alpha=0.15)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    plt.savefig(out, dpi=150, facecolor=DARK_BG)
    plt.close(fig)


# ---------- Entry point ----------
def main() -> None:
    plt.rcParams.update(PLOT_STYLE)
    OUT_DIR.mkdir(exist_ok=True)

    df = load_and_enrich(CSV_PATH)
    print(f"Loaded {len(df)} players from {CSV_PATH}")

    print("\nTop 5 xG overperformers (goals - xG):")
    print(
        df.nlargest(5, "xG_diff")[["player", "team", "goals", "xG", "xG_diff"]]
          .to_string(index=False)
    )

    print("\nTop 5 xG underperformers:")
    print(
        df.nsmallest(5, "xG_diff")[["player", "team", "goals", "xG", "xG_diff"]]
          .to_string(index=False)
    )

    plot_top_scorers(df,          OUT_DIR / "01_top_scorers.png")
    plot_goals_vs_xg(df,          OUT_DIR / "02_goals_vs_xg.png")
    plot_conversion_rate(df,      OUT_DIR / "03_conversion_rate.png")
    plot_goal_contributions(df,   OUT_DIR / "04_goal_contributions.png")
    plot_efficiency_quadrant(df,  OUT_DIR / "05_efficiency_quadrant.png")

    generated = sorted(OUT_DIR.glob("*.png"))
    print(f"\nGenerated {len(generated)} charts in {OUT_DIR}/")
    for f in generated:
        print(f"  - {f.name}")


if __name__ == "__main__":
    main()
