# Curated ETF universe — ticker, name, TER (annual decimal), currency, category
# Prices via yfinance use adjusted close (dividends included in total return)

ETF_UNIVERSE = [
    # ── Global / World ───────────────────────────────────────────────────────
    {"ticker": "IWDA.AS",  "name": "iShares Core MSCI World",          "ter": 0.0020, "currency": "USD", "category": "Global"},
    {"ticker": "VWRL.AS",  "name": "Vanguard FTSE All-World",           "ter": 0.0022, "currency": "USD", "category": "Global"},
    {"ticker": "XDWD.DE",  "name": "Xtrackers MSCI World Swap",         "ter": 0.0019, "currency": "USD", "category": "Global"},
    {"ticker": "XDEW.DE",  "name": "Xtrackers MSCI World Equal Weight", "ter": 0.0025, "currency": "USD", "category": "Global"},
    {"ticker": "SWRD.SW",  "name": "SPDR MSCI World",                   "ter": 0.0012, "currency": "USD", "category": "Global"},

    # ── US Broad Market ───────────────────────────────────────────────────────
    {"ticker": "CSPX.L",   "name": "iShares Core S&P 500 (LON)",        "ter": 0.0007, "currency": "USD", "category": "US Broad"},
    {"ticker": "VUSA.L",   "name": "Vanguard S&P 500 (LON)",             "ter": 0.0007, "currency": "USD", "category": "US Broad"},
    {"ticker": "SPY",      "name": "SPDR S&P 500",                       "ter": 0.0009, "currency": "USD", "category": "US Broad"},
    {"ticker": "VOO",      "name": "Vanguard S&P 500",                   "ter": 0.0003, "currency": "USD", "category": "US Broad"},
    {"ticker": "IVV",      "name": "iShares Core S&P 500",               "ter": 0.0003, "currency": "USD", "category": "US Broad"},
    {"ticker": "VTI",      "name": "Vanguard Total Stock Market",        "ter": 0.0003, "currency": "USD", "category": "US Broad"},

    # ── Nasdaq / Technology ───────────────────────────────────────────────────
    {"ticker": "EQQQ.DE",  "name": "Invesco NASDAQ-100 (EU)",            "ter": 0.0030, "currency": "USD", "category": "Nasdaq / Tech"},
    {"ticker": "QQQ",      "name": "Invesco QQQ NASDAQ-100",             "ter": 0.0020, "currency": "USD", "category": "Nasdaq / Tech"},
    {"ticker": "QDVE.DE",  "name": "iShares S&P 500 Info Tech (EU)",     "ter": 0.0025, "currency": "USD", "category": "Nasdaq / Tech"},
    {"ticker": "XLK",      "name": "Technology Select Sector SPDR",      "ter": 0.0010, "currency": "USD", "category": "Nasdaq / Tech"},

    # ── Europe ────────────────────────────────────────────────────────────────
    {"ticker": "VEUR.AS",  "name": "Vanguard FTSE Dev Europe",           "ter": 0.0012, "currency": "EUR", "category": "Europe"},
    {"ticker": "DXET.DE",  "name": "Xtrackers Euro Stoxx 50",            "ter": 0.0009, "currency": "EUR", "category": "Europe"},
    {"ticker": "MEUD.PA",  "name": "Lyxor Core MSCI EMU",                "ter": 0.0012, "currency": "EUR", "category": "Europe"},
    {"ticker": "IQQE.DE",  "name": "iShares Core MSCI EMU",              "ter": 0.0012, "currency": "EUR", "category": "Europe"},

    # ── Emerging Markets ──────────────────────────────────────────────────────
    {"ticker": "IEMA.L",   "name": "iShares MSCI EM (LON)",              "ter": 0.0018, "currency": "USD", "category": "Emerging Markets"},
    {"ticker": "IS3N.DE",  "name": "iShares Core MSCI EM IMI",           "ter": 0.0018, "currency": "USD", "category": "Emerging Markets"},
    {"ticker": "VWO",      "name": "Vanguard FTSE Emerging Markets",     "ter": 0.0008, "currency": "USD", "category": "Emerging Markets"},

    # ── Small Cap / Factor ────────────────────────────────────────────────────
    {"ticker": "IUSN.DE",  "name": "iShares MSCI World Small Cap",       "ter": 0.0035, "currency": "USD", "category": "Small Cap"},
    {"ticker": "ZPRV.DE",  "name": "SPDR MSCI USA Small Cap Value",      "ter": 0.0030, "currency": "USD", "category": "Small Cap"},

    # ── Bonds / Fixed Income ──────────────────────────────────────────────────
    {"ticker": "AGG",      "name": "iShares Core US Aggregate Bond",     "ter": 0.0003, "currency": "USD", "category": "Bonds"},
    {"ticker": "BND",      "name": "Vanguard Total Bond Market",         "ter": 0.0003, "currency": "USD", "category": "Bonds"},

    # ── Commodities / Gold ────────────────────────────────────────────────────
    {"ticker": "GLD",      "name": "SPDR Gold Shares",                   "ter": 0.0040, "currency": "USD", "category": "Commodities"},
    {"ticker": "IGLN.L",   "name": "iShares Physical Gold (LON)",        "ter": 0.0012, "currency": "USD", "category": "Commodities"},

    # ── Thematic ──────────────────────────────────────────────────────────────
    {"ticker": "IQQH.DE",  "name": "iShares Global Clean Energy",        "ter": 0.0065, "currency": "USD", "category": "Thematic"},
    {"ticker": "ARKK",     "name": "ARK Innovation",                     "ter": 0.0075, "currency": "USD", "category": "Thematic"},
]
