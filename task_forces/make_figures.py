"""Read data.xlsx and produce all six figures in one run.

Self-contained: no imports beyond the standard scientific stack, so this
file and data.xlsx are the only two things needed to reproduce the figures.
"""

import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parent
DATA_PATH = PROJECT_DIR / "data.xlsx"
FIGURES_DIR = PROJECT_DIR / "output" / "figures"

FONT_FAMILY = "Arial"
BASE_FONT_SIZE = 12
SMALL_FONT_SIZE = 11

NBER_RECESSIONS = [
    ("2007-12-01", "2009-06-30"),
    ("2020-02-01", "2020-04-30"),
]


# --- house style helpers -----------------------------------------------


def new_figure(figsize=(12, 6)):
    """Create a new figure/axes pair with the house font applied.

    Parameters
    ----------
    figsize : tuple of float
        Width and height in inches.

    Returns
    -------
    fig, ax : matplotlib Figure and Axes
    """
    plt.rcParams["font.family"] = FONT_FAMILY
    plt.rcParams["font.size"] = BASE_FONT_SIZE
    fig, ax = plt.subplots(figsize=figsize)
    return fig, ax


def apply_house_style(ax, x_is_time=True):
    """Apply the standard spine, gridline, and font formatting to an axes.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
    x_is_time : bool
        If True, omit the x-axis label (time axis is self-evident).
    """
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(True)
    ax.spines["bottom"].set_visible(True)

    ax.yaxis.grid(True, alpha=0.3)
    ax.xaxis.grid(False)
    ax.set_axisbelow(True)

    ax.tick_params(axis="both", labelsize=BASE_FONT_SIZE)
    ax.xaxis.label.set_size(BASE_FONT_SIZE)
    ax.yaxis.label.set_size(BASE_FONT_SIZE)

    if x_is_time:
        ax.set_xlabel("")


def add_bottom_legend(ax):
    """Add a single-row, alphabetized, frameless legend below the axes.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
    """
    handles, labels = ax.get_legend_handles_labels()
    order = sorted(range(len(labels)), key=lambda i: labels[i].lower())
    handles = [handles[i] for i in order]
    labels = [labels[i] for i in order]

    ax.legend(
        handles,
        labels,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.1),
        ncol=len(labels),
        frameon=False,
        fontsize=SMALL_FONT_SIZE,
    )


def add_recession_bars(ax, recessions=NBER_RECESSIONS):
    """Shade NBER recession periods on a time series axes.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
    recessions : list of (str, str)
        Start and end dates (ISO format) for each recession to shade.
    """
    for start, end in recessions:
        ax.axvspan(start, end, color="gray", alpha=0.2, linewidth=0)


def oxford_comma_join(items):
    """Join a list of strings with commas and an Oxford comma before 'and'.

    Parameters
    ----------
    items : list of str

    Returns
    -------
    str
    """
    if len(items) == 0:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def natural_sort_key(series_id):
    """Sort key that orders numeric suffixes by magnitude, not lexically.

    Parameters
    ----------
    series_id : str

    Returns
    -------
    list
        Mixed list of strings and ints for comparison.
    """
    return [int(chunk) if chunk.isdigit() else chunk for chunk in re.split(r"(\d+)", series_id)]


def add_sources_note(ax, series_ids):
    """Add a left-justified "Sources: FRED series ..." line below the legend.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
    series_ids : list of str
        FRED series IDs to cite, in natural-sorted order.
    """
    ids_sorted = sorted(series_ids, key=natural_sort_key)
    label = "Source" if len(ids_sorted) == 1 else "Sources"
    text = f"{label}: FRED series {oxford_comma_join(ids_sorted)}"
    ax.text(0.0, -0.24, text, transform=ax.transAxes, ha="left", va="top", fontsize=SMALL_FONT_SIZE)


