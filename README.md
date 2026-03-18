# OpsPulse — Workforce & Market Intelligence Platform

> A production-style analytics platform for operations managers. Ingests messy multi-source data, cleans it, stores it in a relational data warehouse, and exposes dashboards for workforce planning, ticket analytics, forecasting, and anomaly detection.

![OpsPulse Dashboard](docs/screenshot-overview.png)

---

## Business Problem

Operations teams routinely manage scheduling data, support tickets, market signals, and staffing metrics across disconnected spreadsheets and tools. Leaders have no unified view to answer: *Where are bottlenecks forming? Is staffing keeping pace with demand? What anomalies need attention today?*

OpsPulse consolidates these data streams into a single platform with automated cleaning, relational storage, and analytics dashboards — reducing the time to operational insight from hours to seconds.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         OpsPulse                                 │
│                                                                  │
│  ┌──────────────┐    ┌──────────────────┐    ┌───────────────┐  │
│  │  Data Sources│    │   FastAPI Backend │    │  Next.js UI   │  │
│  │              │    │                  │    │               │  │
│  │  CSV uploads │───▶│  ETL Pipeline    │    │  Overview     │  │
│  │  JSON feeds  │    │  ├─ Ingestion    │    │  Workforce    │  │
│  │  Mock API    │    │  ├─ Cleaning     │    │  Tickets      │  │
│  └──────────────┘    │  └─ Loader       │    │  Forecasting  │  │
│                      │                  │◀───│  Anomalies    │  │
│  ┌──────────────┐    │  Analytics       │    │  Market       │  │
│  │  PostgreSQL  │    │  ├─ Forecasting  │    │  Executive    │  │
│  │  Warehouse   │◀───│  ├─ Anomaly Det. │    └───────────────┘  │
│  │              │    │  └─ Narrative    │                        │
│  │  dim_date    │    │                  │                        │
│  │  dim_employee│    │  REST API /v1    │                        │
│  │  dim_dept    │    │  /workforce      │                        │
│  │  dim_location│    │  /tickets        │                        │
│  │  fact_ops    │    │  /analytics      │                        │
│  │  fact_ticket │    │  /ingestion      │                        │
│  │  fact_market │    └──────────────────┘                        │
│  │  staging_err │                                                 │
│  └──────────────┘                                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Warehouse Schema

```
dim_date ──────────────────────────────────────────────────────────┐
  id, date, year, quarter, month, week_of_year,                    │
  day_of_week, is_weekend, is_holiday, fiscal_year                 │
                                                                   │
dim_department                                                     │
  id, code, name, division, cost_center, headcount_target          │
                                                                   │
dim_location                                                       │
  id, code, city, region, country, timezone, is_remote             │
                                                                   │
dim_employee                                                       │
  id, employee_id, first_name, last_name, email,                   │
  role, level, employment_type, department_id, location_id,        │
  hire_date, is_active                                             │
                                                                   │
fact_operations ── fact table (employee × date)                    │
  id, date_id FK, employee_id FK, department_id FK, location_id FK │
  scheduled_hours, actual_hours, overtime_hours, absent,           │
  tasks_completed, tasks_assigned, utilization_rate,               │
  demand_units, capacity_units, source_file                        │
                                                                   │
fact_ticket ── fact table (1 row per ticket)                       │
  id, ticket_id, created_date_id FK, resolved_date_id FK,         │
  department_id FK, category, priority, status,                    │
  created_at, resolved_at, sla_target_hours,                      │
  actual_resolution_hours, sla_breached, channel, sentiment_score  │
                                                                   │
fact_market_signal ── fact table (1 row per signal)                │
  id, date_id FK, signal_date, source, category,                   │
  industry, region, value, change_pct                              │
                                                                   │
staging_error ── quarantine table                                  │
  id, source_file, source_type, row_number, raw_data (JSON),       │
  error_type, error_message, resolved                              │
```

---

## ETL Flow

```
CSV / JSON / API
      │
      ▼
 ┌─────────────────────────────────────┐
 │  Ingestion Layer (etl/ingestion.py) │
 │  • Column normalization             │
 │  • Schema validation                │
 │  • Dispatch to cleaner              │
 └────────────────┬────────────────────┘
                  │
      ▼
 ┌─────────────────────────────────────┐
 │  Cleaning Layer  (etl/cleaning.py)  │
 │  • Deduplication                    │
 │  • Date parsing                     │
 │  • Numeric coercion                 │
 │  • Range validation                 │
 │  • Derived field computation        │
 │  • Bad rows → error list            │
 └────────────────┬────────────────────┘
                  │                 bad rows
      ▼                               │
 ┌─────────────────────────────────────┐
 │  Loader Layer    (etl/loader.py)    │◀────── staging_error table
 │  • Upsert dim_date                  │
 │  • get_or_create dept/loc/emp       │
 │  • Bulk insert fact rows            │
 └─────────────────────────────────────┘
```

---

## Forecasting Methodology

**Model**: Ridge Regression with engineered time features

**Features**:
- Linear time index (`t = days since start`)
- Cyclic encoding of day-of-week and month (sin/cos)
- Day-of-month, week-of-year

