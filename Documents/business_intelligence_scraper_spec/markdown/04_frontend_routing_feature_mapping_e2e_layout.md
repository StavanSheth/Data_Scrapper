# Document 4 — Frontend + Routing + Feature Mapping + E2E Business Flows + Layout + Styling + Backend/Database Connections

## 1. Frontend objective

The frontend must make the entire scraping pipeline observable.

The user must never need to inspect terminal logs to understand:

- what was searched
- which platforms were selected
- how many records were found
- which websites existed
- which businesses matched
- why a match received its score
- which platforms were unavailable
- why records are unmatched
- whether availability was checked
- whether the run partially failed

The frontend is therefore an **operator console**, not a marketing website.

---

# 2. Main navigation

```text
Dashboard
Run New Search
Runs
Businesses
Matches
Platforms
Platform Directory
Exports
Settings
Logs / Diagnostics
```

---

# 3. Routes

```text
/
 /dashboard
 /runs
 /runs/new
 /runs/:runId
 /runs/:runId/google
 /runs/:runId/platforms
 /runs/:runId/matched
 /runs/:runId/unmatched/google
 /runs/:runId/unmatched/platforms
 /runs/:runId/availability
 /platforms
 /platforms/directory
 /platforms/:platformId
 /exports
 /settings
 /diagnostics
```

---

# 4. Dashboard

Purpose:

Show historical and current run status.

Elements:

```text
Total Runs
Completed
Partial
Failed
Businesses Discovered
Matches
Unmatched
Platforms Used
```

Recent runs table:

```text
Run ID
City
Categories
Threshold
Google Records
Platform Records
Matched
Unmatched
Status
Started
Completed
Open
```

Backend:

```text
GET /runs
```

Database:

```text
runs
```

---

# 5. New Search page

This is the most important screen.

## Section A — Location

```text
City
[ Mumbai                         ]
```

Validation:

```text
required
minimum 2 characters
```

---

## Section B — Categories

Options:

```text
○ Selected Categories
○ All Businesses
```

If selected:

```text
Search categories
☑ Restaurants
☑ Salons
☑ Garages
☑ Agencies
☐ Hospitals
...
```

Category chips:

```text
Restaurants ×
Salons ×
Garages ×
```

Backend source:

```text
GET /categories
```

Database:

```text
categories
```

---

# 6. Platform selection

Three modes:

```text
○ Automatic
○ Manual
○ Automatic + Manual
```

Automatic:

```text
Category
 ↓
Platform Directory
 ↓
Applicable platforms
```

Manual:

```text
Paste platform URL
[ https://example.com ]
```

Directory:

```text
☑ Fresha
☑ Platform B
☐ Platform C
```

The same selected platforms must appear in the run summary.

---

# 7. Confidence threshold

Slider/input:

```text
Match Confidence
[ 80 ] %
```

Display:

```text
70% → More matches, more false positives
80% → Balanced
90% → Strict
95% → Very strict
```

The user can type the value manually.

---

# 8. Search preview

Before Start:

```text
CITY
Mumbai

CATEGORIES
Restaurants
Salons
Garages

GOOGLE
Enabled

PLATFORMS
Fresha
Platform B
Platform C

MATCH THRESHOLD
80%

WEBSITE ENRICHMENT
Enabled

SOCIAL EXTRACTION
Enabled

AVAILABILITY
Enabled where supported
```

Buttons:

```text
[Run Preflight]
[Start Search]
```

---

# 9. Run monitor

After starting:

```text
Run #20261007-001
Mumbai
```

Progress bar:

```text
██████████████░░░░ 72%
```

Stage:

```text
CHECKING PLATFORM AVAILABILITY
```

Metrics:

```text
Google: 1,240
Platforms: 870
Websites: 1,010
Social profiles: 1,880
Matches: 710
Google unmatched: 530
Platform unmatched: 160
Errors: 12
```

---

# 10. Live activity panel

Show recent events:

```text
✓ Google business discovered
✓ Website found
✓ Instagram found
✓ Fresha listing found
✓ Match created: 93%
⚠ Platform B blocked
```

Backend:

```text
WebSocket /ws/runs/:runId
```

