# Document 1 — Architecture + Modular Repository Structure + Tech Stack + Dependency Audit

## 1. Purpose

This document defines the implementation architecture for a **single-user, local-laptop business intelligence scraping application**.

The application accepts:

- City name
- One, multiple, or all business categories
- Configurable match-confidence threshold
- Optional manually supplied platform URLs
- Optional platform-directory selection
- Platform auto-selection based on business category

It then:

1. Discovers businesses from Google Maps.
2. Discovers businesses independently from selected business/booking platforms.
3. Extracts website data where a website exists.
4. Extracts phone, email, social profiles and other public business information.
5. Checks platform presence and, where supported, actual bookability/availability.
6. Normalizes all records.
7. Matches Google and platform entities using deterministic weighted confidence scoring.
8. Produces five spreadsheet outputs.
9. Displays the same run status, records, scores, errors and results in the frontend.

This is **not a SaaS architecture**. It is optimized for one operator running the application on one laptop.

---

## 2. Architectural principles

### 2.1 Local-first

No mandatory cloud backend is required.

Recommended local components:

```text
Desktop/Laptop
├── Frontend
├── Local API
├── Worker runtime
├── Local PostgreSQL/SQLite database
├── Browser runtime
├── Scraper storage
└── Excel export directory
```

### 2.2 HTTP-first, browser-second

The system must not open a browser for every website.

Extraction order:

```text
HTTP request
   ↓
HTML / JSON / JSON-LD extraction
   ↓ failure / JS-only
Browser extraction
   ↓ failure
Retry policy
   ↓
Blocked / unavailable / failed status
```

This is essential for laptop memory efficiency.

### 2.3 Deterministic; no LLM dependency

No LLM API is required for:

- category routing
- platform selection
- website extraction
- social extraction
- entity matching
- confidence scoring
- deduplication
- normalization
- spreadsheet generation

Use:

- URL parsing
- JSON-LD
- CSS/XPath
- regex
- normalized string comparison
- phone normalization
- domain comparison
- address token similarity
- geographic distance
- category dictionaries
- deterministic scoring rules
- state machines

### 2.4 Adapter architecture

Every external platform is an adapter.

```text
PlatformAdapter
├── discover()
├── extract()
├── normalize()
├── check_presence()
├── check_availability()
├── health_check()
└── get_capabilities()
```

Adding Fresha, Booksy, Treatwell or another platform should not require modifying the matching engine.

### 2.5 Source-of-truth separation

Never overwrite raw scraped information with normalized information.

Store:

```text
RAW
 ↓
NORMALIZED
 ↓
MATCHING
 ↓
MERGED
 ↓
EXPORT
```

This preserves auditability.

---

# 3. Recommended technology stack

| Layer | Recommended technology | Reason |
|---|---|---|
| Frontend | React + TypeScript + Vite | Fast local UI |
| Styling | Tailwind CSS | Consistent responsive UI |
| Icons | Lucide React | Lightweight |
| Charts | Recharts | Run metrics |
| API | FastAPI | Python-native, easy local deployment |
| Validation | Pydantic | Strong schemas |
| ORM | SQLAlchemy 2 | Mature Python ORM |
| DB | SQLite initially; PostgreSQL optional | SQLite is ideal for one laptop |
| Queue | DB-backed job queue initially | Avoid Redis overhead |
| Browser | Playwright | Reliable dynamic-page automation |
| HTTP scraping | Scrapling / httpx | Fast extraction |
| General crawling | Crawlee Python if adopted | Queue/retry/browser management |
| Google Maps | Gosom Google Maps Scraper | Specialized Maps discovery |
| Excel | openpyxl | Native `.xlsx` creation |
| Logging | structlog/logging | Structured local logs |
| Tests | pytest + Playwright tests | Unit/integration/E2E |
| Packaging | PyInstaller or local launcher | Single-user deployment |
| Configuration | YAML + `.env` | Local configuration |
| Data validation | Pydantic | Typed boundary validation |

Crawlee currently provides HTTP and browser crawling, queues, storage, retries, routing, browser management and Playwright integration; it is therefore a candidate for the orchestration layer rather than a mandatory second crawler. citeturn0search0turn0search12

Scrapling provides HTTP fetchers, browser-backed fetchers and adaptive extraction, making it appropriate for the generic website layer. citeturn0search1

Agent-Reach is primarily an internet/platform capability router rather than the core business crawler. Its current repository describes multiple platform backends and upstream-tool routing. citeturn0search2turn0search3

---

# 4. Final repository architecture

