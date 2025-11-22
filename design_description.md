# 1. Product spec (v1)

## 1.1. Core idea

Internal research tool for EU equities where you:

1. **Chat with an LLM copilot** about companies and people.
2. Have a **live Excel-like sheet** the LLM can read/write.
3. Get **news and official docs** (ANAF/fisc etc.) on demand.
4. Import/export **.xlsx** files with high Excel parity.
5. See a **custom forward-looking score** for each equity: the
   **Forward Outlook Score (FOS)** (name we’ll use; you can rename later).

---

## 1.2. Main user flows

1. **Research equity + auto-create sheet**

   * User: “Analyze ASML and give me key metrics + Forward Outlook Score.”
   * LLM:

     * Calls tools to scrape data (Finviz + other sites).
     * Computes FOS.
     * Returns explanation in chat.
     * Creates a sheet `ASML_Overview` and fills a table with key metrics + FOS breakdown.

2. **Upload Excel, fill missing fields**

   * User uploads `.xlsx` that has a list of EU tickers and some columns.
   * LLM:

     * Reads sheet.
     * Detects missing columns (P/E, sector, FOS, etc.).
     * Fetches missing data and fills table; explains changes in the chat.

3. **News & docs on a company**

   * User: “For LVMH, show recent news and ANAF/fisc documents if any, and adjust FOS accordingly.”
   * LLM:

     * Tool: `get_news("LVMH", last_30_days)`.
     * Tool: `get_official_docs("LVMH")` (for relevant jurisdictions).
     * Updates FOS sub-scores (e.g., sentiment, risk).
     * Writes updates into sheet and explains.

4. **What-if / scenario**

   * User: “Assume revenue grows 8% and margins improve 1%, recompute valuation & FOS.”
   * LLM:

     * Modifies a valuation sheet, recalculates outputs (using formulas).
     * Updates FOS and describes impact.

---

# 2. Architecture overview

## 2.1. High-level diagram (described)

* **Frontend (Angular)**

  * Chat module
  * Spreadsheet module
  * News/docs module
  * Settings/model config
  * File import/export

* **Backend (Python, FastAPI)**

  * `auth` (simple local auth or none for dev)
  * `chat` (LLM orchestrator + tool router)
  * `sheets` (CRUD for workbooks/sheets + formula engine)
  * `scrapers` (Finviz + other sites; news; official docs)
  * `fos` (Forward Outlook Score computation)
  * `files` (xlsx import/export)
  * `config` (model configs/env)

* **Data stores**

  * Postgres (or SQLite for local dev):

    * Users, sessions
    * Workbooks, sheets (data + metadata)
    * Cached scraped data
    * News / docs metadata
  * Local filesystem:

    * Uploaded/temporary Excel files
    * Cached PDFs of official docs
  * Vector index (optional, local):

    * For semantic search over docs (e.g., Qdrant Docker or simple FAISS file).

* **External services**

  * OpenRouter (LLMs)
  * Browser Agent HTTP API
  * Public websites (Finviz, other finance sites, ANAF/fisc, news pages).

---

# 3. Backend design (Python / FastAPI)

## 3.1. Tech choices

* **Framework**: FastAPI
* **ORM**: SQLAlchemy + Alembic (migrations)
* **HTTP client**: `httpx` (async)
* **Excel**: `openpyxl` or `XlsxWriter` + `pandas` + `pyxlsb` if needed.
* **Formula engine** (for Excel parity):

  * Option A: use something like [Hyperformula] (JS) in frontend; backend just stores raw values & formulas.
  * Option B: simpler: backend does not evaluate formulas; the grid evaluates them client-side. For v1 this is fine.

### 3.2. API modules

#### 3.2.1. Auth

Since it’s single-user, local, you can keep it simple:

* `POST /api/auth/login` – local password from env.
* `GET /api/auth/me` – returns user info.
* Use a signed JWT or session cookie.

#### 3.2.2. Chat (LLM orchestrator)

