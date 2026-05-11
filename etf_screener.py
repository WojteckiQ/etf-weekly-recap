#!/usr/bin/env python3
"""
ETF Weekly Performance Report — PDF edition
Generates a multi-page PDF report and emails it as an attachment.

Pages:
  1. Cover  — top-5 bar charts per period (5d / 3m / YTD / 1Y)
  2–N. Category pages — metrics table + grouped bar chart per ETF cluster
  N+1. Trend chart  — cumulative return (top-8 ETFs, 3-month window)
  N+2. Heatmap      — all ETFs × all periods, colour-coded

Required env vars:
  SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, EMAIL_RECIPIENT
"""

import io
import logging
import os
import smtplib
import sys
from datetime import date, timedelta
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
import pandas as pd
import yfinance as yf

from etfs import ETF_UNIVERSE

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── Theme ─────────────────────────────────────────────────────────────────────
NAVY   = "#1a1a2e"
GOLD   = "#f5c518"
GREEN  = "#27ae60"
RED    = "#e74c3c"
GRAY   = "#888888"
WHITE  = "#ffffff"
LIGHT  = "#f5f7fa"
BLUE4  = ["#4a90d9", "#e67e22", "#9b59b6", "#2ecc71"]   # 4 period colours

FIGSIZE = (16.5, 11.0)   # A4 landscape (inches)
DPI     = 150
TOP_N   = 5
BENCHMARK = "IWDA.AS"

PERIOD_DAYS   = {"5d": 5, "3m": 91, "YTD": None, "1Y": 365}
PERIOD_LABELS = {"5d": "5 Days", "3m": "3 Months", "YTD": "Year-to-Date", "1Y": "1 Year"}