```text
business-intelligence-scraper/
│
├── app/
│   ├── main.py
│   │
│   ├── config/
│   │   ├── settings.py
│   │   ├── logging.py
│   │   ├── constants.py
│   │   └── environment.py
│   │
│   ├── api/
│   │   ├── router.py
│   │   ├── dependencies.py
│   │   ├── schemas/
│   │   │   ├── runs.py
│   │   │   ├── businesses.py
│   │   │   ├── platforms.py
│   │   │   ├── matching.py
│   │   │   └── exports.py
│   │   └── routes/
│   │       ├── health.py
│   │       ├── runs.py
│   │       ├── businesses.py
│   │       ├── platforms.py
│   │       ├── matching.py
│   │       └── exports.py
│   │
│   ├── core/
│   │   ├── domain/
│   │   │   ├── enums.py
│   │   │   ├── value_objects.py
│   │   │   └── models.py
│   │   ├── rules/
│   │   │   ├── category_rules.py
│   │   │   ├── platform_rules.py
│   │   │   ├── matching_rules.py
│   │   │   └── availability_rules.py
│   │   └── services/
│   │       ├── discovery_service.py
│   │       ├── enrichment_service.py
│   │       ├── matching_service.py
│   │       ├── normalization_service.py
│   │       └── export_service.py
│   │
│   ├── database/
│   │   ├── engine.py
│   │   ├── session.py
│   │   ├── models/
│   │   ├── repositories/
│   │   └── migrations/
│   │
│   ├── workers/
│   │   ├── manager.py
│   │   ├── queue.py
│   │   ├── scheduler.py
│   │   ├── jobs/
│   │   │   ├── maps_discovery.py
│   │   │   ├── platform_discovery.py
│   │   │   ├── website_enrichment.py
│   │   │   ├── social_enrichment.py
│   │   │   ├── availability.py
│   │   │   ├── matching.py
│   │   │   └── export.py
│   │   └── retry_policy.py
│   │
│   ├── scraping/
│   │   ├── base/
│   │   │   ├── adapter.py
│   │   │   ├── request.py
│   │   │   ├── response.py
│   │   │   └── capabilities.py
│   │   ├── maps/
│   │   │   ├── gosom_adapter.py
│   │   │   └── mapper.py
│   │   ├── website/
│   │   │   ├── http_fetcher.py
│   │   │   ├── browser_fetcher.py
│   │   │   ├── jsonld.py
│   │   │   ├── contact.py
│   │   │   ├── socials.py
│   │   │   └── website_classifier.py
│   │   └── platforms/
│   │       ├── registry.py
│   │       ├── generic_adapter.py
│   │       ├── fresha/
│   │       ├── booksy/
│   │       ├── treatwell/
│   │       └── custom/
│   │
│   ├── matching/
│   │   ├── candidate_generation.py
│   │   ├── name_matcher.py
│   │   ├── phone_matcher.py
│   │   ├── address_matcher.py
│   │   ├── domain_matcher.py
│   │   ├── category_matcher.py
│   │   ├── social_matcher.py
│   │   ├── score_engine.py
│   │   └── explanation.py
│   │
│   ├── exports/
│   │   ├── workbook.py
│   │   ├── styles.py
│   │   ├── filters.py
│   │   └── validators.py
│   │
│   └── observability/
│       ├── events.py
│       ├── metrics.py
│       └── run_logger.py
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── pages/
│   │   ├── components/
│   │   ├── features/
│   │   │   ├── run-configuration/
│   │   │   ├── discovery/
│   │   │   ├── platforms/
│   │   │   ├── matching/
│   │   │   ├── results/
│   │   │   └── exports/
│   │   ├── hooks/
│   │   ├── services/
│   │   ├── store/
│   │   ├── types/
│   │   └── utils/
│   └── package.json
│
├── platform_directory/
│   ├── platforms.yaml
│   ├── categories.yaml
│   └── mappings.yaml
│
├── data/
│   ├── database/
│   ├── raw/
│   ├── normalized/
│   ├── exports/
│   ├── browser/
│   └── logs/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── scraping/
│   ├── matching/
│   └── e2e/
│
├── scripts/
│   ├── setup.py
│   ├── seed_platforms.py
│   ├── migrate.py
│   └── clean_run.py
│
├── config/
│   ├── default.yaml
│   └── local.yaml
│
├── requirements.txt
├── pyproject.toml
├── package.json
└── README.md
```

README is documentation only and must never be treated as evidence for production-readiness auditing.

---

# 5. Module responsibility map

