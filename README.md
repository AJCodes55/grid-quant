# GridQuant: Probabilistic ERCOT Price Forecasting for Battery Storage Optimization

Battery storage operators in ERCOT leave millions on the table by following naive time-of-use charge/discharge schedules. This system uses probabilistic price forecasting to optimize battery dispatch decisions — capturing **$235,674 in simulated revenue over 6 months, 3.9x more than a naive benchmark strategy**.

Electricity price forecasting in ERCOT presents two core technical challenges: quantifying price uncertainty and optimizing dispatch decisions across time. To address the first, I used **Quantile Regression Forests** — rather than outputting a single average price, QRF produces a full probability distribution, allowing the operator to make risk-aware charge/discharge decisions. To address the second, I used **Dynamic Programming**, which finds the optimal sequence of buy/sell/hold decisions by accounting for future price opportunities and battery state of charge constraints simultaneously.

---

## Live Dashboard
[GridQuant Tableau Dashboard](https://public.tableau.com/app/profile/ashutosh.jaiswal7472/viz/GridQuantBatteryStorageOptimizationDashboard/GridQuantBatteryStorageOptimizationDashboard)

---

## Project Architecture

```
Raw Data → EDA → Feature Engineering → QRF Model → Battery Dispatch Optimizer → Backtest → Business Outcome
```

**Client:** Battery storage operator in ERCOT's HB_NORTH hub  
**Problem:** Maximize revenue from charge/discharge arbitrage using short-term price forecasts  
**Result:** 3.9x revenue outperformance vs naive time-of-use strategy over 6-month backtest  

---

## Repository Structure

```
GridQuant/
│
├── data/
│   ├── raw/                  # Parquet files from ERCOT and NOAA APIs
│   └── processed/            # Feature-engineered dataset and backtest results
│
├── src/
│   ├── ingestion/
│   │   ├── ercot_client.py   # Reusable ERCOT API client (OAuth, pagination, retry)
│   │   ├── price_fetcher.py  # 27 months of 15-min settlement prices
│   │   ├── load_fetcher.py   # 27 months of hourly system load
│   │   └── noaa_client.py    # 27 months of Dallas/DFW weather data
│   └── optimization/
│       └── battery.py        # Battery dispatch and strategy functions
│
├── notebooks/
│   └── 01_EDA.ipynb          # EDA, feature engineering, modeling, backtesting
│
├── models/
│   └── qrf_model.joblib      # Trained QRF model
│
├── tests/
│   └── test_dispatch.py      # Pytest test suite for battery dispatch logic
│
├── dashboard/                # Tableau workbook
└── README.md
```

---

## Data Pipeline

Three data sources, all fetched programmatically via authenticated APIs:

| Source | Dataset | Granularity | Period |
|--------|---------|-------------|--------|
| ERCOT API | Settlement Point Prices (HB_NORTH) | 15-minute | Jan 2024 – Mar 2026 |
| ERCOT API | Actual System Load by Weather Zone | Hourly | Jan 2024 – Mar 2026 |
| NOAA CDO API | DFW Airport Weather Station | Daily | Jan 2024 – Mar 2026 |

**Engineering highlights:**
- OAuth 2.0 authentication with automatic token refresh (55-minute refresh cycle)
- Offset and page-based pagination handling for both APIs
- Idempotent monthly fetching with 429/503 retry logic
- Parquet storage with cross-platform path handling

---

## Feature Engineering

20 features engineered across four categories:

**Load signals** — north zone load, total ERCOT load  
**Weather signals** — wind speed, precipitation, temperature range, average temperature, comfort deviation (|temp - 18°C|)  
**Cyclical time encoding** — hour sin/cos, month sin/cos, day-of-week sin/cos  
**Price history** — lag features at 1h, 3h, 24h, 48h, 168h + rolling averages at 3h and 24h  

Key insight: raw temperature has weak linear correlation with price due to both summer cooling and winter heating demand. `comfort_deviation = |temp_avg - 18|` captures the U-shaped relationship and outperforms raw temperature as a feature.

---

## Model: Quantile Regression Forest

Standard regression models fail for electricity prices because the distribution has extreme fat tails — most hours are $20-50/MWh but occasional spikes reach $2,700+. A point forecast optimizes for average error and completely misses the spikes where all the money is.

QRF outputs a full probability distribution at each timestep:
- **Q10** — 10th percentile: downside risk estimate
- **Q50** — median forecast: expected price
- **Q90** — 90th percentile: upside potential signal

**Hyperparameters:** 300 estimators, max_depth=15, min_samples_leaf=20, max_features=sqrt

**Evaluation on holdout test set (Oct 2025 – Mar 2026):**
| Metric | Value |
|--------|-------|
| 80% Interval Coverage | 89.88% |
| Pinball Loss Q10 | 1.878 |
| Pinball Loss Q50 | 5.039 |
| Pinball Loss Q90 | 2.643 |
| RMSE (median) | $42.68/MWh |

**Train/test split:** Chronological 78/22 split — model trained on Jan 2024 – Sep 2025, tested on Oct 2025 – Mar 2026. No shuffling to prevent data leakage.

---

## Battery Dispatch Optimizer

**Battery specifications:**
- Capacity: 100 MWh
- Max charge/discharge rate: 25 MW/hour
- Round-trip efficiency: 85%
- SOC bounds: 10% – 90% (battery health protection)

**Naive strategy:** Fixed schedule — charge midnight to 6 AM, discharge 5 PM to 10 PM. No forecasting.

**Smart strategy:** Dynamic thresholds using QRF output —
- Charge when current price < 30th percentile of recent prices AND Q90 forecast significantly higher (upside > $10)
- Discharge when current price > 70th percentile of recent prices
- Idle otherwise

The Q90 signal is the key differentiator — it tells the operator whether a profitable discharge window is coming, preventing premature discharge.

---

## Backtesting Results

Simulated over 4,368 test hours (Oct 2025 – Mar 2026):

| Strategy | Total Revenue |
|----------|--------------|
| Naive (time-of-use) | $60,449 |
| Smart (QRF-powered) | $235,674 |
| **Outperformance** | **3.9x** |

**Caveats:** Results based on idealized backtesting assumptions — no transaction costs, perfect price execution, no battery degradation costs. Real-world performance would be lower but the directional advantage is robust.

---

## Testing

```bash
pip install pytest
pytest tests/test_dispatch.py -v
```

7 tests covering battery dispatch logic — charge constraints, discharge constraints, capacity bounds, efficiency losses, and idle behavior.

---

## Setup & Reproduction

```bash
git clone https://github.com/AJCodes55/GridQuant
cd GridQuant
pip install -r requirements.txt
```

Create `.env` file:
```
ERCOT_API_KEY=your_key
ERCOT_USERNAME=your_email
ERCOT_PASSWORD=your_password
ERCOT_CLIENT_ID=your_client_id
NOAA_TOKEN=your_token
```

Register for free API access:
- ERCOT: [developer.ercot.com](https://developer.ercot.com)
- NOAA: [ncdc.noaa.gov/cdo-web/token](https://www.ncdc.noaa.gov/cdo-web/token)

Run data pipeline:
```bash
python src/ingestion/price_fetcher.py
python src/ingestion/load_fetcher.py
python src/ingestion/noaa_client.py
```

Then run `notebooks/01_EDA.ipynb` end to end.

---

## Tech Stack

Python, Pandas, NumPy, Scikit-learn, quantile-forest, Matplotlib, Seaborn, Requests, python-dotenv, joblib, pytest, Tableau Public, Parquet

---

## Author

**Ashutosh Jaiswal**  
MS Information Science, UT Austin  
[GitHub](https://github.com/AJCodes55) | [LinkedIn](https://linkedin.com/in/ashutoshjaiswal5) | ajjaiswal55@utexas.edu