**Why Ridge over ARIMA for a portfolio project?**
- Ridge has no stationarity requirements
- Handles small datasets gracefully (regularization)
- Easy to evaluate with standard MAE / RMSE
- Interpretable feature set

**Confidence intervals**: Normal approximation using rolling residual std (`z = 1.96` for 95%).

**Limitations**: Does not capture autoregressive structure or external shock events. Production use would benefit from a proper time-series model (SARIMA, Prophet, or LightGBM with lag features).

---

## Anomaly Detection

Two methods available:

| Method | Use Case | Strengths |
|--------|----------|-----------|
| **Z-Score (rolling 7d)** | Spike detection against local baseline | Adapts to trends; catches sharp deviations |
| **IQR Fence** | Robust outlier detection | Less sensitive to trend drift |

Severity classification: `critical (|z| > 4)`, `high (|z| > 3.5)`, `medium (|z| > 3)`, `low`.

Automated cause inference maps metric × direction to plain-English explanations displayed in the anomaly feed.

---

## Setup (Local Development)

### Prerequisites
- Python 3.11+
- Node.js 20+
- PostgreSQL 15+ (or Docker)

### Option A — Docker (Recommended)

```bash
# 1. Clone and start all services
git clone https://github.com/yourname/opspulse.git
cd opspulse
docker compose up --build

# 2. Seed the database with 90 days of synthetic data
docker compose --profile seed run seed

# 3. Open
#   Frontend: http://localhost:3000
#   API docs:  http://localhost:8000/api/docs
```

### Option B — Local

```bash
# --- Backend ---
cd backend
cp .env.example .env
# Edit DATABASE_URL in .env to point at your Postgres instance

python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Create tables + seed data
python -m app.seed.seed_data

# Start API
uvicorn app.main:app --reload --port 8000

# --- Frontend ---
cd ../frontend
npm install --legacy-peer-deps

# If backend is on a non-default URL:
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

npm run dev
# → http://localhost:3000
```

---

## Running Tests

```bash
cd backend
source venv/bin/activate

# All tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=app --cov-report=term-missing

# Specific suites
pytest tests/test_etl.py -v        # ETL cleaning logic
pytest tests/test_analytics.py -v  # Forecasting + anomaly detection
pytest tests/test_api.py -v        # API endpoints (uses SQLite in-memory)
```

**Test Coverage Areas**:
- `test_etl.py` — deduplication, date parsing, numeric coercion, schema validation, SLA computation
- `test_analytics.py` — forecast output shape, CI validity, anomaly detection sensitivity, cause inference
- `test_api.py` — all endpoints, date filters, role validation, error responses

---

## API Documentation

