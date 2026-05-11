#!/usr/bin/env python3
"""
ETF Weekly Recap
Fetches performance for 5d / 3m / YTD / 1Y periods (dividends included via
adjusted close prices), adjusts for TER, and emails an HTML summary.

Required env vars:
  SMTP_HOST        e.g. smtp.gmail.com
  SMTP_PORT        e.g. 587
  SMTP_USER        sender address
  SMTP_PASS        SMTP password / app password
  EMAIL_RECIPIENT  recipient address (comma-separated for multiple)
"""

import os
import sys
import smtplib
import logging
from datetime import date, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import yfinance as yf
import pandas as pd

from etfs import ETF_UNIVERSE

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
TOP_N = 5          # winners to highlight per period
PERIODS = {
    "5 Days":    5,
    "3 Months":  91,
    "YTD":       None,   # handled separately
    "1 Year":    365,
}


# ── Data ──────────────────────────────────────────────────────────────────────

def _ytd_start() -> date:
    today = date.today()
    return date(today.year, 1, 1)


def fetch_returns(etf_list: list[dict]) -> pd.DataFrame:
    """Download adjusted-close history and compute period returns + simulated annual perf."""
    tickers = [e["ticker"] for e in etf_list]
    today = date.today()

    # Fetch 400 days so all periods are covered in one call
    start = today - timedelta(days=400)
    log.info("Downloading %d tickers from %s to %s …", len(tickers), start, today)

    raw = yf.download(
        tickers,
        start=start.isoformat(),
        end=(today + timedelta(days=1)).isoformat(),
        auto_adjust=True,          # adjusted close includes dividends
        progress=False,
        group_by="ticker",
        threads=True,
    )

    # Build a clean Close dataframe: columns = tickers
    if len(tickers) == 1:
        close = raw[["Close"]].rename(columns={"Close": tickers[0]})
    else:
        close = raw["Close"]

    close = close.dropna(how="all")

    results = []
    for etf in etf_list:
        ticker = etf["ticker"]
        ter = etf["ter"]          # annual cost as decimal (e.g. 0.002 = 0.20%)

        if ticker not in close.columns:
            log.warning("No data for %s — skipping", ticker)
            continue

        series = close[ticker].dropna()
        if len(series) < 6:
            log.warning("Insufficient data for %s — skipping", ticker)
            continue

        current_price = float(series.iloc[-1])
        row = {
            "Ticker": ticker,
            "Name": etf["name"],
            "TER (%)": round(ter * 100, 2),
            "Price": round(current_price, 2),
            "Currency": etf["currency"],
        }

        period_days = {
            "5 Days":   5,
            "3 Months": 91,
            "YTD":      (date.today() - _ytd_start()).days,
            "1 Year":   365,
        }

        for label, days in period_days.items():
            target_date = today - timedelta(days=days)
            # Pick closest available date on or before target
            subset = series[series.index.date <= target_date]
            if subset.empty:
                row[f"Return {label} (%)"] = None
                row[f"Sim Annual {label} (%)"] = None
                continue

            start_price = float(subset.iloc[-1])
            gross_return = (current_price / start_price) - 1.0

            # Annualise and subtract TER
            ann_factor = 365.0 / max(days, 1)
            annualized_gross = (1 + gross_return) ** ann_factor - 1
            sim_annual = annualized_gross - ter

            row[f"Return {label} (%)"] = round(gross_return * 100, 2)
            row[f"Sim Annual {label} (%)"] = round(sim_annual * 100, 2)

        results.append(row)

    return pd.DataFrame(results)


# ── Email ─────────────────────────────────────────────────────────────────────

_COLORS = {
    "header_bg":  "#1a1a2e",
    "header_fg":  "#e0e0e0",
    "gold":       "#f5c518",
    "silver":     "#c0c0c0",
    "bronze":     "#cd7f32",
    "pos":        "#27ae60",
    "neg":        "#e74c3c",
    "row_even":   "#f8f9fa",
    "row_odd":    "#ffffff",
    "border":     "#dee2e6",
    "text":       "#212529",
    "subtitle":   "#6c757d",
}

