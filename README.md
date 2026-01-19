# Home Health Analytics System

A full-stack analytics platform for home health billing data, featuring a FastAPI backend and Next.js dashboard.

## Prerequisites

- **Node.js** >= 18.0.0
- **pnpm** >= 8.0.0
- **Python** >= 3.9

## Quick Start

```bash
# Install all dependencies (Node.js + Python)
pnpm install:all

# Start development servers (API + Frontend)
pnpm start
```

This starts:
- **API Server**: http://localhost:8000 (API docs at http://localhost:8000/docs)
- **Frontend Dashboard**: http://localhost:3000

## Installation

### Install Node.js Dependencies Only

```bash
pnpm install
```

This installs root dependencies and automatically runs `postinstall` to install dashboard dependencies.

### Install Python Dependencies Only

```bash
pnpm install:python
# or manually:
pip install -r requirements.txt
```

### Install Everything

```bash
pnpm install:all
```

## Development

### Start All Services (Recommended)

```bash
pnpm start
# or
pnpm dev
```

Runs both the FastAPI backend and Next.js frontend concurrently in development mode with hot-reload.

### Start Services Individually

```bash
# Start only the API server
pnpm start:api

# Start only the frontend (in another terminal)
pnpm start:frontend
```

## Production

### Build for Production

```bash
pnpm build
```

This runs:
1. `pnpm build:analytics` - Generates analytics output files
2. `pnpm build:dashboard` - Builds the Next.js production bundle

### Start Production Servers

```bash
pnpm start:prod
```

Runs the API server and serves the production-built frontend.

## Analytics Generation

Analytics are generated from the data in `data/` directory and output to `analytics_output/`.

### When to Regenerate Analytics

Run analytics generation when:
- New PDF files are added to `data/pdfs/`
- Data files in `data/excel/` are updated
- You need fresh analytics output

### Generate Analytics

```bash
# Generate analytics only
pnpm build:analytics

# Or generate analytics + build dashboard
pnpm build
```

### Refresh Analytics via API

You can also trigger a refresh through the running API:

```bash
curl http://localhost:8000/analytics/refresh
```

Or process new PDFs:

```bash
curl -X POST http://localhost:8000/process-pdfs
```

## Available Scripts

| Command | Description |
|---------|-------------|
| `pnpm install` | Install Node.js deps (root + dashboard) |
| `pnpm install:python` | Install Python dependencies |
| `pnpm install:all` | Install all dependencies |
| `pnpm start` | Start API + Frontend (dev mode) |
| `pnpm dev` | Alias for `pnpm start` |
| `pnpm start:api` | Start only API server |
| `pnpm start:frontend` | Start only frontend (dev) |
| `pnpm start:prod` | Start API + Frontend (production) |
| `pnpm build` | Build analytics + dashboard |
| `pnpm build:analytics` | Generate analytics outputs |
| `pnpm build:dashboard` | Build Next.js production bundle |
| `pnpm lint` | Run ESLint on dashboard |

## Project Structure

```
home-health/
├── api_server.py           # FastAPI backend server
├── pivot_analytics.py      # Analytics generation engine
├── profitability_analysis.py
├── home_health_extractor.py
├── requirements.txt        # Python dependencies
├── package.json            # Root package.json with scripts
├── data/                   # Source data (not in git)
│   ├── pdfs/              # PDF files for extraction
│   └── excel/             # Excel/CSV data files
├── analytics_output/       # Generated analytics (not in git)
└── home-health-dashboard/  # Next.js frontend
    ├── src/
    │   ├── app/           # Next.js app router pages
    │   └── components/    # React components
    └── package.json
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | API info and available endpoints |
| `GET /analytics/summary` | Dashboard summary metrics |
| `GET /analytics/revenue-by-claim` | Revenue analysis |
| `GET /analytics/service-costs` | Service cost breakdown |
| `GET /analytics/profitability-by-patient` | Patient profitability |
| `GET /analytics/provider-performance` | Provider metrics |
| `GET /analytics/insurance-performance` | Insurance payer analysis |
| `GET /profitability/analysis` | Full profitability report |
| `GET /explorer/claims` | Raw claims data |
| `GET /explorer/costs` | Employee costs data |
| `POST /process-pdfs` | Process PDFs and regenerate analytics |
| `GET /analytics/refresh` | Reload analytics from files |

Full API documentation available at http://localhost:8000/docs when the server is running.
