"""
fisher_figures_table.py

Reads fisher_data.xlsx and produces the four figures and one table from
the blog post on true expected inflation and the ex-ante real interest rate.

Outputs
-------
1. inflation_measures.png          Measures of inflation (2003-)
2. treasury_yields.png             Fed funds rate and 1-, 5-, 10-year Treasury yields (2003-)
3. inflation_expectations.png      Market- (Cleveland Fed) and survey-based (Michigan) expected inflation (2003-)
4. real_rates.png                  Ex-ante real fed funds (market- and survey-based) and real 10-year rate,
                                    shaded by core PCE inflation threshold (2003-)
5. rate_comparison_2006_2026.png   Table: nominal, ex-ante real, and inflation rates, August 2006 vs. May 2026
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

DATA_PATH = Path(__file__).parent / "fisher_data.xlsx"
OUT_DIR = Path(__file__).parent / "output" / "figures"
TABLE_DIR = Path(__file__).parent / "output" / "tables"
OUT_DIR.mkdir(parents=True, exist_ok=True)
TABLE_DIR.mkdir(parents=True, exist_ok=True)

FONT_FAMILY = "Arial"
BASE_FONT_SIZE = 12
SMALL_FONT_SIZE = 11
START = pd.Timestamp("2003-01-01")

NBER_RECESSIONS = [
    ("2007-12-01", "2009-06-30"),
    ("2020-02-01", "2020-04-30"),
]

PCE_CORE_COLUMN = "PCEPILFE_PC1"
# (lower bound inclusive, upper bound exclusive or None for open-ended, color, alpha)
PCE_CORE_BANDS = [
    (2.25, 2.75, "yellow", 0.15),
    (2.75, None, "red", 0.12),
]


# ── Data loading ─────────────────────────────────────────────────────────

def load_monthly_data(path: Path) -> pd.DataFrame:
    """Load the Monthly sheet from the master workbook.

    Parameters
    ----------
    path : Path
        Path to the master Excel workbook.

    Returns
    -------
    pandas.DataFrame
        Monthly sheet indexed by observation_date, from START onward.
    """
    df = pd.read_excel(path, sheet_name="Monthly")
    df = df.set_index("observation_date").sort_index()
    return df.loc[df.index >= START]


# ── Shared helpers (house style) ─────────────────────────────────────────

def natural_sort_key(series_id: str):
    """Sort key that orders embedded numbers by magnitude, not by character.

    Plain alphabetical sort puts "GS10" before "GS5" and "EXPINF10YR" before
    "EXPINF1YR" because it compares character-by-character. This key splits
    off digit runs and compares them as integers instead.

    Parameters
    ----------
    series_id : str
        A FRED series identifier, e.g. "GS10" or "EXPINF5YR".

    Returns
    -------
    list
        Key usable with sorted(..., key=natural_sort_key).
    """
    import re

    return [
        int(chunk) if chunk.isdigit() else chunk.lower()
        for chunk in re.split(r"(\d+)", series_id)
    ]


def oxford_comma_join(items: list) -> str:
    """Join a list of strings with commas and a trailing oxford comma.

    Parameters
    ----------
    items : list of str
        Items to join, already in the desired order.

    Returns
    -------
    str
        Comma-separated string, e.g. "A, B, and C".
    """
    if len(items) <= 1:
        return "".join(items)
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def new_figure(figsize: tuple = (12, 6)):
    """Create a figure and axes with the house-style base font applied.

    Parameters
    ----------
    figsize : tuple of float
        Figure size in inches, (width, height).

    Returns
    -------
    tuple
        (matplotlib.figure.Figure, matplotlib.axes.Axes)
    """
    plt.rcParams["font.family"] = FONT_FAMILY
    plt.rcParams["font.size"] = BASE_FONT_SIZE
    return plt.subplots(figsize=figsize)


def add_recession_bars(ax, recessions: list = NBER_RECESSIONS) -> None:
    """Shade NBER recession periods on a time-series axis.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        Axes with a datetime x-axis.
    recessions : list of tuple of str
        (start, end) date strings for each recession to shade.
    """
    for start, end in recessions:
        ax.axvspan(pd.Timestamp(start), pd.Timestamp(end), color="gray", alpha=0.2, zorder=0)


def add_pce_core_band_bars(ax, df: pd.DataFrame, bands: list = PCE_CORE_BANDS) -> None:
    """Shade months where year-over-year core PCE inflation falls in a band.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        Axes with a datetime x-axis.
    df : pandas.DataFrame
        Monthly data indexed by observation_date, containing PCE_CORE_COLUMN.
    bands : list of tuple of (float, float or None, str, float)
        (lower, upper, color, alpha) tuples. A month is shaded when core PCE
        year-over-year percent change falls in [lower, upper); upper=None
        means no upper bound.
    """
    for lower, upper, color, alpha in bands:
        mask = df[PCE_CORE_COLUMN] >= lower
        if upper is not None:
            mask &= df[PCE_CORE_COLUMN] < upper
        episode_id = (mask != mask.shift()).cumsum()
        for _, episode in df[mask].groupby(episode_id[mask]):
            start = episode.index.min()
            end = episode.index.max() + pd.offsets.MonthEnd(1)
            ax.axvspan(start, end, color=color, alpha=alpha, zorder=0)


def apply_house_style(ax) -> None:
    """Apply the house-style axes styling.

    Removes the top/right spines, adds horizontal gridlines, and draws a
    zero reference line. Call after plotting the data series.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        Axes to style.
    """
    ax.axhline(0, color="black", linewidth=0.8, zorder=1)
    ax.grid(axis="y", color="gray", alpha=0.3, zorder=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def add_bottom_legend(ax, ncol: int) -> None:
    """Add a single-row legend below the axes, matching house style.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        Axes to attach the legend to.
    ncol : int
        Number of columns in the legend (typically the number of series).
    """
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.1),
        ncol=ncol,
        frameon=False,
        fontsize=SMALL_FONT_SIZE,
        columnspacing=1.2,
        handletextpad=0.5,
    )


def add_sources_note(ax, series_ids: list, prefix: str = "FRED series") -> None:
    """Add a left-justified sources line below the legend.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        Axes to attach the note to.
    series_ids : list of str
        Series identifiers to list, in the order given (typically natural
        sort order).
    prefix : str
        Text naming the data source, inserted before the series list.
    """
    names = oxford_comma_join(series_ids)
    label = "Sources" if len(series_ids) > 1 else "Source"
    ax.text(
        0.0,
        -0.24,
        f"{label}: {prefix} {names}",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=SMALL_FONT_SIZE,
    )


def save_figure(fig, output_path: Path) -> None:
    """Save a figure with the house-style export settings.

    Parameters
    ----------
    fig : matplotlib.figure.Figure
        Figure to save.
    output_path : Path
        Destination file path; parent directories are created if needed.
    """
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {output_path}")


# ── Figure 1: measures of inflation ──────────────────────────────────────

INFLATION_SERIES = {
    "CPIAUCSL_PC1": "CPI all items",
    "CPILFESL_PC1": "CPI core",
    "PCEPI_PC1": "PCE price index",
    "PCEPILFE_PC1": "PCE core",
    "TRMMEANCPIM159SFRBCLE": "Trimmed mean CPI",
}


def fig1_inflation_measures(df: pd.DataFrame) -> None:
    """Plot year-over-year inflation measures.

    Parameters
    ----------
    df : pandas.DataFrame
        Monthly data indexed by observation_date.
    """
    fig, ax = new_figure()
    add_recession_bars(ax)

    for column, label in sorted(INFLATION_SERIES.items(), key=lambda item: item[1]):
        ax.plot(df.index, df[column], label=label, linewidth=1.5, zorder=2)

    ax.set_ylabel("Percent change from a year ago")
    apply_house_style(ax)
    add_bottom_legend(ax, ncol=len(INFLATION_SERIES))
    fred_series_names = [key.replace("_PC1", "") for key in INFLATION_SERIES.keys()]
    add_sources_note(ax, sorted(fred_series_names, key=natural_sort_key))

    save_figure(fig, OUT_DIR / "inflation_measures.png")


# ── Figure 2: nominal Treasury yields and fed funds rate ─────────────────

YIELD_SERIES = {
    "FEDFUNDS": "Fed funds",
    "GS1": "1 year",
    "GS5": "5 year",
    "GS10": "10 year",
}


def fig2_treasury_yields(df: pd.DataFrame) -> None:
    """Plot the fed funds rate and 1-, 5-, and 10-year Treasury yields.

    Parameters
    ----------
    df : pandas.DataFrame
        Monthly data indexed by observation_date.
    """
    fig, ax = new_figure()
    add_recession_bars(ax)

    for column, label in YIELD_SERIES.items():
        ax.plot(df.index, df[column], label=label, linewidth=1.5, zorder=2)

    ax.set_ylabel("Percent")
    apply_house_style(ax)
    add_bottom_legend(ax, ncol=len(YIELD_SERIES))
    add_sources_note(ax, sorted(YIELD_SERIES.keys(), key=natural_sort_key))

    save_figure(fig, OUT_DIR / "treasury_yields.png")


# ── Figure 3: expected inflation, market- and survey-based ───────────────

EXPECTATIONS_SERIES = {
    "EXPINF1YR": "1 year",
    "MICH": "1 year (survey)",
    "EXPINF5YR": "5 year",
    "EXPINF10YR": "10 year",
}


def fig3_inflation_expectations(df: pd.DataFrame) -> None:
    """Plot market- and survey-based expected inflation.

    Parameters
    ----------
    df : pandas.DataFrame
        Monthly data indexed by observation_date.
    """
    fig, ax = new_figure()
    add_recession_bars(ax)

    for column, label in EXPECTATIONS_SERIES.items():
        ax.plot(df.index, df[column], label=label, linewidth=1.5, zorder=2)

    ax.set_ylabel("Percent")
    apply_house_style(ax)
    add_bottom_legend(ax, ncol=len(EXPECTATIONS_SERIES))
    add_sources_note(ax, sorted(EXPECTATIONS_SERIES.keys(), key=natural_sort_key))

    save_figure(fig, OUT_DIR / "inflation_expectations.png")


# ── Figure 4: ex-ante real rates ─────────────────────────────────────────

# label -> (nominal yield column, expected inflation column)
REAL_RATE_SERIES = {
    "Fed funds": ("FEDFUNDS", "EXPINF1YR"),
    "Fed funds (survey)": ("FEDFUNDS", "MICH"),
    "10 year": ("GS10", "EXPINF10YR"),
}


def fig4_real_rates(df: pd.DataFrame) -> None:
    """Plot ex-ante real fed funds and real 10-year rates, with core PCE shading.

    Parameters
    ----------
    df : pandas.DataFrame
        Monthly data indexed by observation_date.
    """
    fig, ax = new_figure()
    add_recession_bars(ax)
    add_pce_core_band_bars(ax, df)

    for label, (yield_col, inflation_col) in REAL_RATE_SERIES.items():
        real_rate = df[yield_col] - df[inflation_col]
        ax.plot(df.index, real_rate, label=label, linewidth=1.5, zorder=2)

    ax.set_ylabel("Percent")
    apply_house_style(ax)
    add_bottom_legend(ax, ncol=len(REAL_RATE_SERIES))

    raw_series_ids = {col for pair in REAL_RATE_SERIES.values() for col in pair} | {PCE_CORE_COLUMN}
    fred_series_names = [col.replace("_PC1", "") for col in raw_series_ids]
    add_sources_note(ax, sorted(fred_series_names, key=natural_sort_key))

    save_figure(fig, OUT_DIR / "real_rates.png")


# ── Table 1: rate comparison, August 2006 vs. May 2026 ───────────────────

TABLE_DATES = [pd.Timestamp("2006-08-01"), pd.Timestamp("2026-05-01")]
TABLE_COLUMN_LABELS = ["August 2006", "May 2026"]

TABLE_ROWS = [
    ("Fed funds rate", lambda r: r["FEDFUNDS"]),
    ("Real fed funds (market-based)", lambda r: r["FEDFUNDS"] - r["EXPINF1YR"]),
    ("Real fed funds (survey-based)", lambda r: r["FEDFUNDS"] - r["MICH"]),
    ("Real 10-year rate", lambda r: r["GS10"] - r["EXPINF10YR"]),
    ("PCE-core inflation", lambda r: r["PCEPILFE_PC1"]),
]


def build_rate_comparison_table(df: pd.DataFrame) -> pd.DataFrame:
    """Compute the August 2006 vs. May 2026 rate comparison table.

    Parameters
    ----------
    df : pandas.DataFrame
        Monthly data indexed by observation_date.

    Returns
    -------
    pandas.DataFrame
        Rows are labels, columns are TABLE_COLUMN_LABELS, values are percent.
    """
    data = {
        col_label: [formula(df.loc[date]) for _, formula in TABLE_ROWS]
        for col_label, date in zip(TABLE_COLUMN_LABELS, TABLE_DATES)
    }
    return pd.DataFrame(data, index=[label for label, _ in TABLE_ROWS])


def table1_rate_comparison(df: pd.DataFrame) -> None:
    """Render the rate comparison table as a publication-ready PNG.

    Manually places text and rule lines for precise control over spacing
    and the final tight-cropped image.

    Parameters
    ----------
    df : pandas.DataFrame
        Monthly data indexed by observation_date.
    """
    table = build_rate_comparison_table(df)

    plt.rcParams["font.family"] = FONT_FAMILY

    label_x = 0.0
    col_x = [0.64, 0.92]
    n_rows = len(table)
    total_bands = n_rows + 1  # +1 for the header band

    fig, ax = plt.subplots(figsize=(5.4, 0.5 * total_bands))
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    def band_center_y(band_index: int) -> float:
        return 1 - (band_index + 0.5) / total_bands

    header_y = band_center_y(0)
    for col_label, x in zip(table.columns, col_x):
        ax.text(x, header_y, col_label, fontsize=10, fontweight="bold", ha="center", va="center")
    rule_y = 1 - 1.0 / total_bands
    ax.plot([col_x[0] - 0.16, 1.0], [rule_y, rule_y], color="black", linewidth=1.2)

    for i, (row_label, values) in enumerate(table.iterrows()):
        y = band_center_y(i + 1)
        ax.text(label_x, y, row_label, fontsize=10, fontweight="bold", ha="left", va="center")
        for value, x in zip(values, col_x):
            ax.text(x, y, f"{value:.2f}%", fontsize=10, ha="center", va="center")
        band_bottom = 1 - (i + 2) / total_bands
        ax.plot([label_x, 1.0], [band_bottom, band_bottom], color="#d9d9d9", linewidth=0.8)

    output_path = TABLE_DIR / "rate_comparison_2006_2026.png"
    fig.savefig(output_path, dpi=300, bbox_inches="tight", pad_inches=0.1)
    plt.close(fig)
    print(f"Saved: {output_path}")


# ── Main ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    monthly = load_monthly_data(DATA_PATH)

    fig1_inflation_measures(monthly)
    fig2_treasury_yields(monthly)
    fig3_inflation_expectations(monthly)
    fig4_real_rates(monthly)
    table1_rate_comparison(monthly)