MEDAL = {0: "🥇", 1: "🥈", 2: "🥉"}


def _pct(val):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "N/A"
    color = _COLORS["pos"] if val >= 0 else _COLORS["neg"]
    sign = "+" if val >= 0 else ""
    return f'<span style="color:{color};font-weight:600">{sign}{val:.2f}%</span>'


def _build_winners_block(df: pd.DataFrame, period: str) -> str:
    col_ret = f"Return {period} (%)"
    col_sim = f"Sim Annual {period} (%)"
    if col_ret not in df.columns:
        return ""

    top = df.dropna(subset=[col_ret]).nlargest(TOP_N, col_ret).reset_index(drop=True)
    if top.empty:
        return ""

    rows_html = ""
    for i, r in top.iterrows():
        medal = MEDAL.get(i, "")
        bg = _COLORS["row_even"] if i % 2 == 0 else _COLORS["row_odd"]
        rows_html += f"""
        <tr style="background:{bg}">
          <td style="padding:8px 12px;font-size:18px">{medal}</td>
          <td style="padding:8px 12px;font-weight:600">{r['Ticker']}</td>
          <td style="padding:8px 12px;color:{_COLORS['subtitle']};font-size:13px">{r['Name']}</td>
          <td style="padding:8px 12px;text-align:right">{_pct(r[col_ret])}</td>
          <td style="padding:8px 12px;text-align:right">{_pct(r[col_sim])}</td>
          <td style="padding:8px 12px;text-align:right;color:{_COLORS['subtitle']}">{r['TER (%)']:.2f}%</td>
        </tr>"""

    return f"""
    <h3 style="margin:24px 0 8px;color:{_COLORS['header_bg']};border-bottom:2px solid {_COLORS['gold']};
               padding-bottom:4px">Best performers — {period}</h3>
    <table width="100%" cellspacing="0" cellpadding="0"
           style="border-collapse:collapse;border:1px solid {_COLORS['border']};border-radius:6px;overflow:hidden">
      <thead>
        <tr style="background:{_COLORS['header_bg']};color:{_COLORS['header_fg']}">
          <th style="padding:8px 12px;width:30px"></th>
          <th style="padding:8px 12px;text-align:left">Ticker</th>
          <th style="padding:8px 12px;text-align:left">Name</th>
          <th style="padding:8px 12px;text-align:right">Period Return</th>
          <th style="padding:8px 12px;text-align:right">Sim. Annual Net</th>
          <th style="padding:8px 12px;text-align:right">TER</th>
        </tr>
      </thead>
      <tbody>{rows_html}</tbody>
    </table>"""


