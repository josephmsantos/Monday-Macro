"""
blog_figures.py

Reads great_expectations_data.xlsx and produces the eight figures from
'Breakeven Yields Understate Expected Inflation'.

Figures
-------
1. inflation_measures.png         Measures of inflation (2003–)
2. GS5_FII5_lines.png             5-year Treasury and TIPS yields (2003–)
3. breakeven_line.png             5-year breakeven inflation (2003–)
4. expected_breakeven_lines.png   Breakeven and Cleveland Fed expected inflation (2003–)
5. EXPINF5YR_errors_line.png      5-year expected minus actual inflation measures (line)
6. fed_bondsheld_lines.png        Fed Treasury holdings in levels (2003–)
7. fed_bondsheld_indexed_2026.png Fed Treasury holdings indexed to Jan 7, 2026 = 100
8. expected1yr_michigan_lines.png 1-year Cleveland Fed and Michigan expectations (2003–)
"""

from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

DATA_PATH = Path(__file__).parent / "great_expectations_data.xlsx"
OUT_DIR   = Path(__file__).parent / "output" / "figures"
OUT_DIR.mkdir(parents=True, exist_ok=True)

START = pd.Timestamp("2003-01-01")

RECESSIONS = [
    ("2007-12-01", "2009-06-01"),
    ("2020-02-01", "2020-04-01"),
]


# ── Data loading ──────────────────────────────────────────────────────────

def load_data():
    """Load monthly and weekly sheets from the dataset Excel file.

    Returns
    -------
    monthly : pd.DataFrame
        Monthly dataset, 2003-01 onward.
    weekly : pd.DataFrame
        Weekly Fed holdings (WSHONBNL, WSHONBIIL), full history.
    """
    monthly = pd.read_excel(DATA_PATH, sheet_name="Monthly",
                            parse_dates=["observation_date"])
    monthly = monthly.sort_values("observation_date").reset_index(drop=True)

    weekly = pd.read_excel(DATA_PATH, sheet_name="Weekly",
                           parse_dates=["observation_date"])
    weekly = weekly.sort_values("observation_date").reset_index(drop=True)

    return monthly, weekly


# ── Shared helpers ────────────────────────────────────────────────────────

def fred_source(*series):
    """Return an alphabetically sorted FRED source line."""
    return "FRED series: " + ", ".join(sorted(series))


def shade_recessions(ax):
    """Add NBER recession bands to ax."""
    for start, end in RECESSIONS:
        ax.axvspan(pd.Timestamp(start), pd.Timestamp(end),
                   color="gray", alpha=0.2, linewidth=0)


def style_axes(ax, ylabel, fontsize=9):
    """Apply standard axis styling: label, spine, grid, tick format."""
    ax.set_ylabel(ylabel, fontsize=fontsize)
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.tick_params(axis="x", rotation=0)
    ax.tick_params(labelsize=10)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", linestyle="--", alpha=0.4)


def add_legend(ax, ncol=2, y_anchor=-0.12, fontsize=9):
    """Place legend below axes, centered, no frame."""
    ax.legend(ncol=ncol, loc="upper center",
              bbox_to_anchor=(0.5, y_anchor),
              fontsize=fontsize, frameon=False)


def save_fig(fig, path, source, source_y=-0.04):
    """Attach source line, apply tight layout, save, and close."""
    fig.text(0.01, source_y, source, fontsize=8, color="gray")
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {path}")


# ── Figure functions ──────────────────────────────────────────────────────

def fig1_inflation_measures(df):
    """Line chart of five inflation measures from 2003.

    Parameters
    ----------
    df : pd.DataFrame
        Monthly dataset.
    """
    # Alphabetical legend order
    series = [
        ("CPIAUCSL_PC1",          "CPI",           "#2166ac"),
        ("TRMMEANCPIM159SFRBCLE", "CPI (16 trim)", "#984ea3"),
        ("CPILFESL_PC1",          "CPI (core)",    "#74add1"),
        ("PCEPI_PC1",             "PCE",           "#d4813a"),
        ("PCEPILFE_PC1",          "PCE (core)",    "#1a9e6e"),
    ]
    data = df[df["observation_date"] >= START].dropna(
        subset=[col for col, _, _ in series])

    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    shade_recessions(ax)

    for col, label, color in series:
        ax.plot(data["observation_date"], data[col],
                color=color, linewidth=1.2, label=label)

    ax.axhline(0, color="black", linewidth=0.6)
    style_axes(ax, "Year-over-year percentage change", fontsize=10)
    add_legend(ax, ncol=5, y_anchor=-0.12, fontsize=8)
    save_fig(fig, OUT_DIR / "inflation_measures.png",
             fred_source("CPIAUCSL", "CPILFESL", "PCEPI", "PCEPILFE",
                         "TRMMEANCPIM159SFRBCLE"),
             source_y=-0.06)