Fallback:

```text
GET /runs/:runId
```

---

# 11. Run detail layout

Tabs:

```text
Overview
Google Data
Platform Data
Matched
Google Unmatched
Platform Unmatched
Availability
Errors
```

This directly corresponds to the five output sheets plus operational information.

---

# 12. Google Data table

Columns:

```text
Business
Category
Phone
Email
Website
Instagram
Facebook
LinkedIn
Rating
Reviews
Address
Website Status
Source
```

Filters:

```text
Category
Website status
City
Rating
Has Instagram
Has Phone
Has Email
```

Actions:

```text
Open website
Open Google listing
Open social
View raw record
```

---

# 13. Platform Data table

Columns:

```text
Platform
Business
Category
Phone
Email
Website
Profile
Presence
Bookable
Next Available
Address
Rating
Reviews
Checked At
```

Filters:

```text
Platform
Category
Presence
Bookable
Availability
```

---

# 14. Matched table

Main columns:

```text
Business
Google Name
Platform Name
Platform
Match Score
Threshold
Decision
Phone Match
Domain Match
Address Match
Category Match
Availability
```

Score cell:

```text
93%
```

Clicking score opens:

### Match explanation drawer

```text
Final Score: 93%

Phone        100% × 25 = 25
Domain       100% × 20 = 20
Name          94% × 20 = 18.8
Address       86% × 20 = 17.2
City         100% × 5  = 5
Category      80% × 5  = 4
Social         60% × 5 = 3

TOTAL = 93.0%
```

This makes the deterministic matching explainable.

---

# 15. Unmatched Google

Display:

```text
Business
Category
Google URL
Website
Phone
Address
Best Platform Candidate
Best Score
Threshold
Reason
```

Example:

```text
ABC Garage
Best platform candidate: ABC Auto
Score: 72%
Threshold: 80%
Reason: address mismatch
```

---

# 16. Unmatched Platform

Display:

```text
Platform
Business
Platform URL
Category
Address
Phone
Best Google Candidate
Best Score
Threshold
Reason
```

---

# 17. Availability page

Cards:

```text
Platform
Presence
Bookable
Next Slot
Checked At
```

Example:

```text
Fresha
FOUND
BOOKABLE
Today 4:30 PM
Checked 2 minutes ago
```

Possible state colors should be subtle and consistent:

```text
Success
Warning
Error
Neutral
```

Do not rely on color alone; always display text.

---

# 18. Platform Directory page

Table:

```text
Platform
Base URL
Categories
Discovery
Availability
Adapter
Status
```

Filters:

```text
Category
Discovery supported
Availability supported
Active
```

Buttons:

```text
Add platform
Edit
Test
Disable
```

---

# 19. Platform configuration drawer

Fields:

```text
Platform Name
Base URL
Search URL pattern
Profile URL pattern
Supported categories
Discovery supported
Availability supported
Requires browser
Adapter
Enabled
```

The system must not allow a platform to claim capabilities that its adapter does not implement.

---

# 20. E2E flow — normal search

```text
User
 ↓
New Search
 ↓
Enter city
 ↓
Select categories
 ↓
Select platforms
 ↓
Set threshold
 ↓
Preflight
 ↓
Start
 ↓
Backend creates Run
 ↓
Workers start
 ↓
Google discovery
 ↓
Platform discovery
 ↓
Website enrichment
 ↓
Availability
 ↓
Normalization
 ↓
Matching
 ↓
Unmatched classification
 ↓
Export
 ↓
Frontend shows results
```

---

# 21. E2E flow — no website

```text
Google record
 ↓
website = null
 ↓
website_status = NOT_FOUND
 ↓
platform discovery still runs
 ↓
social profiles may still be found
 ↓
record remains valid
```

Frontend:

```text
Website
No website found
```

This must not be shown as an error.

---

# 22. E2E flow — website exists

```text
Google
 ↓
website URL
 ↓
HTTP fetch
 ↓
contact extraction
 ↓
social extraction
 ↓
normalize
 ↓
save
```

Frontend:

```text
Website: Found
Phone: Found
Email: Found
Instagram: Found
```

