# Document 3 — Backend + API + Workers + WebSockets + Integrations + Architecture

## 1. Backend objective

The backend is the orchestration and data-integrity layer.

It must:

- validate user input
- create runs
- select platforms
- generate discovery jobs
- execute scraping
- normalize data
- enrich websites
- check platform presence
- check availability
- generate match candidates
- score matches
- classify unmatched records
- persist every stage
- publish progress to the frontend
- export the five-sheet workbook

---

# 2. Backend architecture

```text
React Frontend
      │
      │ REST
      ▼
FastAPI
      │
      ├──────── WebSocket ───────► Frontend
      │
      ▼
Application Services
      │
      ├── Run Service
      ├── Discovery Service
      ├── Enrichment Service
      ├── Matching Service
      ├── Availability Service
      └── Export Service
      │
      ▼
Job Queue
      │
      ├── Google Maps Worker
      ├── Platform Worker
      ├── Website Worker
      ├── Social Worker
      ├── Availability Worker
      ├── Matching Worker
      └── Export Worker
      │
      ▼
Database
```

---

# 3. API conventions

Base URL:

```text
/api/v1
```

JSON responses should use:

```json
{
  "success": true,
  "data": {},
  "error": null,
  "request_id": "..."
}
```

Errors:

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "INVALID_CITY",
    "message": "City could not be resolved"
  },
  "request_id": "..."
}
```

---

# 4. Run creation API

## POST `/runs`

Request:

```json
{
  "city": "Mumbai",
  "categories": [
    "salon",
    "restaurant",
    "garage"
  ],
  "category_mode": "selected",
  "confidence_threshold": 80,
  "platform_mode": "directory_plus_manual",
  "platform_ids": [
    "fresha"
  ],
  "platform_urls": []
}
```

Response:

```json
{
  "success": true,
  "data": {
    "run_id": "run_...",
    "status": "CREATED"
  }
}
```

---

# 5. Run validation

Before scraping:

```text
Validate city
Validate threshold
Validate categories
Validate platform URLs
Resolve platform directory
Check adapter availability
Build job plan
```

The backend returns a preflight summary:

```text
City: Mumbai
Categories: 3
Google discovery: enabled
Platform discovery: 4
Website enrichment: enabled
Availability checks: 3 platforms
Estimated jobs: 4,800
```

The user can then start the run.

---

# 6. Preflight endpoint

## POST `/runs/{run_id}/preflight`

Returns:

```json
{
  "google_searches": 3,
  "platforms": [
    "Fresha",
    "Platform B",
    "Platform C"
  ],
  "estimated_discovery_tasks": 6,
  "estimated_browser_tasks": 840,
  "warnings": [
    "Some platforms require browser rendering"
  ]
}
```

---

# 7. Start run

## POST `/runs/{run_id}/start`

The API must return immediately.

It must not perform scraping inside the HTTP request.

```text
HTTP request
   ↓
Create jobs
   ↓
Return 202
   ↓
Worker processes jobs
```

---

# 8. Cancel run

## POST `/runs/{run_id}/cancel`

Cancellation should be cooperative.

Workers check:

```python
if run.cancel_requested:
    stop_after_current_atomic_step()
```

Do not abruptly kill the database process.

---

# 9. Run status

## GET `/runs/{run_id}`

Return:

```json
{
  "status": "MATCHING",
  "progress": 76,
  "google_records": 1200,
  "platform_records": 860,
  "matched": 730,
  "google_unmatched": 320,
  "platform_unmatched": 130,
  "errors": 17
}
```

---

# 10. Business endpoints

```text
GET /runs/{run_id}/businesses
GET /runs/{run_id}/businesses/{id}
GET /runs/{run_id}/google-records
GET /runs/{run_id}/platform-records
GET /runs/{run_id}/matched
GET /runs/{run_id}/unmatched/google
GET /runs/{run_id}/unmatched/platform
```

Query parameters:

```text
page
page_size
search
category
platform
status
score_min
score_max
availability
website_status
```

---

# 11. Matching endpoints

## POST `/runs/{run_id}/rematch`

Request:

```json
{
  "threshold": 85
}
```

This must reuse existing source records where possible.

It should not rescrape the web unnecessarily.

## GET `/runs/{run_id}/matches`

Return candidate scores and explanations.

---

# 12. Platform endpoints

```text
GET /platforms
GET /platforms/{id}
POST /platforms
PATCH /platforms/{id}
DELETE /platforms/{id}
POST /platforms/test
```

Platform creation:

```json
{
  "name": "Example Platform",
  "base_url": "https://example.com",
  "categories": [
    "salon"
  ],
  "discovery_supported": true,
  "availability_supported": true
}
```

A generic platform should only be enabled if its adapter can actually perform the required workflow.

---

# 13. Website enrichment API

Internal service:

```python
enrich_website(source_record)
```

Flow:

```text
website URL
 ↓