CATEGORY_ORDER = [
    "Global", "US Broad", "Nasdaq / Tech", "Europe",
    "Emerging Markets", "Small Cap", "Bonds", "Commodities", "Thematic",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ytd_days() -> int:
    t = date.today()
    return (t - date(t.year, 1, 1)).days or 1


def _fv(val, fmt="+.1f", suffix="%") -> str:
    """Format a float value; returns '—' for None/NaN."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "—"
    return f"{val:{fmt}}{suffix}"


def _tc(val, higher_is_better=True) -> str:
    """Return GREEN/RED/GRAY text colour for a metric value."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return GRAY
    pos = val >= 0 if higher_is_better else val <= 0
    return GREEN if pos else RED


def _header(fig, title: str, subtitle: str = "") -> None:
    ax = fig.add_axes([0, 0.935, 1, 0.065])
    ax.set_facecolor(NAVY)
    ax.axis("off")
    ax.text(0.018, 0.5, title, color=GOLD, fontsize=15, fontweight="bold", va="center")
    if subtitle:
        ax.text(0.982, 0.5, subtitle, color="white", fontsize=10,
                ha="right", va="center", alpha=0.75)


# ── Data layer ────────────────────────────────────────────────────────────────

def fetch_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Download 400 days of adjusted-close history for every ETF.
    Returns
    -------
    metrics : DataFrame — one row per ETF with all computed metrics
    close   : DataFrame — daily adjusted close prices (date index, ticker columns)
    """
    tickers = [e["ticker"] for e in ETF_UNIVERSE]
    today   = date.today()
    start   = (today - timedelta(days=400)).isoformat()
    end     = (today + timedelta(days=1)).isoformat()

    log.info("Downloading %d tickers …", len(tickers))
    raw = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False)

    if isinstance(raw.columns, pd.MultiIndex):
        close = raw["Close"].copy() if "Close" in raw.columns.get_level_values(0) else pd.DataFrame()
    else:
        close = raw[["Close"]].rename(columns={"Close": tickers[0]}) if "Close" in raw.columns else pd.DataFrame()

    if close.empty:
        log.error("yfinance returned no Close data.")
        return pd.DataFrame(), pd.DataFrame()

    close = close.dropna(how="all")

    # Benchmark daily returns for beta computation
    bm_ret = close[BENCHMARK].pct_change().dropna() if BENCHMARK in close.columns else None

    rows = []
    for etf in ETF_UNIVERSE:
        t = etf["ticker"]
        if t not in close.columns:
            log.warning("No data for %s — skipping", t)
            continue
        s = close[t].dropna()
        if len(s) < 10:
            continue

        cur = float(s.iloc[-1])
        row: dict = {
            "Ticker":   t,
            "Name":     etf["name"],
            "Category": etf["category"],
            "TER":      etf["ter"],
            "Price":    cur,
        }

        # Period returns & simulated annual net return
        for key, days in PERIOD_DAYS.items():
            if days is None:
                days = _ytd_days()
            target = today - timedelta(days=days)
            sub = s[s.index.date <= target]
            if sub.empty:
                row[f"ret_{key}"] = np.nan
                row[f"sim_{key}"] = np.nan
                continue
            gross  = cur / float(sub.iloc[-1]) - 1
            annual = (1 + gross) ** (365.0 / days) - 1
            row[f"ret_{key}"] = gross  * 100
            row[f"sim_{key}"] = (annual - etf["ter"]) * 100

        # Annualised volatility (daily σ × √252)
        daily = s.pct_change().dropna()
        row["vol"] = float(daily.std() * np.sqrt(252) * 100)

        # Max drawdown over the last year
        s1y = s[s.index >= pd.Timestamp(today - timedelta(days=365))]
        if len(s1y) > 1:
            roll_max = s1y.cummax()
            row["max_dd"] = float(((s1y - roll_max) / roll_max).min() * 100)
        else:
            row["max_dd"] = np.nan

        # Beta vs benchmark
        if bm_ret is not None and t != BENCHMARK:
            aligned = pd.concat([daily, bm_ret], axis=1).dropna()
            aligned.columns = ["etf", "bm"]
            if len(aligned) >= 20:
                cov = np.cov(aligned["etf"], aligned["bm"])
                row["beta"] = float(cov[0, 1] / cov[1, 1])
            else:
                row["beta"] = np.nan
        else:
            row["beta"] = 1.0 if t == BENCHMARK else np.nan

        # 52-week range position (0 = at 52w low, 100 = at 52w high)
        s52 = s[s.index >= pd.Timestamp(today - timedelta(days=365))]
        if len(s52) > 1:
            lo, hi = float(s52.min()), float(s52.max())
            row["range_pct"] = (cur - lo) / (hi - lo) * 100 if hi > lo else 50.0
        else:
            row["range_pct"] = np.nan

        rows.append(row)

    return pd.DataFrame(rows), close


# ── PDF pages ─────────────────────────────────────────────────────────────────

def page_cover(pdf: PdfPages, df: pd.DataFrame) -> None:
    """Page 1: Top-N horizontal bar charts, one per period (2×2 grid)."""
    fig = plt.figure(figsize=FIGSIZE, facecolor=LIGHT)
    _header(fig, "ETF Weekly Performance Report", date.today().strftime("%B %d, %Y"))

    positions = [
        [0.04, 0.49, 0.44, 0.42],   # 5d   — top-left
        [0.53, 0.49, 0.44, 0.42],   # 3m   — top-right
        [0.04, 0.05, 0.44, 0.42],   # YTD  — bottom-left
        [0.53, 0.05, 0.44, 0.42],   # 1Y   — bottom-right
    ]

    for pos, key in zip(positions, ["5d", "3m", "YTD", "1Y"]):
        col = f"ret_{key}"
        if col not in df.columns:
            continue
        top = df.dropna(subset=[col]).nlargest(TOP_N, col).reset_index(drop=True)
        if top.empty:
            continue

        ax = fig.add_axes(pos)
        ax.set_facecolor(WHITE)

        colours = [GREEN if v >= 0 else RED for v in top[col]]
        bars = ax.barh(top["Ticker"], top[col], color=colours, height=0.55, zorder=2)
        ax.axvline(0, color=GRAY, lw=0.8, zorder=3)

        for bar, v in zip(bars, top[col]):
            pad = 0.08
            ha  = "left" if v >= 0 else "right"
            ax.text(v + (pad if v >= 0 else -pad), bar.get_y() + bar.get_height() / 2,
                    f"{v:+.2f}%", va="center", ha=ha, fontsize=8.5,
                    fontweight="bold", color=GREEN if v >= 0 else RED)

        ax.set_title(f"Best {TOP_N} — {PERIOD_LABELS[key]}",
                     fontweight="bold", color=NAVY, fontsize=11, pad=6)
        ax.tick_params(axis="both", labelsize=9)
        ax.spines[["top", "right"]].set_visible(False)
        ax.set_xlabel("Total Return (%)", fontsize=8, color=GRAY)
        ax.grid(axis="x", alpha=0.25, zorder=1)

    fig.text(0.5, 0.016,
             "Returns are dividend-adjusted (total return via adjusted close). "
             "Sim. Annual Net subtracts the fund TER. Past performance is not indicative of future results. Not financial advice.",
             ha="center", fontsize=7.5, color=GRAY)

    pdf.savefig(fig, dpi=DPI, bbox_inches="tight")
    plt.close(fig)


def page_category(pdf: PdfPages, category: str, cat_df: pd.DataFrame, close: pd.DataFrame) -> None:
    """One page per category: metrics table (top) + grouped bar chart (bottom)."""
    cat_df = cat_df.sort_values("ret_1Y", ascending=False, na_position="last").copy()
    n = len(cat_df)

    fig = plt.figure(figsize=FIGSIZE, facecolor=LIGHT)
    _header(fig, f"Category — {category}", date.today().strftime("%B %d, %Y"))

    # ── Table ─────────────────────────────────────────────────────────────────
    ax_tbl = fig.add_axes([0.01, 0.37, 0.98, 0.55])
    ax_tbl.axis("off")

    COLS = ["Ticker", "Name", "TER %", "5d %", "3m %", "YTD %", "1Y %",
            "Sim 1Y %", "Vol %", "MaxDD %", "Beta", "52wk Pos"]

    cell_text   = []
    cell_bg     = []
    text_colors = []

    for i, (_, r) in enumerate(cat_df.iterrows()):
        v5d   = r.get("ret_5d");   v3m  = r.get("ret_3m")
        vYTD  = r.get("ret_YTD"); v1Y  = r.get("ret_1Y")
        vsim  = r.get("sim_1Y");  vvol = r.get("vol")
        vdd   = r.get("max_dd");  vbet = r.get("beta")
        vrng  = r.get("range_pct")

        row_vals = [
            r["Ticker"],
            r["Name"][:32],
            f"{r['TER']*100:.2f}",
            _fv(v5d),  _fv(v3m), _fv(vYTD), _fv(v1Y),
            _fv(vsim),
            _fv(vvol, ".1f"),
            _fv(vdd),
            _fv(vbet, ".2f", ""),
            _fv(vrng, ".0f"),
        ]
        cell_text.append(row_vals)

        bg = "#eef2f7" if i % 2 == 0 else WHITE
        cell_bg.append([bg] * len(COLS))

        text_colors.append([
            NAVY, "#333333", GRAY,
            _tc(v5d), _tc(v3m), _tc(vYTD), _tc(v1Y),
            _tc(vsim),
            GRAY,
            _tc(vdd, higher_is_better=False),
            GRAY, GRAY,
        ])

    tbl = ax_tbl.table(
        cellText=cell_text,
        colLabels=COLS,
        cellColours=cell_bg,
        loc="upper center",
        cellLoc="center",
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(8.5)
    tbl.scale(1, max(1.6, 9.5 / (n + 1)))

    for j in range(len(COLS)):
        hdr = tbl[(0, j)]
        hdr.set_facecolor(NAVY)
        hdr.get_text().set_color("white")
        hdr.get_text().set_fontweight("bold")

    for i, tc_row in enumerate(text_colors):
        for j, color in enumerate(tc_row):
            tbl[(i + 1, j)].get_text().set_color(color)
        tbl[(i + 1, 7)].get_text().set_fontweight("bold")   # Sim 1Y bold

    # ── Bar chart ─────────────────────────────────────────────────────────────
    ax_bar = fig.add_axes([0.05, 0.05, 0.90, 0.29])
    ax_bar.set_facecolor(WHITE)

    tickers = cat_df["Ticker"].tolist()
    x = np.arange(len(tickers))
    w = 0.18

    for j, (pkey, colour) in enumerate(zip(["5d", "3m", "YTD", "1Y"], BLUE4)):
        col = f"ret_{pkey}"
        vals = []
        for t in tickers:
            mask = cat_df["Ticker"] == t
            v = cat_df.loc[mask, col].values[0] if col in cat_df.columns and mask.any() else np.nan
            vals.append(0.0 if np.isnan(v) else v)
        ax_bar.bar(x + (j - 1.5) * w, vals, width=w,
                   label=PERIOD_LABELS[pkey], color=colour, alpha=0.85, zorder=2)

    ax_bar.axhline(0, color=GRAY, lw=0.8, zorder=3)
    ax_bar.set_xticks(x)
    ax_bar.set_xticklabels(tickers, fontsize=9, fontweight="bold")
    ax_bar.set_ylabel("Return (%)", fontsize=9)
    ax_bar.legend(fontsize=8.5, framealpha=0.5, ncol=4, loc="best")
    ax_bar.spines[["top", "right"]].set_visible(False)
    ax_bar.grid(axis="y", alpha=0.25, zorder=1)
    ax_bar.set_title("Returns by Period (dividend-adjusted total return)",
                     fontweight="bold", color=NAVY, fontsize=10)

    pdf.savefig(fig, dpi=DPI, bbox_inches="tight")
    plt.close(fig)


def page_trend(pdf: PdfPages, df: pd.DataFrame, close: pd.DataFrame) -> None:
    """Normalized cumulative-return chart for top-8 ETFs (3-month window)."""
    fig = plt.figure(figsize=FIGSIZE, facecolor=LIGHT)
    _header(fig, "Cumulative Performance — Top 8 ETFs (3-Month Window)",
            date.today().strftime("%B %d, %Y"))

    ax = fig.add_axes([0.06, 0.10, 0.91, 0.80])
    ax.set_facecolor(WHITE)

    top8    = df.dropna(subset=["ret_1Y"]).nlargest(8, "ret_1Y")
    cutoff  = pd.Timestamp(date.today() - timedelta(days=91))
    cmap    = plt.get_cmap("tab10")

    for i, (_, row) in enumerate(top8.iterrows()):
        t = row["Ticker"]
        if t not in close.columns:
            continue
        s = close[t].dropna()
        s = s[s.index >= cutoff]
        if s.empty:
            continue
        rebased = s / float(s.iloc[0]) * 100
        label   = f"{t}  {_fv(row['ret_1Y'])} 1Y"
        ax.plot(rebased.index, rebased.values, lw=2.2, color=cmap(i), label=label)
        # Annotate last value
        ax.annotate(f"{float(rebased.iloc[-1]):.1f}",
                    xy=(rebased.index[-1], float(rebased.iloc[-1])),
                    xytext=(6, 0), textcoords="offset points",
                    fontsize=8, color=cmap(i), va="center")

    ax.axhline(100, color=GRAY, lw=0.9, ls="--", alpha=0.7, label="Base (100)")
    ax.set_ylabel("Indexed Price (100 = window start)", fontsize=10)
    ax.set_xlabel("Date", fontsize=10)
    ax.legend(fontsize=8.5, loc="upper left", framealpha=0.6, ncol=2)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.3)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0f}"))

    fig.text(0.5, 0.025,
             "Prices dividend-adjusted. Rebased to 100 at the start of the 3-month window. "
             "Selection = top 8 ETFs by 1-year total return.",
             ha="center", fontsize=8, color=GRAY)

    pdf.savefig(fig, dpi=DPI, bbox_inches="tight")
    plt.close(fig)


def page_heatmap(pdf: PdfPages, df: pd.DataFrame) -> None:
    """Full performance heatmap — all ETFs × all periods, grouped by category."""
    HCOLS      = ["5d", "3m", "YTD", "1Y", "Sim 1Y net"]
    DATA_COLS  = ["ret_5d", "ret_3m", "ret_YTD", "ret_1Y", "sim_1Y"]

    # Build ordered list: sort by category then 1Y desc
    ordered = []
    for cat in CATEGORY_ORDER:
        sub = df[df["Category"] == cat].sort_values("ret_1Y", ascending=False, na_position="last")
        ordered.append(sub)
    plot_df = pd.concat(ordered, ignore_index=True)

    matrix  = plot_df[DATA_COLS].values.astype(float)
    ylabels = [f"{r['Ticker']}  ({r['Category'][:5]})" for _, r in plot_df.iterrows()]

    fig = plt.figure(figsize=FIGSIZE, facecolor=LIGHT)
    _header(fig, "Performance Heatmap — All ETFs × All Periods",
            date.today().strftime("%B %d, %Y"))

    ax = fig.add_axes([0.14, 0.06, 0.74, 0.86])

    vmax = np.nanpercentile(np.abs(matrix), 95)
    im   = ax.imshow(matrix, aspect="auto", cmap="RdYlGn", vmin=-vmax, vmax=vmax, interpolation="nearest")

    # Cell text
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            val = matrix[i, j]
            if np.isnan(val):
                continue
            bright = abs(val) > vmax * 0.55
            ax.text(j, i, f"{val:+.1f}%", ha="center", va="center",
                    fontsize=7.5, fontweight="bold",
                    color="white" if bright else "#222222")

    # Category separator lines
    count = 0
    for cat in CATEGORY_ORDER:
        count += len(plot_df[plot_df["Category"] == cat])
        if count < len(plot_df):
            ax.axhline(count - 0.5, color="white", lw=2)

    ax.set_xticks(range(len(HCOLS)))
    ax.set_xticklabels(HCOLS, fontweight="bold", fontsize=10)
    ax.set_yticks(range(len(ylabels)))
    ax.set_yticklabels(ylabels, fontsize=7.5)
    ax.xaxis.set_ticks_position("top")
    ax.xaxis.set_label_position("top")

    cbar = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.015)
    cbar.set_label("Return (%)", fontsize=9)

    # Category labels on right side
    ax_right = ax.twinx()
    ax_right.set_ylim(ax.get_ylim())
    cat_ticks, cat_labels = [], []
    count = 0
    for cat in CATEGORY_ORDER:
        n = len(plot_df[plot_df["Category"] == cat])
        if n:
            cat_ticks.append(count + n / 2 - 0.5)
            cat_labels.append(cat)
            count += n
    ax_right.set_yticks(cat_ticks)
    ax_right.set_yticklabels(cat_labels, fontsize=8, fontweight="bold", color=NAVY)
    ax_right.tick_params(length=0)

    pdf.savefig(fig, dpi=DPI, bbox_inches="tight")
    plt.close(fig)


# ── PDF builder ───────────────────────────────────────────────────────────────

def generate_pdf(df: pd.DataFrame, close: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with PdfPages(buf) as pdf:
        d = pdf.infodict()
        d["Title"]   = f"ETF Weekly Report — {date.today()}"
        d["Author"]  = "ETF Screener"
        d["Subject"] = "Weekly ETF Performance"

        page_cover(pdf, df)

        for cat in CATEGORY_ORDER:
            cat_df = df[df["Category"] == cat].copy()
            if not cat_df.empty:
                page_category(pdf, cat, cat_df, close)

        page_trend(pdf, df, close)
        page_heatmap(pdf, df)

    return buf.getvalue()


# ── Mailer ────────────────────────────────────────────────────────────────────

def send_email(pdf_bytes: bytes) -> None:
    host       = os.environ["SMTP_HOST"]
    port       = int(os.environ.get("SMTP_PORT", 587))
    user       = os.environ["SMTP_USER"]
    password   = os.environ["SMTP_PASS"]
    recipients = [r.strip() for r in os.environ["EMAIL_RECIPIENT"].split(",")]

    today_str = date.today().strftime("%Y-%m-%d")
    subject   = f"ETF Weekly Report — {today_str}"

    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"]    = user
    msg["To"]      = ", ".join(recipients)

    html_intro = f"""
    <html><body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#333">
      <div style="max-width:600px;margin:0 auto">
        <div style="background:#1a1a2e;padding:20px 24px;border-radius:8px 8px 0 0">
          <h2 style="margin:0;color:#f5c518">ETF Weekly Performance Report</h2>
          <p style="margin:4px 0 0;color:#fff;opacity:.7;font-size:13px">{date.today().strftime('%B %d, %Y')}</p>
        </div>
        <div style="background:#f5f7fa;padding:20px 24px;border-radius:0 0 8px 8px">
          <p>Your weekly ETF recap is attached as a PDF. It includes:</p>
          <ul>
            <li><b>Cover page</b> — top-{TOP_N} performers per period (5d / 3m / YTD / 1Y)</li>
            <li><b>Category pages</b> — table with returns, volatility, beta, max drawdown, 52-week range + bar chart</li>
            <li><b>Trend chart</b> — cumulative performance of top-8 ETFs over the last 3 months</li>
            <li><b>Heatmap</b> — all ETFs × all periods, colour-coded and grouped by category</li>
          </ul>
          <p style="font-size:12px;color:#888;margin-top:16px">
            Returns are dividend-adjusted. Simulated annual net subtracts the fund TER.
            Past performance is not indicative of future results. Not financial advice.
          </p>
        </div>
      </div>
    </body></html>"""

    msg.attach(MIMEText(html_intro, "html"))

    att = MIMEApplication(pdf_bytes, _subtype="pdf")
    att.add_header("Content-Disposition", "attachment",
                   filename=f"etf_report_{today_str}.pdf")
    msg.attach(att)

    log.info("Sending to %s via %s:%d …", recipients, host, port)
    with smtplib.SMTP(host, port) as server:
        server.ehlo()
        server.starttls()
        server.login(user, password)
        server.sendmail(user, recipients, msg.as_string())
    log.info("Email sent.")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    df, close = fetch_data()
    if df.empty:
        log.error("No data retrieved — aborting.")
        sys.exit(1)

    pdf_bytes = generate_pdf(df, close)

    out = "/tmp/etf_report.pdf"
    with open(out, "wb") as f:
        f.write(pdf_bytes)
    log.info("PDF written to %s (%d KB)", out, len(pdf_bytes) // 1024)

    send_email(pdf_bytes)


if __name__ == "__main__":
    main()