Interactive docs at `http://localhost:8000/api/docs` (Swagger UI).

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/v1/workforce/summary` | Aggregate workforce metrics |
| `GET` | `/api/v1/workforce/by-department` | Dept breakdown with status |
| `GET` | `/api/v1/workforce/utilization-heatmap` | Daily × dept utilization data |
| `GET` | `/api/v1/workforce/staffing-gaps` | Days where demand > capacity |
| `GET` | `/api/v1/tickets/summary` | Ticket KPIs |
| `GET` | `/api/v1/tickets/trends` | Daily volume trend |
| `GET` | `/api/v1/tickets/sla-report` | SLA breach rate by priority |
| `GET` | `/api/v1/tickets/by-category` | Category breakdown |
| `GET` | `/api/v1/analytics/forecast` | Ridge regression forecast |
| `GET` | `/api/v1/analytics/anomalies` | Z-score anomaly alerts |
| `GET` | `/api/v1/analytics/narrative` | AI-style narrative summary |
| `GET` | `/api/v1/analytics/market-signals` | Market intelligence feed |
| `POST` | `/api/v1/ingestion/upload` | Upload CSV/JSON file |
| `GET` | `/api/v1/ingestion/errors` | Quarantined ingestion errors |

**Common query parameters**: `start_date`, `end_date`, `department_code`

**Example**:
```bash
curl "http://localhost:8000/api/v1/workforce/summary?start_date=2024-01-01&end_date=2024-01-31"
curl "http://localhost:8000/api/v1/analytics/forecast?metric=ticket_volume&horizon_days=30"
curl "http://localhost:8000/api/v1/analytics/anomalies?metric=ticket_volume"
```

---

## Project Structure

```
opspulse/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, CORS, startup
│   │   ├── config.py            # Settings via pydantic-settings
│   │   ├── database.py          # SQLAlchemy engine + session
│   │   ├── models/
│   │   │   ├── dimensions.py    # DimDate, DimDept, DimLocation, DimEmployee
│   │   │   └── facts.py         # FactOperations, FactTicket, FactMarketSignal
│   │   ├── schemas/             # Pydantic response schemas
│   │   ├── etl/
│   │   │   ├── cleaning.py      # Pandas-based data cleaners
│   │   │   ├── ingestion.py     # CSV/JSON ingest dispatcher
│   │   │   └── loader.py        # DB writers + dim upserts
│   │   ├── analytics/
│   │   │   ├── forecasting.py   # Ridge regression with time features
│   │   │   ├── anomaly_detection.py  # Z-score + IQR methods
│   │   │   └── narrative.py     # Plain-English summary generator
│   │   ├── api/endpoints/       # FastAPI routers
│   │   └── seed/seed_data.py    # 90-day synthetic seed
│   ├── tests/                   # pytest suites
│   ├── data/                    # Sample CSV/JSON data
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/                 # Next.js App Router pages
│   │   │   ├── page.tsx         # Overview dashboard
│   │   │   ├── workforce/       # Utilization + heatmap + gaps
│   │   │   ├── tickets/         # Volume + SLA + categories
│   │   │   ├── forecasting/     # Forecast chart + model info
│   │   │   ├── anomalies/       # Alert feed + severity breakdown
│   │   │   ├── market/          # Market signals table + chart
│   │   │   └── executive/       # Clean leadership summary
│   │   ├── components/          # Dashboard components + UI kit
│   │   └── lib/                 # API client + utils
│   ├── Dockerfile
│   └── package.json
├── .github/workflows/ci.yml     # CI: test + lint + build
└── docker-compose.yml
```

---

## Sample Data

| File | Rows | Description |
|------|------|-------------|
| `data/sample_workforce.csv` | 1,078 | 49 employees × 30 workdays across 5 departments |
| `data/sample_tickets.csv` | 530 | 30 days of tickets with priorities, SLAs, sentiments |
| `data/sample_market.json` | 130 | Market signals across 5 industries and 4 categories |

Seed script generates **90 days** of richer synthetic data with an intentional anomaly injected into the SUPPORT department in days 35–42 (elevated ticket volume + absenteeism spike) — demonstrable to interviewers.

---

## Assumptions & Known Limitations

- Forecasting uses Ridge regression. For high-frequency production data, SARIMA or Prophet would be more accurate.
- Anomaly detection uses a 7-day rolling window; sparse datasets may produce false positives in early rows.
- The narrative generator uses SQL aggregates only — no LLM is called. Metrics are factual, not hallucinated.
- Authentication is not implemented — add JWT middleware for real deployments.
- Export to CSV/PDF is implemented via browser-side CSV download; PDF requires a report rendering library (e.g., WeasyPrint).

---

## Resume Bullets (Reference)

- Built a full-stack operations intelligence platform using **Python, FastAPI, PostgreSQL, Pandas, scikit-learn**, and **Next.js** to ingest, clean, and analyze multi-source enterprise operational data.
- Designed **ETL pipelines** with schema validation, deduplication, and error quarantine; implemented a **star-schema data warehouse** with 4 dimension tables and 3 fact tables.
- Developed **Ridge regression forecasting** with engineered cyclic time features and confidence intervals, plus **Z-score and IQR anomaly detection** with automated severity classification and cause inference.
- Built **role-based dashboards** (analyst, lead, executive) exposing workforce utilization heatmaps, SLA breach tracking, staffing gap analysis, and a plain-English narrative summary generator.
- Added **automated testing** (pytest, 3 suites) covering ETL logic, analytics correctness, and API endpoints; shipped **Docker Compose** configuration and **GitHub Actions CI** pipeline.

---

## Interview Demo Script

> "OpsPulse is an operations intelligence platform I built to replicate the kind of internal analytics tool a data or analytics team would own. Let me walk you through it quickly.

> Starting on the **Overview page** — this is the analyst's daily dashboard. It pulls workforce utilization and ticket volume for the last 30 days. The AI Narrative card at the top automatically generates a plain-English summary from computed SQL metrics — things like 'support demand rose 34% period-over-period while staffing rose only 6%'.

> On the **Workforce page**, there's a utilization heatmap — each cell is a department × day combination, colour-coded by utilization rate. Red means over-capacity, green is optimal. The staffing gaps table shows days where demand exceeded capacity by more than 5%.

> On the **Forecasting page**, I used Ridge regression with cyclic time features — sin/cos encoding for day-of-week and month — to produce a 30-day forecast with a 95% confidence band. You can switch between ticket volume, demand units, and utilization rate.

> On the **Anomalies page** — I seeded a deliberate spike in the Support department around days 35–42. The Z-score detector surfaces that automatically and shows the inferred likely cause.

> Under the hood: Python FastAPI with a proper star-schema PostgreSQL data warehouse, a Pandas-based ETL layer that validates, deduplicates, and quarantines bad rows, and three pytest suites covering the ETL logic, analytics correctness, and all API endpoints. Everything runs in Docker with a one-command seed."

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| API | Python 3.11, FastAPI, Uvicorn |
| ORM | SQLAlchemy 2.0 |
| Database | PostgreSQL 15 |
| ETL | Pandas, NumPy |
| ML | scikit-learn (Ridge, StandardScaler) |
| Frontend | Next.js 14, React 18, TypeScript |
| Charts | Recharts |
| Styling | Tailwind CSS |
| Testing | pytest, SQLite in-memory |
| CI | GitHub Actions |
| Infra | Docker, Docker Compose |