* `POST /api/chat`

  * Input:

    ```json
    {
      "conversation_id": "optional",
      "messages": [
        {"role": "user", "content": "Analyze ASML"},
        {"role": "assistant", "content": "..." }
      ],
      "model_config_name": "default"   // e.g., "fast_demo", "quality"
    }
    ```

  * Backend:

    * Loads model config (OpenRouter model name, temperature, etc.).
    * Builds system prompt with:

      * App role
      * Tools descriptions (JSON schemas)
      * FOS definition
      * Rules (only cite sources for news, etc.).
    * Calls OpenRouter’s chat completion with **function calling** (tools).
    * When model requests a tool:

      * Call internal endpoints/services (search_financial_data, get_news, etc.).
      * Feed results back to the LLM.
    * Stream or return final assistant message + tool traces.

  * Output:

    ```json
    {
      "conversation_id": "abc123",
      "assistant_message": {...},
      "tool_calls": [ ... ],
      "sources": [ ... ]   // for UI cites
    }
    ```

##### Tools exposed to the LLM

Define them in the system prompt as JSON schemas:

1. `search_financial_data`

   ```json
   {
     "name": "search_financial_data",
     "description": "Get structured financial data for an EU equity by ticker or company name.",
     "parameters": {
       "type": "object",
       "properties": {
         "ticker": {"type": "string"},
         "exchange": {"type": "string"},
         "fields": {
           "type": "array",
           "items": {"type": "string"},
           "description": "E.g. pe, eps, market_cap, sector, country, debt_to_equity, etc."
         }
       },
       "required": ["ticker"]
     }
   }
   ```

2. `get_news`

   ```json
   {
     "name": "get_news",
     "description": "Get recent news for a company or ticker.",
     "parameters": {
       "type": "object",
       "properties": {
         "query": {"type": "string"},
         "tickers": {
           "type": "array",
           "items": {"type": "string"}
         },
         "days": {"type": "integer", "default": 7},
         "limit": {"type": "integer", "default": 10}
       },
       "required": ["query"]
     }
   }
   ```

3. `get_official_docs`

   ```json
   {
     "name": "get_official_docs",
     "description": "Search official tax/fiscal documents for a given entity.",
     "parameters": {
       "type": "object",
       "properties": {
         "entity_name": {"type": "string"},
         "country": {"type": "string", "default": "RO"},
         "limit": {"type": "integer", "default": 5}
       },
       "required": ["entity_name"]
     }
   }
   ```

4. `read_sheet`, `write_sheet`, `create_sheet`

   ```json
   {
     "name": "read_sheet",
     "description": "Read a range from a sheet.",
     "parameters": {
       "type": "object",
       "properties": {
         "workbook_id": {"type": "string"},
         "sheet_name": {"type": "string"},
         "range": {"type": "string", "description": "A1 notation"}
       },
       "required": ["workbook_id", "sheet_name", "range"]
     }
   }
   ```

   ```json
   {
     "name": "write_sheet",
     "description": "Write values into a sheet range.",
     "parameters": {
       "type": "object",
       "properties": {
         "workbook_id": {"type": "string"},
         "sheet_name": {"type": "string"},
         "range": {"type": "string"},
         "values": {
           "type": "array",
           "items": {
             "type": "array",
             "items": {}
           }
         }
       },
       "required": ["workbook_id", "sheet_name", "range", "values"]
     }
   }
   ```

   ```json
   {
     "name": "create_sheet",
     "description": "Create a new sheet, optionally from a template.",
     "parameters": {
       "type": "object",
       "properties": {
         "workbook_id": {"type": "string"},
         "sheet_name": {"type": "string"},
         "template": {
           "type": "string",
           "enum": ["empty", "equity_overview", "valuation_model", "comparables"]
         }
       },
       "required": ["workbook_id", "sheet_name"]
     }
   }
   ```

5. `compute_fos`

   ```json
   {
     "name": "compute_fos",
     "description": "Compute the Forward Outlook Score for an equity based on structured financial data and optional sentiment/risk inputs.",
     "parameters": {
       "type": "object",
       "properties": {
         "ticker": {"type": "string"},
         "fundamentals": {"type": "object"},
         "news_summary": {"type": "string"},
         "official_docs_summary": {"type": "string"}
       },
       "required": ["ticker", "fundamentals"]
     }
   }
   ```

