# Curated ETF universe with name, ticker and TER (Total Expense Ratio, annual %)
# Prices fetched via yfinance use adjusted close (dividends already included)

ETF_UNIVERSE = [
    # === Global / World ===
    {"ticker": "IWDA.AS",  "name": "iShares Core MSCI World",          "ter": 0.0020, "currency": "USD"},
    {"ticker": "VWRL.AS",  "name": "Vanguard FTSE All-World",           "ter": 0.0022, "currency": "USD"},
    {"ticker": "XDWD.DE",  "name": "Xtrackers MSCI World Swap",         "ter": 0.0019, "currency": "USD"},
    {"ticker": "XDEW.DE",  "name": "Xtrackers MSCI World Equal Weight", "ter": 0.0025, "currency": "USD"},
    {"ticker": "SWRD.SW",  "name": "SPDR MSCI World",                   "ter": 0.0012, "currency": "USD"},

    # === S&P 500 / US ===
    {"ticker": "CSPX.L",  "name": "iShares Core S&P 500 (LON)",        "ter": 0.0007, "currency": "USD"},
    {"ticker": "VUSA.L",  "name": "Vanguard S&P 500 (LON)",             "ter": 0.0007, "currency": "USD"},
    {"ticker": "SPY",     "name": "SPDR S&P 500",                       "ter": 0.0009, "currency": "USD"},
    {"ticker": "VOO",     "name": "Vanguard S&P 500",                   "ter": 0.0003, "currency": "USD"},
    {"ticker": "IVV",     "name": "iShares Core S&P 500",               "ter": 0.0003, "currency": "USD"},
    {"ticker": "VTI",     "name": "Vanguard Total Stock Market",        "ter": 0.0003, "currency": "USD"},

    # === Nasdaq / Tech ===
    {"ticker": "EQQQ.DE", "name": "Invesco NASDAQ-100 (EU)",            "ter": 0.0030, "currency": "USD"},
    {"ticker": "QQQ",     "name": "Invesco QQQ NASDAQ-100",             "ter": 0.0020, "currency": "USD"},
    {"ticker": "QDVE.DE", "name": "iShares S&P 500 Info Tech",          "ter": 0.0025, "currency": "USD"},
    {"ticker": "XLK",     "name": "Technology Select Sector SPDR",      "ter": 0.0010, "currency": "USD"},

    # === Europe ===
    {"ticker": "VEUR.AS", "name": "Vanguard FTSE Dev Europe",           "ter": 0.0012, "currency": "EUR"},
    {"ticker": "DXET.DE", "name": "Xtrackers Euro Stoxx 50",            "ter": 0.0009, "currency": "EUR"},
    {"ticker": "MEUD.PA", "name": "Lyxor Core MSCI EMU",                "ter": 0.0012, "currency": "EUR"},
    {"ticker": "SMEA.PA", "name": "iShares Core MSCI EMU",              "ter": 0.0012, "currency": "EUR"},

    # === Emerging Markets ===
    {"ticker": "IEMA.L",  "name": "iShares MSCI EM (LON)",              "ter": 0.0018, "currency": "USD"},
    {"ticker": "IS3N.DE", "name": "iShares Core MSCI EM IMI",           "ter": 0.0018, "currency": "USD"},
    {"ticker": "VWO",     "name": "Vanguard FTSE Emerging Markets",     "ter": 0.0008, "currency": "USD"},

    # === Small Cap / Factor ===
    {"ticker": "IUSN.DE", "name": "iShares MSCI World Small Cap",       "ter": 0.0035, "currency": "USD"},
    {"ticker": "ZPRV.DE", "name": "SPDR MSCI USA Small Cap Value",      "ter": 0.0030, "currency": "USD"},

    # === Bonds ===
    {"ticker": "AGG",     "name": "iShares Core US Aggregate Bond",     "ter": 0.0003, "currency": "USD"},
    {"ticker": "BND",     "name": "Vanguard Total Bond Market",         "ter": 0.0003, "currency": "USD"},

    # === Commodities / Gold ===
    {"ticker": "GLD",     "name": "SPDR Gold Shares",                   "ter": 0.0040, "currency": "USD"},
    {"ticker": "IGLN.L",  "name": "iShares Physical Gold (LON)",        "ter": 0.0012, "currency": "USD"},

    # === Thematic ===
    {"ticker": "IQQH.DE", "name": "iShares Global Clean Energy",        "ter": 0.0065, "currency": "USD"},
    {"ticker": "ARKK",    "name": "ARK Innovation",                     "ter": 0.0075, "currency": "USD"},
]
