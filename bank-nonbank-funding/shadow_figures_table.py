"""
shadow_figures_table.py

Reads shadow_data.xlsx and produces the five figures and two tables in the
blog post on bank and nonbank funding of U.S. borrowers.

Outputs (output/post/)
----------------------
figure1_bank_loans.png            Bank loans, trillions of dollars (log, left) and percent
                                  of GDP (right), 1970-
table1_bank_charters.png          FDIC-insured institutions and loans by charter, Fed
                                  membership, and regulator, December 31, 2025
figure2_bank_vs_other.png         Banks vs. all other sources, percent of gross funding,
                                  decade totals
figure3_funding_shares.png        Funding by source, percent of gross funding, decade totals
table2_funding_shares.png         Funding shares, 1960s vs. 2020-25, and the change
figure4_funding_pct_gdp.png       Funding by source, percent of GDP (gross), decade totals
figure5_hyperscaler_debt.png      Debt plus finance leases of five hyperscalers and
                                  CoreWeave, 2019-2026Q2

Tables are typeset with LaTeX (booktabs) and rendered to PNG with Ghostscript;
the .tex source is always written, and the PDF/PNG need pdflatex and gs on the
PATH.

Run from any directory:  python3 shadow_figures_table.py
"""

import re
import shutil
import subprocess
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import FixedLocator, NullLocator, StrMethodFormatter

DATA_PATH = Path(__file__).parent / "shadow_data.xlsx"
OUT_DIR = Path(__file__).parent / "output" / "post"
OUT_DIR.mkdir(parents=True, exist_ok=True)

BASE_FONT_SIZE = 12
SMALL_FONT_SIZE = 11
LEGEND_Y = -0.1
SOURCES_Y = -0.24
FIG1_FIRST_YEAR = 1970
FIG1_LOG_TICKS = [0.3, 1, 3, 10]  # trillions of dollars

NBER_RECESSIONS = [
    ("1953-07-01", "1954-05-31"), ("1957-08-01", "1958-04-30"), ("1960-04-01", "1961-02-28"),
    ("1969-12-01", "1970-11-30"), ("1973-11-01", "1975-03-31"), ("1980-01-01", "1980-07-31"),
    ("1981-07-01", "1982-11-30"), ("1990-07-01", "1991-03-31"), ("2001-03-01", "2001-11-30"),
    ("2007-12-01", "2009-06-30"), ("2020-02-01", "2020-04-30"),
]

# Funding categories in stack order (bottom to top) with their colors: a
# fixed categorical palette, validated for adjacent-pair separation.
CATEGORIES = [
    ("Bank loans", "#2a78d6"),
    ("Nonbank financial loans", "#eb6834"),
    ("Private credit loans", "#1baf7a"),
    ("Government loans", "#eda100"),
    ("Other loans", "#e87ba4"),
    ("Debt securities", "#008300"),
    ("Equity", "#6250d6"),
]
BANK_COLOR, OTHER_COLOR = CATEGORIES[0][1], CATEGORIES[1][1]
Z1_SOURCE = ("Source: Federal Reserve Financial Accounts of the United States (Z.1), "
             "September 10 2026 release")

# Table 1 rows: label, class code, regulator filter (None = any), charter,
# Fed membership, primary federal regulator.
TABLE1_ROWS = [
    ("Commercial banks", "National banks", "N", None, "National", "Member", "OCC"),
    ("Commercial banks", "State member banks", "SM", None, "State", "Member", "Fed"),
    ("Commercial banks", "State nonmember banks", "NM", None, "State", "Nonmember", "FDIC"),
    ("Savings institutions", "Federal savings banks", "SB", None, "Federal", "Nonmember", "OCC"),
    ("Savings institutions", "Federal savings and loans", "SL", "OCC", "Federal", "Nonmember", "OCC"),
    ("Savings institutions", "State savings institutions", "SI", None, "State", "Nonmember", "FDIC"),
    ("Savings institutions", "State savings and loans", "SL", "FDIC", "State", "Nonmember", "FDIC"),
    ("Foreign bank branches", "Insured U.S. branches, federal license", "OI", "OCC",
     "Federal", "Nonmember", "OCC"),
    ("Foreign bank branches", "Insured U.S. branches, state license", "OI", "FDIC",
     "State", "Nonmember", "FDIC"),
]
UNINSURED_CLASS = "NC"