HTTP fetch
 ↓
HTML parse
 ↓
JSON-LD
 ↓
contact extraction
 ↓
social extraction
 ↓
if insufficient:
    browser
 ↓
normalize
 ↓
persist
```

---

# 14. Worker architecture

Each worker consumes a job type.

```text
DISCOVER_GOOGLE
DISCOVER_PLATFORM
ENRICH_WEBSITE
EXTRACT_SOCIAL
CHECK_PLATFORM_PRESENCE
CHECK_AVAILABILITY
NORMALIZE_RECORD
MATCH_RECORD
EXPORT_WORKBOOK
```

---

# 15. Job schema

```sql
CREATE TABLE scrape_jobs (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    job_type TEXT NOT NULL,
    payload TEXT NOT NULL,
    status TEXT NOT NULL,
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    priority INTEGER DEFAULT 100,
    scheduled_at TEXT,
    started_at TEXT,
    completed_at TEXT,
    error_code TEXT,
    error_message TEXT,
    created_at TEXT NOT NULL
);
```

---

# 16. Job state machine

```text
QUEUED
 ↓
RUNNING
 ├── SUCCESS
 ├── RETRY
 ├── FAILED
 ├── BLOCKED
 └── CANCELLED
```

Retryable:

```text
timeout
temporary network error
HTTP 429
temporary 5xx
browser crash
```

Usually non-retryable:

```text
invalid URL
unsupported platform
permanent 404
malformed adapter configuration
```

---

# 17. Concurrency

For 16 GB RAM:

```text
Google Maps:
1 active job

HTTP:
8–20 concurrent requests

Browser:
2–4 concurrent contexts

Availability:
1–2 concurrent browser tasks/platform
```

The worker manager should dynamically lower concurrency when memory pressure increases.

---

# 18. WebSockets

Endpoint:

```text
/ws/runs/{run_id}
```

Events:

```json
{
  "event": "run.progress",
  "run_id": "run_123",
  "stage": "ENRICHING_WEBSITES",
  "completed": 720,
  "total": 1200,
  "percentage": 60
}
```

Other events:

```text
run.started
run.stage_changed
job.started
job.completed
job.failed
business.discovered
website.found
platform.found
match.created
availability.updated
run.warning
run.completed
run.failed
run.cancelled
```

---

# 19. WebSocket reconnect

Frontend must reconnect automatically.

When reconnecting:

```text
GET current run state
+
resume WebSocket
```

Do not rely on missed WebSocket events for data integrity.

WebSocket is for UX; database is the source of truth.

---

# 20. Google Maps integration

Recommended flow:

```text
Run
 ↓
Category search generation
 ↓
Google Maps scraper
 ↓
raw records
 ↓
source_records
 ↓
business normalization
```

Search examples:

```text
salons in Mumbai
restaurants in Mumbai
garages in Mumbai
```

For all categories:

```text
category registry
 ↓
generate searches
 ↓
deduplicate results
```

Do not generate one gigantic unbounded "all businesses" request.

---

# 21. Platform integration

Each platform adapter should implement:

```python
class PlatformAdapter(Protocol):

    def discover(self, context) -> list[SourceRecord]:
        ...

    def extract_listing(self, response) -> SourceRecord:
        ...

    def check_presence(self, business) -> PresenceResult:
        ...

    def check_availability(self, listing) -> AvailabilityResult:
        ...

    def health_check(self) -> HealthResult:
        ...