---

# 23. E2E flow — browser fallback

```text
HTTP fetch
 ↓
JS required
 ↓
browser queue
 ↓
Playwright
 ↓
extract
 ↓
close/reuse context
```

The UI should show:

```text
Extraction method: Browser
```

This is useful for diagnostics.

---

# 24. E2E flow — platform match

```text
Google business
       +
Platform listing
       ↓
Candidate generation
       ↓
Score
       ↓
>= threshold?
   ├── YES → MATCHED
   └── NO  → UNMATCHED
```

Frontend reflects the exact backend decision.

---

# 25. E2E flow — rematching

User changes:

```text
80% → 90%
```

Frontend:

```text
POST /runs/{id}/rematch
```

Backend:

```text
existing source records
 ↓
recalculate candidates
 ↓
new decisions
```

Do not rescrape.

---

# 26. Styling system

Recommended:

```text
Background: neutral dark/light theme
Primary: deep green
Accent: restrained gold
Cards: low-radius / medium-radius
Borders: subtle
Tables: dense but readable
```

Use a professional data-operations interface rather than a consumer landing page.

Typography:

```text
Inter / system sans
```

Hierarchy:

```text
Page title: 24–30px
Section title: 16–20px
Body: 13–15px
Table: 12–14px
Metadata: 11–12px
```

---

# 27. Reusable frontend components

```text
AppShell
Sidebar
TopBar
PageHeader
MetricCard
StatusBadge
ProgressBar
DataTable
FilterBar
SearchInput
CategorySelector
PlatformSelector
ConfidenceSlider
RunSummary
ActivityFeed
MatchScoreBadge
MatchExplanationDrawer
AvailabilityCard
PlatformCard
ErrorPanel
ExportButton
```

---

# 28. State management

Global state:

```text
currentRun
runStatus
selectedFilters
platformDirectory
categories
settings
```

Server state should be fetched through query hooks.

Example:

```text
useRun(runId)
useRunBusinesses(runId, filters)
useMatches(runId)
usePlatforms()
useCategories()
```

Avoid putting the entire database into global frontend state.

---

# 29. Frontend/backend contract

Frontend never directly talks to:

```text
Google Maps
Fresha
Scrapling
Playwright
SQLite
```

Frontend only talks to:

```text
FastAPI
```

This ensures architecture separation.

---

# 30. Frontend/database relationship

```text
Frontend
  ↓
API
  ↓
Service
  ↓
Repository
  ↓
Database
```

Never:

```text
Frontend
  ↓
SQLite
```

---

# 31. Loading states

Every async operation requires:

```text
idle
loading
success
empty
partial
error
```

For scraping:

```text
queued
running
completed
failed
blocked
not_supported
```

---

# 32. Empty-state examples

No website:

```text
No website found from the current sources.
```

No platform:

```text
No listing found on selected platforms.
```

No availability:

```text
Availability could not be established.
Reason: platform does not expose bookable slots.
```

No match:

```text
No candidate reached the configured 80% threshold.
```

---

# 33. Export UI

Button:

```text
Export Excel
```

Dropdown:

```text
All 5 sheets
Google only
Platform only
Matched only
Unmatched only
```

Default:

```text
All 5 sheets
```

After export:

```text
Workbook generated successfully
5 sheets
1,240 Google records
870 platform records
710 matched
```

---

# 34. Responsive requirement

Primary target:

```text
Laptop 1280×720+
```

Must remain usable at:

```text
1366×768
1920×1080
```

Tables should horizontally scroll rather than compress critical fields.

---

# 35. Frontend acceptance criteria

A user must be able to:

1. Enter city.
2. Select one/multiple/all categories.
3. Select automatic/manual/all platform mode.
4. Change confidence threshold.
5. Run preflight.
6. Start run.
7. See live progress.
8. Inspect Google data.
9. Inspect platform data.
10. Inspect matches.
11. Inspect confidence explanations.
12. Inspect unmatched data.
13. Inspect availability.
14. Inspect failures.
15. Rematch with another threshold.
16. Export five-sheet workbook.

All of these must be backed by real API/database data, not mocked frontend state.