# Figure 5 firms in stack order with the same palette slots.
FIRMS = [("Amazon", "#2a78d6"), ("Microsoft", "#eb6834"), ("Oracle", "#1baf7a"),
         ("Alphabet", "#eda100"), ("Meta", "#e87ba4"), ("CoreWeave", "#008300")]


# ── Data loading ─────────────────────────────────────────────────────────

def load_sheet(sheet, **kwargs):
    """Read one input sheet, dropping the note rows below the data.

    Parameters
    ----------
    sheet : str
        Sheet name in shadow_data.xlsx.
    **kwargs
        Passed to ``pandas.read_excel``.

    Returns
    -------
    pandas.DataFrame
    """
    data = pd.read_excel(DATA_PATH, sheet_name=sheet, **kwargs)
    return data.dropna(how="all", subset=data.columns[1:])


def load_us_annual():
    """Annual net funding flows by category and GDP, $ millions.

    Returns
    -------
    pandas.DataFrame
        Indexed by year; a "Decade" label column, one column per category,
        and "GDP".
    """
    data = load_sheet("Fig2-4_US_Annual", dtype={"Year": str})
    data.columns = [re.sub(r" \(\$ millions\)$", "", column) for column in data.columns]
    return data.set_index(data["Year"].astype(int)).drop(columns="Year")


def decade_totals(annual):
    """Sum flows and GDP within each decade, keeping decades in time order.

    Parameters
    ----------
    annual : pandas.DataFrame

    Returns
    -------
    pandas.DataFrame
        Indexed by decade label.
    """
    return annual.groupby("Decade", sort=False).sum(numeric_only=True)


def gross_pct_gdp(decades):
    """Gross funding by source as percent of GDP: net inflows only.

    Parameters
    ----------
    decades : pandas.DataFrame
        Decade totals of flows and GDP.

    Returns
    -------
    pandas.DataFrame
        One column per category.
    """
    names = [name for name, _ in CATEGORIES]
    return decades[names].clip(lower=0).div(decades["GDP"], axis=0) * 100


def gross_shares(decades):
    """Percent of gross funding by source; each decade sums to 100.

    Parameters
    ----------
    decades : pandas.DataFrame

    Returns
    -------
    pandas.DataFrame
    """
    gross = gross_pct_gdp(decades)
    return gross.div(gross.sum(axis=1), axis=0) * 100


# ── House style ──────────────────────────────────────────────────────────

def natural_sort_key(text):
    """Sort key that orders embedded numbers by magnitude (GS5 before GS10).

    Parameters
    ----------
    text : str

    Returns
    -------
    list
    """
    return [int(chunk) if chunk.isdigit() else chunk.lower()
            for chunk in re.split(r"(\d+)", text)]


def oxford_comma_join(items):
    """Join items as "A", "A and B", or "A, B, and C".

    Parameters
    ----------
    items : list of str

    Returns
    -------
    str
    """
    items = list(items)
    if len(items) <= 2:
        return " and ".join(items)
    return ", ".join(items[:-1]) + ", and " + items[-1]


def new_figure(width=12, height=6.5):
    """Create a figure and axes with the house font sizes.

    Parameters
    ----------
    width, height : float
        Inches.

    Returns
    -------
    tuple of (matplotlib.figure.Figure, matplotlib.axes.Axes)
    """
    plt.rcParams.update({
        "font.size": BASE_FONT_SIZE, "axes.labelsize": BASE_FONT_SIZE,
        "xtick.labelsize": BASE_FONT_SIZE, "ytick.labelsize": BASE_FONT_SIZE,
        "legend.fontsize": SMALL_FONT_SIZE,
    })
    return plt.subplots(figsize=(width, height))