| Module | Responsibility | Must not do |
|---|---|---|
| `discovery_service` | Create discovery jobs | Parse platform-specific HTML |
| `platform_registry` | Select adapters | Perform scraping |
| `website_enrichment` | Extract website information | Match entities |
| `normalization_service` | Standardize fields | Decide business identity |
| `matching_service` | Match entities | Crawl websites |
| `score_engine` | Calculate confidence | Persist directly |
| `availability_service` | Check bookability | Export Excel |
| `export_service` | Create workbook | Scrape |
| `worker_manager` | Execute jobs | Business matching |
| API routes | Request/response transport | Long-running scraping |
| Frontend | Display/configure | Scrape directly |

---

# 6. Dependency policy

## Mandatory

```text
fastapi
uvicorn
pydantic
sqlalchemy
alembic
httpx
scrapling
playwright
openpyxl
python-dotenv
pyyaml
rapidfuzz
phonenumbers
beautifulsoup4
lxml
pytest
```

## Optional

```text
crawlee
structlog
orjson
geopy
tenacity
```

Crawlee is optional because the application can initially use a small DB-backed local queue. If the crawler grows beyond the initial architecture, Crawlee can replace custom queue/browser orchestration. Crawlee has both JavaScript/TypeScript and Python implementations. citeturn0search0turn0search12

## Avoid unless needed

- Redis
- Kafka
- RabbitMQ
- Kubernetes
- Docker-only deployment
- cloud object storage
- LLM APIs
- vector databases
- Elasticsearch

These add complexity without solving a requirement for one local operator.

---

# 7. Repository responsibilities of the previously evaluated projects

| Repository/tool | Keep? | Role |
|---|---|---|
| Gosom Google Maps Scraper | YES | Google Maps discovery |
| Google Maps Scraper Kit | OPTIONAL | Convenience wrapper around Maps scraper |
| Scrapling | YES | Generic website extraction |
| Playwright | YES | Complex dynamic workflows |
| Crawlee Python | RECOMMENDED | Queue/retry/crawler orchestration if custom queue becomes insufficient |
| Agent-Reach | OPTIONAL | Specific social/platform access |
| LLM browser | NO | Not needed for deterministic pipeline |

The Google Maps kit should not be confused with the underlying Maps scraping engine. Keep the kit only if its local workflow/cleaning/export features are useful; otherwise integrate the underlying scraper directly.

Agent-Reach is not useless, but it is not foundational to this application. Its purpose is broader platform capability access rather than entity-discovery/matching orchestration. citeturn0search3turn0search14

---

# 8. Laptop resource policy

Assume approximately 16 GB RAM.

Recommended browser limits:

```text
HTTP concurrency: 8–20
Browser contexts: 2–4
Browser pages/context: 1–2
Maps jobs: 1 active discovery job
Platform browser jobs: 1–2
```

Never create one Chromium process per business.

Use:

```text
one browser
  └── limited contexts
       └── limited pages
```

Prefer HTTP extraction wherever possible.

---

# 9. Run lifecycle

```text
CREATED
  ↓
VALIDATING
  ↓
DISCOVERING_GOOGLE
  ↓
DISCOVERING_PLATFORMS
  ↓
ENRICHING_WEBSITES
  ↓
CHECKING_PLATFORM_PRESENCE
  ↓
CHECKING_AVAILABILITY
  ↓
NORMALIZING
  ↓
MATCHING
  ↓
CLASSIFYING_UNMATCHED
  ↓
EXPORTING
  ↓
COMPLETED
```

Failure state:

```text
ANY STATE → PARTIAL_FAILURE
ANY STATE → FAILED
USER → CANCELLED
```

A partial failure must not delete successful records.

---

# 10. Non-functional architecture requirements

- All scraping operations must be resumable.
- Every external request must have timeout and retry limits.
- Every extracted field must retain source metadata.
- Every matching decision must have an explanation.
- Every availability result must have `checked_at`.
- Every run must have a unique ID.
- Every exported workbook must be tied to a run ID.
- No frontend component may contain scraper logic.
- No scraper may directly manipulate Excel.
- No platform adapter may directly call another platform adapter.
- Platform-specific logic stays isolated.

---

# 11. Architecture decision

### Final recommended stack

```text
React + TypeScript
        │
        ▼
FastAPI
        │
        ▼
Service / Rule Layer
        │
 ┌──────┼──────────┐
 ▼      ▼          ▼
SQLite  Job Queue  Matching Engine
 │
 ▼
Adapters
 ├── Google Maps / Gosom
 ├── Website / Scrapling
 ├── Browser / Playwright
 ├── Fresha adapter
 ├── Other platform adapters
 └── Social discovery
        │
        ▼
Normalizer
        │
        ▼
SQLite
        │
        ▼
Excel Export
```

This is the baseline architecture to implement.