def fig2_gs5_fii5(df):
    """Line chart of 5-year nominal Treasury and TIPS yields from 2003.

    Parameters
    ----------
    df : pd.DataFrame
        Monthly dataset.
    """
    data = df[df["observation_date"] >= START].dropna(subset=["GS5", "FII5"])

    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    shade_recessions(ax)

    # Alphabetical: FII5 before GS5
    ax.plot(data["observation_date"], data["FII5"],
            color="#1a9e6e", linewidth=1.2, label="5-Year TIPS")
    ax.plot(data["observation_date"], data["GS5"],
            color="#2166ac", linewidth=1.2, label="5-Year Treasury")

    style_axes(ax, "Yields to maturity (percent)")
    add_legend(ax, ncol=2)
    save_fig(fig, OUT_DIR / "GS5_FII5_lines.png",
             fred_source("FII5", "GS5"),
             source_y=-0.04)


def fig3_breakeven(df):
    """Line chart of 5-year breakeven inflation (no legend).

    Parameters
    ----------
    df : pd.DataFrame
        Monthly dataset.
    """
    data = df[df["observation_date"] >= START].dropna(subset=["BREAKEVEN"])

    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    shade_recessions(ax)

    ax.plot(data["observation_date"], data["BREAKEVEN"],
            color="#1a9e6e", linewidth=1.2)

    style_axes(ax, "Percent")
    save_fig(fig, OUT_DIR / "breakeven_line.png",
             fred_source("FII5", "GS5"))


def fig4_expected_breakeven(df):
    """Line chart of breakeven and Cleveland Fed 5-year expected inflation.

    Parameters
    ----------
    df : pd.DataFrame
        Monthly dataset.
    """
    data = df[df["observation_date"] >= START].dropna(
        subset=["BREAKEVEN", "EXPINF5YR"])

    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    shade_recessions(ax)

    # Alphabetical: Breakeven before Expected
    ax.plot(data["observation_date"], data["BREAKEVEN"],
            color="#1a9e6e", linewidth=1.2, label="Breakeven (5 year)")
    ax.plot(data["observation_date"], data["EXPINF5YR"],
            color="#d4813a", linewidth=1.2, label="Expected (5 year)")

    style_axes(ax, "Percent")
    add_legend(ax, ncol=2)
    save_fig(fig, OUT_DIR / "expected_breakeven_lines.png",
             fred_source("EXPINF5YR", "FII5", "GS5"),
             source_y=-0.04)


def fig5_expinf5yr_errors_line(df):
    """Line chart of 5-year expected inflation minus each actual measure (60 months forward).

    X-axis shows the date on which actual inflation was realized (t + 60 months).

    Parameters
    ----------
    df : pd.DataFrame
        Monthly dataset.
    """
    # Alphabetical legend order
    measures = [
        ("CPIAUCSL_PC1",          "CPI",           "#2166ac"),
        ("TRMMEANCPIM159SFRBCLE", "CPI (16 trim)", "#984ea3"),
        ("CPILFESL_PC1",          "CPI (core)",    "#74add1"),
        ("PCEPI_PC1",             "PCE",           "#d4813a"),
        ("PCEPILFE_PC1",          "PCE (core)",    "#1a9e6e"),
    ]

    fig, ax = plt.subplots(figsize=(6.5, 4.5))

    for col, label, color in measures:
        # Shift realized inflation dates back 60 months so they merge on expectation date
        realized = df[["observation_date", col]].copy()
        realized["observation_date"] = (
            realized["observation_date"] - pd.DateOffset(months=60)
        )
        merged = (
            df[["observation_date", "EXPINF5YR"]]
            .merge(realized, on="observation_date")
            .dropna()
        )
        merged = merged[merged["observation_date"] >= START]

        plot_dates = merged["observation_date"] + pd.DateOffset(months=60)
        errors = merged["EXPINF5YR"] - merged[col]
        ax.plot(plot_dates, errors, color=color, linewidth=1.2, label=label)

    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xlabel("Date actual inflation realized", fontsize=9, labelpad=8)
    style_axes(ax, "Percentage points")
    add_legend(ax, ncol=5, y_anchor=-0.18, fontsize=8)
    save_fig(fig, OUT_DIR / "EXPINF5YR_errors_line.png",
             fred_source("CPIAUCSL", "CPILFESL", "EXPINF5YR", "PCEPI", "PCEPILFE",
                         "TRMMEANCPIM159SFRBCLE"),
             source_y=-0.08)