def apply_house_style(ax):
    """Remove top and right spines; horizontal gridlines only.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
    """
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", color="0.85", linewidth=0.8)
    ax.grid(axis="x", visible=False)
    ax.set_axisbelow(True)


def add_bottom_legend(ax, handles, labels):
    """Frameless single-row legend below the axes, sorted alphabetically.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
    handles, labels : list
    """
    pairs = sorted(zip(labels, handles), key=lambda pair: pair[0].lower())
    ax.legend([h for _, h in pairs], [lab for lab, _ in pairs], loc="upper center",
              bbox_to_anchor=(0.5, LEGEND_Y), ncol=len(pairs), frameon=False,
              fontsize=SMALL_FONT_SIZE, handlelength=1.2, columnspacing=1.2)


def add_recession_bars(ax):
    """Shade NBER recessions on a date axis.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
    """
    x_min, x_max = ax.get_xlim()
    for start, end in NBER_RECESSIONS:
        x_start, x_end = mdates.datestr2num(start), mdates.datestr2num(end)
        if x_end >= x_min and x_start <= x_max:
            ax.axvspan(x_start, x_end, color="gray", alpha=0.2, linewidth=0, zorder=0)
    ax.set_xlim(x_min, x_max)


def add_sources_note(ax, text):
    """Left-justified sources line below the legend, in axes coordinates.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
    text : str
    """
    ax.text(0, SOURCES_Y, text, transform=ax.transAxes, ha="left", va="top",
            fontsize=SMALL_FONT_SIZE)


def save_figure(fig, name):
    """Save at 300 dpi, tightly cropped, and close.

    Parameters
    ----------
    fig : matplotlib.figure.Figure
    name : str
        File stem in the output folder.
    """
    path = OUT_DIR / f"{name}.png"
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  {path.name}")


def stack_bars(ax, values, items, width=0.8, edge_width=0.3, margin=0.7):
    """Draw stacked bars, positives upward from zero.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
    values : pandas.DataFrame
        One row per bar, one column per stacked item.
    items : list of (str, str)
        Column name and color, bottom to top.
    width : float
        Bar width.
    edge_width : float
        White separator line between stacked segments.
    margin : float
        Space between the outer bar centers and the axis ends.
    """
    positions = np.arange(len(values))
    bottom = np.zeros(len(values))
    for name, color in items:
        heights = values[name].to_numpy()
        ax.bar(positions, heights, bottom=bottom, width=width, color=color,
               edgecolor="white", linewidth=edge_width, zorder=2)
        bottom += heights
    ax.set_xticks(positions)
    ax.set_xticklabels(values.index)
    ax.set_xlim(-margin, len(values) - 1 + margin)


def legend_patches(items):
    """Legend handles for colored categories.

    Parameters
    ----------
    items : list of (str, str)

    Returns
    -------
    tuple of (list, list)
    """
    handles = [Patch(facecolor=color, label=name) for name, color in items]
    return handles, [h.get_label() for h in handles]


# ── Tables (LaTeX) ───────────────────────────────────────────────────────

def compile_table(tex, name):
    """Write a standalone LaTeX table and render it to PDF and PNG.

    Parameters
    ----------
    tex : str
        Complete standalone LaTeX document.
    name : str
        File stem in the output folder.
    """
    tex_path = OUT_DIR / f"{name}.tex"
    tex_path.write_text(tex)
    if not (shutil.which("pdflatex") and shutil.which("gs")):
        print(f"  {tex_path.name} (pdflatex or gs not found; PNG not rendered)")
        return
    subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", tex_path.name],
                   cwd=OUT_DIR, check=True, capture_output=True)
    subprocess.run(["gs", "-q", "-dSAFER", "-dBATCH", "-dNOPAUSE", "-sDEVICE=png16m", "-r300",
                    "-dTextAlphaBits=4", "-dGraphicsAlphaBits=4",
                    f"-sOutputFile={name}.png", f"{name}.pdf"],
                   cwd=OUT_DIR, check=True, capture_output=True)
    for extension in (".aux", ".log"):
        (OUT_DIR / f"{name}{extension}").unlink(missing_ok=True)
    print(f"  {name}.png")