def _build_full_table(df: pd.DataFrame) -> str:
    sort_col = "Sim Annual 1 Year (%)"
    if sort_col not in df.columns:
        sort_col = df.columns[-1]
    sorted_df = df.sort_values(sort_col, ascending=False, na_position="last").reset_index(drop=True)

    header_cells = "".join(
        f'<th style="padding:7px 10px;text-align:right;white-space:nowrap">{c}</th>'
        for c in ["Ticker", "Name", "TER", "5d", "3m", "YTD", "1Y", "Sim 1Y net"]
    )

    rows_html = ""
    for i, r in sorted_df.iterrows():
        bg = _COLORS["row_even"] if i % 2 == 0 else _COLORS["row_odd"]
        rows_html += f"""
        <tr style="background:{bg};font-size:12px">
          <td style="padding:6px 10px;font-weight:600">{r['Ticker']}</td>
          <td style="padding:6px 10px;color:{_COLORS['subtitle']}">{r['Name']}</td>
          <td style="padding:6px 10px;text-align:right">{r['TER (%)']:.2f}%</td>
          <td style="padding:6px 10px;text-align:right">{_pct(r.get('Return 5 Days (%)'))}</td>
          <td style="padding:6px 10px;text-align:right">{_pct(r.get('Return 3 Months (%)'))}</td>
          <td style="padding:6px 10px;text-align:right">{_pct(r.get('Return YTD (%)'))}</td>
          <td style="padding:6px 10px;text-align:right">{_pct(r.get('Return 1 Year (%)'))}</td>
          <td style="padding:6px 10px;text-align:right">{_pct(r.get('Sim Annual 1 Year (%)'))}</td>
        </tr>"""

    return f"""
    <h3 style="margin:32px 0 8px;color:{_COLORS['header_bg']};border-bottom:2px solid {_COLORS['border']};
               padding-bottom:4px">Full scorecard (sorted by Sim. 1Y net)</h3>
    <table width="100%" cellspacing="0" cellpadding="0"
           style="border-collapse:collapse;border:1px solid {_COLORS['border']};font-size:12px">
      <thead>
        <tr style="background:{_COLORS['header_bg']};color:{_COLORS['header_fg']}">
          {header_cells}
        </tr>
      </thead>
      <tbody>{rows_html}</tbody>
    </table>"""


def build_html(df: pd.DataFrame) -> str:
    today_str = date.today().strftime("%B %d, %Y")
    winners = "".join(_build_winners_block(df, p) for p in PERIODS)
    full_table = _build_full_table(df)

    note = (
        "<p style='font-size:11px;color:#aaa;margin-top:24px'>"
        "<b>Methodology:</b> Prices are dividend-adjusted (total return). "
        "\"Sim. Annual Net\" annualises the gross period return then subtracts the fund TER. "
        "Past performance is not indicative of future results. Not financial advice."
        "</p>"
    )

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
             color:{_COLORS['text']};background:#f4f4f4;padding:0;margin:0">
  <div style="max-width:860px;margin:0 auto;background:#fff;border-radius:8px;
              box-shadow:0 2px 12px rgba(0,0,0,.08);overflow:hidden">

    <!-- Header -->
    <div style="background:{_COLORS['header_bg']};padding:28px 32px">
      <h1 style="margin:0;color:{_COLORS['gold']};font-size:24px">ETF Weekly Recap</h1>
      <p style="margin:4px 0 0;color:{_COLORS['header_fg']};opacity:.7;font-size:14px">{today_str}</p>
    </div>

    <div style="padding:24px 32px">
      <p style="color:{_COLORS['subtitle']};font-size:14px;margin-top:0">
        Top {TOP_N} best-performing ETFs across 4 time windows, dividend-adjusted and net of fees.
      </p>
      {winners}
      <br>
      {full_table}
      {note}
    </div>
  </div>
</body>
</html>"""


# ── Mailer ────────────────────────────────────────────────────────────────────

def send_email(html: str) -> None:
    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", 587))
    user = os.environ["SMTP_USER"]
    password = os.environ["SMTP_PASS"]
    recipients = [r.strip() for r in os.environ["EMAIL_RECIPIENT"].split(",")]

    today_str = date.today().strftime("%Y-%m-%d")
    subject = f"ETF Weekly Recap — {today_str}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(html, "html"))

    log.info("Sending email to %s via %s:%d …", recipients, host, port)
    with smtplib.SMTP(host, port) as server:
        server.ehlo()
        server.starttls()
        server.login(user, password)
        server.sendmail(user, recipients, msg.as_string())
    log.info("Email sent.")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    df = fetch_returns(ETF_UNIVERSE)
    if df.empty:
        log.error("No ETF data retrieved — aborting.")
        sys.exit(1)

    html = build_html(df)

    # Dump HTML locally for inspection when running manually
    out_path = "/tmp/etf_recap.html"
    with open(out_path, "w") as f:
        f.write(html)
    log.info("HTML preview written to %s", out_path)

    send_email(html)


if __name__ == "__main__":
    main()