Your backend implements each tool as a Python function; the chat orchestrator calls them when the LLM asks.

---

### 3.3. Scrapers & data sources

#### 3.3.1. Finviz & similar (for EU equities)

* Implement a `data_providers` module with pluggable scrapers:

  * `finviz_scraper.py`

    * Functions:

      * `get_equity_overview(ticker: str) -> dict`
      * `get_key_metrics(ticker: str) -> dict`
    * Use `httpx` + `BeautifulSoup4`.
    * Parse HTML and map to fields (P/E, EPS, ROE, Debt/Equity, etc.).
    * Cache responses in DB (ticker + timestamp) to avoid re-scraping.

  * Later add:

    * `investing_com_scraper.py`
    * `morningstar_scraper.py` (if allowed)
    * etc.

* `financial_data_service.py`

  * Orchestrates providers:

    * Given `ticker`, query each provider in order of preference.
    * Merge results, prefer latest / most complete.

#### 3.3.2. News

* For v1:

  * Use Browser Agent to search/browse and return top links for each query.
  * Or write a simple aggregator using:

    * `NewsAPI`-like services or just manual Google News scraping (for internal use).

* `news_service.py`:

  * `search_news(query, tickers, days, limit) -> list[NewsItem]`
  * Store (title, url, source, date, snippet, sentiment) in cache.

#### 3.3.3. Official docs (ANAF/fisc etc.)

* `govdocs_scraper.py`:

  * Scrape public lists of decisions, press releases, sanctions, etc.
  * For each document:

    * Download HTML/PDF.
    * Extract text (using `pdfplumber` or `PyMuPDF` for PDFs).
    * Store:

      * `id`, `entity_name`, `entity_id` (if present), `country`, `date`, `doc_type`, `url`, `text_excerpt`, `full_text_path`.
  * Run as a CLI/cron script locally to build your corpus.

* `govdocs_service.py`:

  * Search by `entity_name` (exact/approx match).
  * Optional: add simple trigram search or vector similarity for better matches.

---

### 3.4. Sheets service

Data model ideas (simplified):

* `Workbook`:

  * `id`, `name`, `created_at`, `updated_at`
* `Sheet`:

  * `id`, `workbook_id`, `name`, `order`
* `Cell`:

  * `sheet_id`, `row`, `col`, `value`, `formula`, `format`

For performance you might store sheet as a JSON blob per sheet instead of row/col per cell, e.g.:

```json
{
  "cells": {
    "A1": {"v": "Ticker", "f": null},
    "B1": {"v": "Market Cap", "f": null},
    "A2": {"v": "ASML", "f": null}
  }
}
```

API:

* `GET /api/workbooks`
* `POST /api/workbooks`
* `GET /api/workbooks/{id}`
* `POST /api/workbooks/{id}/sheets`
* `GET /api/workbooks/{id}/sheets/{sheet_name}`
* `PATCH /api/workbooks/{id}/sheets/{sheet_name}` – write range.
* `POST /api/workbooks/{id}/import` – upload `.xlsx`.
* `GET /api/workbooks/{id}/export` – download `.xlsx`.

The sheet grid in Angular will map cell data to UI, and optionally use a JS formula engine for calculations.

---

### 3.5. Files (Excel import/export)

* `files_service.py`:

  * `import_xlsx(file_bytes) -> WorkbookModel`

    * Use `openpyxl` to read sheet names, cell values, formulas.
    * Store into your DB model.
  * `export_xlsx(workbook_id) -> bytes`

    * Fetch workbook/sheets from DB.
    * Create new `.xlsx` via `openpyxl` or `XlsxWriter`.
    * Write values + formulas.

---

### 3.6. Model configuration

Config file `models.yaml`:

```yaml
default_model: "fast_demo"
models:
  fast_demo:
    provider: "openrouter"
    model_name: "gpt-4.1-mini"          # example
    temperature: 0.3
  quality:
    provider: "openrouter"
    model_name: "gpt-4.1"               # example
    temperature: 0.2
```

Backend:

* Expose `GET /api/config/models` to list.
* `POST /api/config/models/use` to set current or choose per chat.

Frontend:

* Settings menu where you pick the active profile.

---

# 4. Frontend design (Angular)

## 4.1. Overall layout

Use a 3-pane layout:

* **Left pane (30–40%)** – Chat
* **Center pane (40–50%)** – Spreadsheet
* **Right pane (20–30%)** – News & Docs / Sources / FOS breakdown

Use Angular routing for tabs (e.g., `/workspace`, `/news`, `/settings`).

## 4.2. Angular modules & components

### Modules

* `AppModule` – root.
* `WorkspaceModule`

  * `ChatComponent`
  * `SheetComponent`
  * `SourcesPanelComponent`
  * `FosPanelComponent`
* `NewsModule`

  * `NewsFeedComponent`
  * `NewsFiltersComponent`
* `SettingsModule`

  * `ModelConfigComponent`
* `SharedModule`

  * UI elements, services, pipes.

### Key components

1. **ChatComponent**

   * Shows conversation as bubbles (user vs assistant).
   * Input box + send button.
   * Option to show/hide tool traces or sources.
   * When assistant writes: “I updated sheet X…”, show link to open that sheet.

2. **SheetComponent**

   * Uses an Angular data grid / sheet library:

     * e.g., AG Grid, Handsontable Angular wrapper, or similar.
   * Features:

     * Select workbook + sheet.
     * Edit cells, see formulas (Excel-like).
     * Auto-resize, copy-paste.
   * Emits:

     * `onCellChange`, `onSelectionChange` events so you can log / show context.
   * Buttons:

     * “Import Excel”
     * “Export Excel”
     * “New sheet from template” (dropdown).

3. **SourcesPanelComponent**

   * Shows list of sources for current answer:

     * News article titles & links.
     * Official docs with snippet.
   * Used mainly to display citations from the assistant.

4. **FosPanelComponent**

   * For selected ticker, show:

     * FOS total score (0–100).
     * Sub-scores:

       * Growth Outlook
       * Profitability Trend
       * Balance Sheet Health
       * Market Sentiment
       * Valuation
       * Risk
   * Can display a small radar chart or bar chart (nice visual).

5. **NewsFeedComponent**

   * List view:

     * Title, source, date, tags (tickers).
   * Filters:

     * Date range
     * Tickers
     * Source
   * Button “Explain this feed” → sends context to chat with LLM.

6. **ModelConfigComponent**

   * Dropdown for model profile (fast_demo / quality).
   * Option: show raw config details.

---

# 5. Forward Outlook Score (FOS) design

You wanted a single nice metric that “dictates the future of this equity.” We’ll define:

> **FOS (Forward Outlook Score)** – 0 to 100, higher = better expected medium-term outlook (e.g., 12–24 months).

### 5.1. Components

1. **Growth Outlook (G) – 0–100**

   * Inputs:

     * Revenue growth (1y / 3y)
     * EPS growth
     * Expected growth (if available)
   * Normalize:

     * Very negative growth → low score
     * Strong positive growth → high score.

2. **Profitability Trend (P) – 0–100**

   * Inputs:

     * Operating margin trend
     * ROE / ROIC
     * Net margin stability.
   * Penalize deteriorating margins.

3. **Balance Sheet Health (B) – 0–100**

   * Inputs:

     * Debt/Equity
     * Interest coverage
     * Cash/short-term assets vs liabilities.

4. **Market Sentiment (S) – 0–100**

   * Inputs:

     * Recent price momentum (1m/3m)
     * News sentiment (from `news_service`)
     * Analyst tone (if scraped).

5. **Valuation Position (V) – 0–100**

   * Compare P/E, EV/EBITDA, P/B to sector or index:

     * If high quality and cheap vs peers → high score.
     * If expensive with weak fundamentals → low score.