def save_figure(fig, path):
    """Save a figure with a tight bounding box at 300 dpi.

    Parameters
    ----------
    fig : matplotlib.figure.Figure
    path : pathlib.Path
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight", dpi=300)
    plt.close(fig)


# --- figures -------------------------------------------------------------


def plot_balance_sheet_liabilities(balance_sheet):
    """Total liabilities and capital vs. the monetary base, in trillions."""
    series = {"RESPPLNWW": "Total Liabilities and Capital", "BOGMBASE": "Monetary Base"}

    fig, ax = new_figure()
    for column, label in series.items():
        ax.plot(balance_sheet.index, balance_sheet[column] / 1_000_000, label=label)

    add_recession_bars(ax)
    apply_house_style(ax)
    ax.set_xlim(balance_sheet.index.min(), balance_sheet.index.max())
    ax.set_ylabel("Trillions of dollars")
    add_bottom_legend(ax)
    add_sources_note(ax, list(series.keys()))

    save_figure(fig, FIGURES_DIR / "liabilities_and_capital_vs_monetary_base.png")


def plot_balance_sheet_assets(balance_sheet):
    """Total assets vs. Treasury and MBS holdings, in trillions."""
    series = {
        "RESPPANWW": "Total Assets",
        "TREAST": "U.S. Treasury Securities",
        "WSHOMCB": "Mortgage-Backed Securities",
    }

    fig, ax = new_figure()
    for column, label in series.items():
        ax.plot(balance_sheet.index, balance_sheet[column] / 1_000_000, label=label)

    add_recession_bars(ax)
    apply_house_style(ax)
    ax.set_xlim(balance_sheet.index.min(), balance_sheet.index.max())
    ax.set_ylabel("Trillions of dollars")
    add_bottom_legend(ax)
    add_sources_note(ax, list(series.keys()))

    save_figure(fig, FIGURES_DIR / "assets_treasuries_and_mbs.png")


def plot_inflation_measures(inflation):
    """Year-over-year inflation rates across all five price index series."""
    series = {
        "CPIAUCSL_PC1": "CPI",
        "CPILFESL_PC1": "Core CPI",
        "PCEPI_PC1": "PCE",
        "PCEPILFE_PC1": "Core PCE",
        "TRMMEANCPIM159SFRBCLE": "Trimmed-Mean CPI",
    }

    fig, ax = new_figure()
    for column, label in series.items():
        ax.plot(inflation.index, inflation[column], label=label)

    add_recession_bars(ax)
    apply_house_style(ax)
    ax.set_xlim(inflation.index.min(), inflation.index.max())
    ax.set_ylabel("Year-over-year percent change")
    add_bottom_legend(ax)
    fred_series_names = [key.replace("_PC1", "") for key in series.keys()]
    add_sources_note(ax, sorted(fred_series_names, key=natural_sort_key))

    save_figure(fig, FIGURES_DIR / "yoy_inflation_by_measure.png")


def plot_taylor_rule(taylor_rule):
    """Actual fed funds rate vs. a custom Taylor rule prescription."""
    series = {
        "actual_fed_funds_rate": "Actual Fed Funds Rate",
        "taylor_rule_prescription": "Taylor Rule Prescription",
    }

    fig, ax = new_figure()
    for column, label in series.items():
        ax.plot(taylor_rule.index, taylor_rule[column], label=label)

    add_recession_bars(ax)
    apply_house_style(ax)
    ax.set_xlim(taylor_rule.index.min(), taylor_rule.index.max())
    ax.set_ylabel("Percent")
    add_bottom_legend(ax)
    ax.text(
        0.0,
        -0.24,
        "Source: Federal Reserve Bank of Atlanta, Taylor Rule Utility",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=SMALL_FONT_SIZE,
    )

    save_figure(fig, FIGURES_DIR / "taylor_rule_vs_actual.png")


def quarter_label(observation_date):
    """Format a quarter's observation date as e.g. '2026 Q2'."""
    period = pd.Period(observation_date, freq="Q")
    return f"{period.year} Q{period.quarter}"


def plot_gdp_revision_size(gdp_revisions):
    """Size of each BEA revision to year-over-year real GDP growth."""
    included_quarters = pd.to_datetime(["2025-10-01", "2026-01-01"])
    diff_order = ["Second Revision", "Third Revision"]
    diff_colors = {"Second Revision": "#6baed6", "Third Revision": "#2171b5"}

    df = gdp_revisions[gdp_revisions["quarter"].isin(included_quarters)]
    quarters = sorted(df["quarter"].unique())

    growth = df.pivot(index="quarter", columns="revision", values="yoy_growth")
    diffs = pd.DataFrame(
        {
            "Second Revision": growth["Second"] - growth["Advance"],
            "Third Revision": growth["Third"] - growth["Second"],
        }
    )

    fig, ax = new_figure()
    n_stages = len(diff_order)
    bar_width = 0.8 / n_stages
    x = np.arange(len(quarters))

    for i, stage in enumerate(diff_order):
        offset = (i - (n_stages - 1) / 2) * bar_width
        ax.bar(x + offset, diffs[stage].values, width=bar_width, label=stage, color=diff_colors[stage])

    apply_house_style(ax, x_is_time=False)
    ax.axhline(0, color="black", linewidth=0.8, zorder=3)
    ax.set_xticks(x)
    ax.set_xticklabels([quarter_label(q) for q in quarters])
    ax.set_ylabel("Revision size (percentage points)")
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.12),
        ncol=n_stages,
        frameon=False,
        fontsize=SMALL_FONT_SIZE,
    )
    ax.text(
        0.0,
        -0.24,
        "Sources: FRED series GDPC1 (ALFRED vintages: advance, second, and third BEA estimates)",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=SMALL_FONT_SIZE,
    )

    save_figure(fig, FIGURES_DIR / "gdp_revision_size.png")