TABLE_PREAMBLE = [
    r"\documentclass[border=8pt]{standalone}",
    r"\usepackage[scaled]{helvet}",
    r"\renewcommand{\familydefault}{\sfdefault}",
    r"\usepackage{booktabs}",
    r"\usepackage{xcolor}",
    r"\usepackage{threeparttable}",
    r"\begin{document}",
    r"\begin{threeparttable}",
]


def table_note(text):
    """Close a threeparttable with a tight, ragged-right note.

    Parameters
    ----------
    text : str

    Returns
    -------
    list of str
    """
    return [r"\begin{tablenotes}[flushleft]", r"\footnotesize\raggedright",
            rf"\item[]\hspace*{{-\labelsep}}{text}", r"\end{tablenotes}",
            r"\end{threeparttable}", r"\end{document}"]


# ── Figure 1 ─────────────────────────────────────────────────────────────

def figure1_bank_loans():
    """Bank loans: trillions of dollars (log, left) and percent of GDP (right), 1970-."""
    loans = load_sheet("Fig1_Loans_Monthly")
    gdp = load_sheet("Fig1_GDP_Quarterly", usecols="A:B")
    # The note rows below each table make the date column mixed; restore dates.
    loans = loans.set_index(pd.to_datetime(loans["Month"]))["LOANS ($ billions)"]
    gdp = gdp.set_index(pd.to_datetime(gdp["Quarter"]))["GDP ($ billions, SAAR)"]
    # Quarterly average of monthly loans over that quarter's GDP.
    share = (loans.resample("QS").mean() / gdp * 100).dropna()
    start = str(FIG1_FIRST_YEAR)
    level = loans.loc[start:] / 1000
    share = share.loc[start:]

    fig, ax = new_figure(width=12, height=6)
    ax.plot(level.index, level, color=BANK_COLOR, linewidth=1.6, label="Loans in levels")
    ax.set_yscale("log")
    ax.yaxis.set_major_locator(FixedLocator(FIG1_LOG_TICKS))
    ax.yaxis.set_minor_locator(NullLocator())
    ax.yaxis.set_major_formatter(StrMethodFormatter("{x:g}"))
    ax.set_ylabel("Trillions of dollars (log scale)")
    ax.set_xlim(level.index.min(), level.index.max())
    apply_house_style(ax)

    right = ax.twinx()  # second scale, so the right spine stays
    right.plot(share.index, share, color=OTHER_COLOR, linewidth=1.6, label="Loans as percent of GDP")
    right.set_ylabel("Percent of GDP")
    right.set_ylim(0, max(60, share.max() * 1.05))
    right.spines["top"].set_visible(False)

    add_recession_bars(ax)
    handles = ax.get_lines()[:1] + right.get_lines()
    add_bottom_legend(ax, handles, [line.get_label() for line in handles])
    ids = sorted(["LOANS", "GDP"], key=natural_sort_key)
    add_sources_note(ax, f"Sources: FRED series {oxford_comma_join(ids)}")
    save_figure(fig, "figure1_bank_loans")


# ── Table 1 ──────────────────────────────────────────────────────────────