def fig6_fed_holdings_level(df):
    """Line chart of Fed outright Treasury holdings in trillions from 2003.

    Parameters
    ----------
    df : pd.DataFrame
        Monthly dataset (WSHONBNL and WSHONBIIL in millions).
    """
    data = df[df["observation_date"] >= START].dropna(
        subset=["WSHONBNL", "WSHONBIIL"]).copy()
    data["NOM_T"]  = data["WSHONBNL"]  / 1_000_000
    data["TIPS_T"] = data["WSHONBIIL"] / 1_000_000

    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    shade_recessions(ax)

    ax.plot(data["observation_date"], data["NOM_T"],
            color="#2166ac", linewidth=1.2, label="Nominal Treasury Bonds")
    ax.plot(data["observation_date"], data["TIPS_T"],
            color="#1a9e6e", linewidth=1.2, label="TIPS")

    style_axes(ax, "Trillions of dollars")
    add_legend(ax, ncol=2)
    save_fig(fig, OUT_DIR / "fed_bondsheld_lines.png",
             fred_source("WSHONBIIL", "WSHONBNL"),
             source_y=-0.04)


def fig7_fed_holdings_indexed(weekly):
    """Line chart of Fed holdings indexed to 100 at January 7, 2026.

    Uses weekly data so the January 21, 2026 divergence is fully visible.

    Parameters
    ----------
    weekly : pd.DataFrame
        Weekly Fed holdings dataset (WSHONBNL, WSHONBIIL in millions).
    """
    data = weekly[
        weekly["observation_date"] >= pd.Timestamp("2026-01-01")
    ].copy().reset_index(drop=True)

    base_nom  = data["WSHONBNL"].iloc[0]
    base_tips = data["WSHONBIIL"].iloc[0]
    data["NOM_IDX"]  = 100 * data["WSHONBNL"]  / base_nom
    data["TIPS_IDX"] = 100 * data["WSHONBIIL"] / base_tips

    fig, ax = plt.subplots(figsize=(6.5, 4.5))

    ax.plot(data["observation_date"], data["NOM_IDX"],
            color="#2166ac", linewidth=1.2, label="Nominal Treasury Bonds")
    ax.plot(data["observation_date"], data["TIPS_IDX"],
            color="#1a9e6e", linewidth=1.2, label="TIPS")

    ax.axhline(100, color="black", linewidth=0.8)
    ax.set_ylabel("Index (first observation = 100)", fontsize=9)
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.tick_params(axis="x", rotation=0)
    ax.tick_params(labelsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    add_legend(ax, ncol=2, y_anchor=-0.22)
    save_fig(fig, OUT_DIR / "fed_bondsheld_indexed_2026.png",
             fred_source("WSHONBIIL", "WSHONBNL"),
             source_y=-0.08)


def fig8_expected1yr_michigan(df):
    """Line chart of 1-year Cleveland Fed and Michigan inflation expectations from 2003.

    Parameters
    ----------
    df : pd.DataFrame
        Monthly dataset.
    """
    data = df[df["observation_date"] >= START].dropna(
        subset=["EXPINF1YR", "MICH"])

    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    shade_recessions(ax)

    # Alphabetical: Expected before Michigan
    ax.plot(data["observation_date"], data["EXPINF1YR"],
            color="#2166ac", linewidth=1.2, label="Expected (1 year)")
    ax.plot(data["observation_date"], data["MICH"],
            color="#d4813a", linewidth=1.2, label="Michigan (1 year)")

    style_axes(ax, "Percent")
    add_legend(ax, ncol=2)
    save_fig(fig, OUT_DIR / "expected1yr_michigan_lines.png",
             fred_source("EXPINF1YR", "MICH"),
             source_y=-0.04)


# ── Main ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    monthly, weekly = load_data()

    fig1_inflation_measures(monthly)
    fig2_gs5_fii5(monthly)
    fig3_breakeven(monthly)
    fig4_expected_breakeven(monthly)
    fig5_expinf5yr_errors_line(monthly)
    fig6_fed_holdings_level(monthly)
    fig7_fed_holdings_indexed(weekly)
    fig8_expected1yr_michigan(monthly)