```

Optional capabilities:

```text
DISCOVERY
PROFILE
AVAILABILITY
SERVICES
PRICING
REVIEWS
SOCIALS
```

---

# 22. Generic platform adapter

For platforms without a custom adapter:

```text
platform URL
 ↓
HTTP fetch
 ↓
parse search/result links
 ↓
identify listing
 ↓
extract common fields
```

If dynamic:

```text
HTTP
 ↓ fail/insufficient
Playwright
```

Generic adapter must never pretend it supports availability if it cannot reliably identify booking state.

---

# 23. Fresha-style availability flow

Conceptually:

```text
Search platform
 ↓
Find listing
 ↓
Verify listing identity
 ↓
Open booking flow
 ↓
Check whether booking is enabled
 ↓
Read available slots if exposed
 ↓
Store timestamped snapshot
```

Result:

```text
Presence = FOUND
Bookable = TRUE
Availability = 2026-10-07T14:00+05:30
Checked = timestamp
```

Platform terms and access restrictions must be respected. The system should not bypass authentication, CAPTCHAs or technical access controls.

---

# 24. Website/social integration

Website parser should discover:

```text
mailto:
tel:
Instagram
Facebook
LinkedIn
YouTube
TikTok
X
WhatsApp
```

Social URLs may be discovered without visiting the social network.

This is preferable to unnecessary platform crawling.

---

# 25. Agent-Reach integration

Agent-Reach should be treated as an optional connector for specific platforms, not the core website crawler.

Its current architecture routes capabilities to upstream tools/backends rather than replacing the application's own domain-specific entity pipeline. citeturn0search2turn0search14

Use it when:

```text
platform adapter would otherwise be expensive to implement
AND
Agent-Reach has a suitable backend
```

Do not use it for:

```text
Google Maps discovery
generic website crawling
entity matching
Excel generation
```

---

# 26. Export service

Endpoint:

```text
POST /runs/{run_id}/export
```

Pipeline:

```text
database
 ↓
validated query
 ↓
5 datasets
 ↓
Excel writer
 ↓
formatting
 ↓
validation
 ↓
file
```

Output:

```text
exports/
└── run_<id>/
    └── business_intelligence_<timestamp>.xlsx
```

---

# 27. Export validation

Before returning success:

```text
Sheet count == 5
Required columns present
Matched count consistent
Unmatched counts consistent
No duplicate Match IDs
All hyperlinks valid
All scores within 0–100
Threshold matches run
```

---

# 28. Logging

Every job should log:

```text
run_id
job_id
platform
URL/domain
stage
attempt
duration
status
error
```

Never log:

```text
passwords
session cookies
authentication tokens
private credentials
```

---

# 29. Backend failure isolation

A platform failure must not fail the entire run.

Example:

```text
Google = SUCCESS
Fresha = SUCCESS
Platform B = BLOCKED
Platform C = FAILED
```

Run:

```text
PARTIAL_SUCCESS
```

with clear frontend warnings.

---

# 30. Integration contract

Every adapter must return the same normalized envelope:

```json
{
  "platform": "fresha",
  "external_id": "...",
  "name": "...",
  "category": "...",
  "address": "...",
  "city": "...",
  "phone": "...",
  "email": "...",
  "website": "...",
  "profile_url": "...",
  "presence_status": "FOUND",
  "availability": {
    "supported": true,
    "bookable": true,
    "next_available": "..."
  },
  "source": {
    "url": "...",
    "scraped_at": "..."
  }
}
```

This contract is what makes multiple platforms mergeable.

---

# 31. Backend implementation order

1. Database
2. Domain models
3. Run API
4. Job queue
5. Google Maps adapter
6. Website enrichment
7. Platform registry
8. One platform adapter
9. Normalization
10. Matching engine
11. WebSocket events
12. Export
13. Additional platform adapters
14. Performance optimization
15. Packaging

Do not build ten platform adapters before the core pipeline works end-to-end.