def month_label(observation_date):
    """Format a month's observation date as e.g. 'Apr 2026'."""
    return observation_date.strftime("%b %Y")


def plot_payems_revision_size(payems_revisions):
    """Size of each BLS revision to total nonfarm payroll employment."""
    revision_stages = ["Initial", "First Revision", "Second Revision"]
    diff_order = ["First Revision", "Second Revision"]
    diff_colors = {"First Revision": "#6baed6", "Second Revision": "#2171b5"}
    n_months_shown = 2

    complete = payems_revisions.groupby("month")["revision"].nunique()
    complete_months = complete[complete == len(revision_stages)].index
    months = sorted(complete_months)[-n_months_shown:]
    df = payems_revisions[payems_revisions["month"].isin(months)]

    levels = df.pivot(index="month", columns="revision", values="level")
    diffs = pd.DataFrame(
        {
            "First Revision": levels["First Revision"] - levels["Initial"],
            "Second Revision": levels["Second Revision"] - levels["First Revision"],
        }
    )

    fig, ax = new_figure()
    n_stages = len(diff_order)
    bar_width = 0.8 / n_stages
    x = np.arange(len(months))

    for i, stage in enumerate(diff_order):
        offset = (i - (n_stages - 1) / 2) * bar_width
        ax.bar(x + offset, diffs[stage].values, width=bar_width, label=stage, color=diff_colors[stage])

    apply_house_style(ax, x_is_time=False)
    ax.axhline(0, color="black", linewidth=0.8, zorder=3)
    ax.set_xticks(x)
    ax.set_xticklabels([month_label(m) for m in months])
    ax.set_ylabel("Revision size (thousands of jobs)")
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.12),
        ncol=n_stages,
        frameon=False,
        fontsize=SMALL_FONT_SIZE,
    )
    ax.text(
        0.0,
        -0.24,
        "Sources: FRED series PAYEMS (ALFRED vintages: initial, first, and second BLS revisions)",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=SMALL_FONT_SIZE,
    )

    save_figure(fig, FIGURES_DIR / "payems_revision_size.png")


# --- data loaders ----------------------------------------------------------


def load_balance_sheet(path):
    """Load the Balance_Sheet sheet, indexed by observation_date."""
    df = pd.read_excel(path, sheet_name="Balance_Sheet")
    df["observation_date"] = pd.to_datetime(df["observation_date"])
    return df.set_index("observation_date").sort_index()


def load_inflation(path):
    """Load the Inflation sheet, indexed by observation_date."""
    df = pd.read_excel(path, sheet_name="Inflation")
    df["observation_date"] = pd.to_datetime(df["observation_date"])
    return df.set_index("observation_date").sort_index()


def load_taylor_rule(path):
    """Load the Taylor_Rule sheet, indexed by date."""
    df = pd.read_excel(path, sheet_name="Taylor_Rule")
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date").sort_index()


def load_gdp_revisions(path):
    """Load the GDP_Revisions sheet (long format)."""
    df = pd.read_excel(path, sheet_name="GDP_Revisions")
    df["quarter"] = pd.to_datetime(df["quarter"])
    return df


def load_payems_revisions(path):
    """Load the PAYEMS_Revisions sheet (long format)."""
    df = pd.read_excel(path, sheet_name="PAYEMS_Revisions")
    df["month"] = pd.to_datetime(df["month"])
    return df


if __name__ == "__main__":
    balance_sheet = load_balance_sheet(DATA_PATH)
    inflation = load_inflation(DATA_PATH)
    taylor_rule = load_taylor_rule(DATA_PATH)
    gdp_revisions = load_gdp_revisions(DATA_PATH)
    payems_revisions = load_payems_revisions(DATA_PATH)

    plot_balance_sheet_liabilities(balance_sheet)
    plot_balance_sheet_assets(balance_sheet)
    plot_inflation_measures(inflation)
    plot_taylor_rule(taylor_rule)
    plot_gdp_revision_size(gdp_revisions)
    plot_payems_revision_size(payems_revisions)

    print(f"Saved 6 figures to {FIGURES_DIR}")