def table1_bank_charters():
    """Institutions and loans by insurance, charter, and Fed membership, end-2025."""
    filers = load_sheet("Table1_FDIC_Filers")
    filers.columns = ["CERT", "NAME", "BKCLASS", "REGAGNT", "INSAGNT1", "LNLSGR", "ASSET"]
    filers["loans_bn"] = filers["LNLSGR"] / 1e6
    insured = filers[filers["BKCLASS"] != UNINSURED_CLASS]
    total_loans = insured["loans_bn"].sum()

    lines = TABLE_PREAMBLE + [
        r"\begin{tabular}{l l l l r r r}", r"\toprule",
        r" & Charter & Fed member & Regulator & Institutions & Loans (\$bn) & "
        r"Share of insured loans (\%) \\", r"\midrule",
    ]
    classified, group = 0, None
    for row_group, label, code, regulator, charter, member, agency in TABLE1_ROWS:
        mask = filers["BKCLASS"] == code
        if regulator is not None:
            mask &= filers["REGAGNT"] == regulator
        subset = filers[mask]
        classified += len(subset)
        if row_group != group:
            if group is not None:
                lines.append(r"\addlinespace")
            lines.append(rf"\multicolumn{{7}}{{l}}{{\textit{{{row_group}}}}} \\")
            group = row_group
        share = subset["loans_bn"].sum() / total_loans * 100
        lines.append(rf"\quad {label} & {charter} & {member} & {agency} & {len(subset):,} & "
                     rf"{subset['loans_bn'].sum():,.0f} & {share:.1f} \\")
    assert classified == len(insured), "Every insured filer must fall in exactly one row"
    uninsured = filers[filers["BKCLASS"] == UNINSURED_CLASS]
    lines += [
        r"\midrule",
        rf"\textbf{{All FDIC-insured institutions}} & & & & {len(insured):,} & "
        rf"{total_loans:,.0f} & 100.0 \\",
        r"\addlinespace",
        rf"Uninsured Call Report filers & & & & {len(uninsured):,} & "
        rf"{uninsured['loans_bn'].sum():,.0f} & \\",
        r"\bottomrule", r"\end{tabular}",
    ]
    lines += table_note(
        "Gross loans and leases, December 31, 2025. Regulator is the primary federal regulator. "
        "Credit unions (NCUA) and most uninsured U.S. branches of foreign banks do not file Call "
        "Reports and are not included. Source: FDIC BankFind Suite.")
    compile_table("\n".join(lines) + "\n", "table1_bank_charters")


# ── Figures 2-4 and Table 2 ──────────────────────────────────────────────

def figure2_bank_vs_other(decades):
    """Banks vs. all other sources, percent of gross funding, decade totals."""
    shares = gross_shares(decades)
    bank = shares["Bank loans"]
    lines = [("All other sources", OTHER_COLOR, 100 - bank), ("Bank loans", BANK_COLOR, bank)]

    fig, ax = new_figure(width=12, height=6.5)
    positions = np.arange(len(shares))
    for label, color, values in lines:
        ax.plot(positions, values.to_numpy(), color=color, linewidth=1.6, marker="o",
                markersize=6, label=label, zorder=2)
    ax.axhline(0, color="0.2", linewidth=0.8, zorder=1.5)
    ax.set_xticks(positions)
    ax.set_xticklabels(shares.index)
    ax.set_xlim(-0.5, len(shares) - 0.5)
    ax.set_ylabel("Percent of gross funding")
    apply_house_style(ax)
    handles = ax.get_lines()[:2]
    add_bottom_legend(ax, handles, [line.get_label() for line in handles])
    add_sources_note(ax, Z1_SOURCE)
    save_figure(fig, "figure2_bank_vs_other")


def figure3_funding_shares(decades):
    """Funding by source, percent of gross funding, decade totals."""
    shares = gross_shares(decades)
    fig, ax = new_figure(width=12, height=6.5)
    stack_bars(ax, shares, CATEGORIES)
    ax.axhline(0, color="0.2", linewidth=0.8, zorder=2.5)
    ax.set_ylabel("Percent of gross funding")
    ax.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
    apply_house_style(ax)
    add_bottom_legend(ax, *legend_patches(CATEGORIES))
    add_sources_note(ax, Z1_SOURCE)
    save_figure(fig, "figure3_funding_shares")


def figure4_funding_pct_gdp(decades):
    """Funding by source, percent of GDP (gross), decade totals."""
    gross = gross_pct_gdp(decades)
    fig, ax = new_figure(width=12, height=6.5)
    stack_bars(ax, gross, CATEGORIES)
    ax.axhline(0, color="0.2", linewidth=0.8, zorder=2.5)
    ax.set_ylabel("Percent of GDP")
    ax.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
    apply_house_style(ax)
    add_bottom_legend(ax, *legend_patches(CATEGORIES))
    add_sources_note(ax, Z1_SOURCE)
    save_figure(fig, "figure4_funding_pct_gdp")