6. **Risk Profile (R) – 0–100** (Inverted risk)

   * Inputs:

     * Volatility (beta)
     * Size (small caps more risky)
     * Regulatory/official-doc red flags.

### 5.2. Formula

Example weighting (tweak later):

* FOS = 0.2·G + 0.2·P + 0.15·B + 0.15·S + 0.2·V + 0.1·R

Where each sub-score is computed with min-max / z-score normalization on typical ranges.

In practice:

* Implement numeric functions in `fos_service.py`:

  * `compute_growth_score(data)`
  * `compute_profitability_score(data)`
  * `compute_balance_sheet_score(data)`
  * `compute_sentiment_score(news_items)`
  * `compute_valuation_score(data, sector_data)`
  * `compute_risk_score(data, docs)`
* Expose `compute_fos` tool to LLM, but computation is deterministic.

The sheet templates can also show:

* Row for each sub-score.
* Comments from the LLM explaining each component.

---

# 6. Implementation roadmap (step-by-step)

### Phase 1 – Skeleton

1. Setup repo with:

   * `backend/` – FastAPI project
   * `frontend/` – Angular project
2. Implement minimal FastAPI server with healthcheck:

   * `GET /api/health`.
3. Add OpenRouter integration:

   * `POST /api/chat/test` – simple echo style.

### Phase 2 – Frontend shell

1. Create Angular project + routing.
2. Implement layout:

   * 3-column workspace with empty components.
3. Implement basic ChatComponent:

   * Calls `/api/chat/test` and displays messages.

### Phase 3 – Sheets backend & frontend

1. Backend:

   * Models for Workbook/Sheet.
   * In-memory or SQLite storage.
   * `GET/POST /api/workbooks`, `POST /api/workbooks/{id}/sheets`.
   * `PATCH /api/workbooks/{id}/sheets/{sheet_name}` – write a small range.
2. Frontend:

   * Integrate a grid (AG Grid, Handsontable).
   * Bind to `SheetComponent`.
   * Show dummy data.

### Phase 4 – Excel import/export

1. Backend:

   * Add `/api/workbooks/{id}/import`:

     * Accept file upload.
     * Use `openpyxl` to parse.
   * Add `/api/workbooks/{id}/export`:

     * Generate `.xlsx`.
2. Frontend:

   * File upload button → call import.
   * “Download” button → open export URL.

### Phase 5 – LLM orchestrator & tools

1. Implement `chat` endpoint:

   * Accept conversation, call OpenRouter with function calling.
   * Implement first tools:

     * `read_sheet`, `write_sheet`, `create_sheet`.
   * Test: user asks “create a sheet with A1,B1 headers and fill them”.

2. Add `search_financial_data` tool:

   * Implement `finviz_scraper`.
   * Map Finviz fields into normalized dict.
   * Wire tool → service.

3. Add `get_news` tool:

   * Use Browser Agent (or simple stub) for now.

### Phase 6 – FOS metric

1. Implement `fos_service.py` with numeric logic.
2. Add `compute_fos` tool.
3. Add sheet template `equity_overview`:

   * FOS and sub-scores table formatted.
4. In the system prompt, explain FOS so LLM can speak about it.

### Phase 7 – Official docs ingestion

1. Write `govdocs_scraper` CLI that:

   * Crawls ANAF/fisc pages.
   * Saves basic metadata + full text.
2. Add `govdocs_service` to query by entity name.
3. Expose `get_official_docs` tool.
4. Have LLM use docs to adjust risk/sentiment and FOS.

### Phase 8 – News/Docs UI

1. `NewsFeedComponent`:

   * Display results from `/api/news`.
   * Filters.
2. `SourcesPanelComponent`:

   * For each chat answer, show news/docs used.

### Phase 9 – Model config & polish

1. Implement model config file + endpoints.
2. Angular settings page to switch between `fast_demo` and `quality`.
3. Minor UX improvements:

   * Loading states, error messages.
   * Clear indicator when LLM edited the sheet (e.g., “Last updated by AI via prompt XYZ”).