def table2_funding_shares(decades):
    """Funding shares, 1960s vs. 2020-25, with the change in points."""
    periods = ["1960s", "2020–25"]
    shares = gross_shares(decades).loc[periods].T
    shares["Change"] = shares[periods[1]] - shares[periods[0]]

    def signed(value):
        rounded = round(value, 1)
        if rounded == 0:
            return "0.0"
        return f"{'+' if rounded > 0 else '$-$'}{abs(rounded):.1f}"

    lines = TABLE_PREAMBLE[:6] + [
        r"\newcommand{\key}[1]{\textcolor[HTML]{#1}{\rule{0.75em}{0.75em}}\hspace{0.5em}}",
    ] + TABLE_PREAMBLE[6:] + [
        r"\begin{tabular}{l r r r}", r"\toprule",
        r"Source of funds & 1960s & 2020--25 & Change (points) \\", r"\midrule",
    ]
    for name, color in CATEGORIES:
        row = shares.loc[name]
        label = "Equity (net issuance)" if name == "Equity" else name
        lines.append(rf"\key{{{color[1:].upper()}}}{label} & {row[periods[0]]:.1f} & "
                     rf"{row[periods[1]]:.1f} & {signed(row['Change'])} \\")
    lines += [
        r"\midrule",
        rf"\textbf{{Total}} & {shares[periods[0]].sum():.1f} & {shares[periods[1]].sum():.1f} & \\",
        r"\bottomrule", r"\end{tabular}",
    ]
    lines += table_note(
        "Percent of gross funding: funds raised by U.S. households, nonfinancial businesses, and "
        "state and local governments from sources that were net inflows over the period; decade "
        "totals. Source: Federal Reserve Financial Accounts of the United States (Z.1).")
    compile_table("\n".join(lines) + "\n", "table2_funding_shares")


# ── Figure 5 ─────────────────────────────────────────────────────────────

def figure5_hyperscaler_debt():
    """Debt plus finance leases of five hyperscalers and CoreWeave, 2019-2026Q2."""
    bars = load_sheet("Fig5_Hyperscalers", dtype={"Period": str}).set_index("Period")
    bars.columns = [column.replace(" ($ billions)", "") for column in bars.columns]
    bars = bars[[name for name, _ in FIRMS]]  # the Total column is recomputed below
    totals = bars.sum(axis=1)
    ymax = totals.max() * 1.12

    fig, ax = new_figure(width=12, height=6.5)
    stack_bars(ax, bars, FIRMS, width=0.7, edge_width=0.5, margin=0.6)
    for x, total in enumerate(totals):
        ax.text(x, total + ymax * 0.012, f"{total:,.0f}", ha="center", va="bottom",
                fontsize=SMALL_FONT_SIZE)
    ax.set_ylim(0, ymax)
    ax.set_ylabel("Billions of dollars")
    apply_house_style(ax)
    add_bottom_legend(ax, *legend_patches(FIRMS))
    add_sources_note(ax,
        "Source: SEC EDGAR company filings (10-K and 10-Q). Debt outstanding (bonds and loans\n"
        "including current portion) plus finance-lease liabilities at year end (Oracle: November)\n"
        "and at the latest quarter; operating leases excluded. CoreWeave public since 2025.")
    save_figure(fig, "figure5_hyperscaler_debt")


def main():
    """Build every figure and table in the post."""
    print(f"Reading {DATA_PATH.name}; writing to {OUT_DIR}")
    decades = decade_totals(load_us_annual())
    figure1_bank_loans()
    table1_bank_charters()
    figure2_bank_vs_other(decades)
    figure3_funding_shares(decades)
    table2_funding_shares(decades)
    figure4_funding_pct_gdp(decades)
    figure5_hyperscaler_debt()


if __name__ == "__main__":
    main()
