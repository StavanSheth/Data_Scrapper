# Document 5 — Edge Cases + Security + Testing + Performance + Bugs + Production Readiness + Remediation

## 1. Production-readiness objective

Because this application is single-user and local, production readiness does **not** mean enterprise-scale infrastructure.

It means:

- predictable runs
- recoverable failures
- accurate data lineage
- no silent corruption
- controlled resource usage
- explainable matching
- reproducible exports
- safe local operation
- stable browser automation
- correct UI/backend synchronization

---

# 2. Edge-case matrix

| Edge case | Required behavior |
|---|---|
| City invalid | Preflight warning/error |
| City ambiguous | Ask user to choose/normalize |
| Category empty | Reject |
| All categories | Generate bounded category jobs |
| No Google results | Valid empty run |
| Duplicate Google records | Deduplicate |
| No website | `NOT_FOUND` |
| Website 404 | `DEAD` |
| Website timeout | `FAILED` |
| JS-only website | Browser fallback |
| Website blocked | `BLOCKED` |
| Social not found | `NOT_FOUND` |
| Platform unavailable | `PLATFORM_ERROR` |
| Platform not applicable | `NOT_SELECTED` |
| Platform listing absent | `NOT_FOUND` |
| Listing found | `FOUND` |
| Listing bookable | `BOOKABLE` |
| Listing has no slots | `NO_SLOTS` |
| Availability unsupported | `NOT_SUPPORTED` |
| Multiple matches | Ambiguous handling |
| Score below threshold | Unmatched |
| Exact phone match | Strong signal |
| Different phone but same domain | Candidate, not automatic certainty |
| Duplicate websites | Deduplicate |
| Same business multiple branches | Keep separate entities |
| Rate limiting | Backoff |
| Browser crash | Retry |
| Laptop sleep | Resume |
| Application crash | Resume queued jobs |
| Export crash | Rebuild from DB |
| User cancels | Stop safely |
| Partial platform failure | Keep successful results |

---

# 3. City resolution

Input:

```text
Mumbai
```

should resolve to a normalized city context.

Store:

```text
city_input
city_normalized
country
timezone
```

Do not silently substitute another city.

For ambiguous names:

```text
Springfield
```

the application should request disambiguation rather than guessing.

---

# 4. Google duplication

Possible duplicates:

```text
ABC Salon
ABC Salon - Andheri
ABC Salon Mumbai
```

Use:

1. Google Place ID/external ID where available.
2. Phone.
3. Domain.
4. Coordinates.
5. Name + address.

Branches must remain separate when physical location differs.

---

# 5. Website edge cases

### Redirect

Follow redirects within safe limits.

### HTTP → HTTPS

Treat same domain as same website.

### Domain expired

Mark:

```text
DEAD
```

### Website requires JavaScript

Use browser fallback.

### Website has no contact page

Search homepage/footer/JSON-LD.

### Website has multiple locations

Do not automatically assign every phone/address to every business branch.

---

# 6. Social edge cases

Possible false positives:

```text
Business name = "Royal Salon"
Instagram = @royal
```

This is insufficient.

Use evidence:

```text
website link
matching business name
matching city
matching phone/email if public
bio similarity
```

If confidence is insufficient:

```text
social_status = UNVERIFIED
```

---

# 7. Platform edge cases

### Platform has search but no public availability

```text
presence = FOUND
availability = NOT_SUPPORTED
```

### Platform requires login

```text
availability = AUTH_REQUIRED
```

### Platform uses a different city naming convention

Normalize location before comparing.

### Platform has multiple branches

Match at branch level.

### Platform has same business with slightly different name

Matching engine handles normalization.

---

# 8. Availability edge cases

Availability is volatile.

Never store only:

```text
available = true
```

Store:

```text
available
checked_at
timezone
next_slot
source_url
```

If the slot disappears later, the previous snapshot remains historically correct.

---

# 9. Matching false positives

High-risk scenario:

```text
ABC Dental
ABC Dental
```

same city but different address.

Rule:

```text
name match alone is insufficient.
```

High-risk scenario:

```text
ABC Salon
ABC Salon & Spa
```

same name but different phone/address.

Do not merge unless threshold and identity evidence support it.

---

# 10. Matching false negatives

Example:

```text
Sharma Auto Garage
Sharma Motors
```

same phone and address.

A strong phone/domain/address match should compensate for name differences.

---

# 11. Ambiguity state

Add:

```text
AMBIGUOUS
```

when:

```text
best score >= threshold
AND
second best is too close
```

Example:

```text
Candidate A = 91
Candidate B = 89
threshold = 80
```

Do not blindly choose A.

---

# 12. Security model

Even though this is local, apply baseline security.

## Input validation

Validate:

- URLs
- city names
- category IDs
- platform IDs
- thresholds
- export paths

## SSRF protection

Because users can provide platform URLs, the backend must restrict dangerous targets.

Block:

```text
localhost
127.0.0.1
0.0.0.0
private IP ranges
metadata endpoints
file://
```

unless explicitly required for local configuration.

Do not allow arbitrary URL fetching to become a local-network attack surface.

---

# 13. Credential security

If a platform ever requires login:

- never store passwords in database plaintext
- never log cookies
- never log session tokens
- use OS/browser profile storage where appropriate
- make authentication optional
- clearly indicate authentication state

Do not implement CAPTCHA or access-control bypassing.

---

# 14. File-system security

Exports must remain inside an application-controlled directory.

Reject paths containing traversal:

```text
../
..\ 
```

Use generated filenames.

---

# 15. Database safety

Enable:

```text
SQLite WAL
foreign_keys = ON
busy_timeout
```

Back up database before destructive migrations.

Never delete historical runs automatically.

---

# 16. Browser security

Use:

```text
context isolation
limited permissions
controlled downloads
download directory
timeouts
page limits
```

Do not let scraped websites execute arbitrary local filesystem operations through the application.

---

# 17. Rate limiting

Even single-user applications need crawler-level rate control.

For each domain:

```text
concurrency limit
delay/backoff
retry cap
```

On HTTP 429:

```text
exponential backoff
```

Do not aggressively retry.

---

# 18. Robots and platform terms

The system should respect applicable website terms, access restrictions and robots directives where relevant.

The architecture must not be designed around bypassing CAPTCHAs, authentication barriers or other technical access controls.

---

# 19. Testing pyramid

```text
          E2E
        /-----\
      Integration
    /-----------\
       Unit
  /---------------\
```

---

# 20. Unit tests

Test:

### Normalization

```text
name
phone
email
URL
address
category
```

### Matching

```text
exact
near match
false positive
false negative
threshold boundary
ambiguous candidates
```

### Platform rules

```text
selected
auto-selected
disabled
unsupported
```

### Availability

```text
bookable
not bookable
no slots
unsupported
failed
```

---

# 21. Integration tests

Test:

```text
Google → DB
Platform → DB
Website → DB
Matching → DB
Export → XLSX
```

Verify row counts.

---

# 22. Contract tests

Every adapter must pass:

```text
returns normalized record
returns source URL
returns status
does not crash on missing optional fields
```

---

# 23. Frontend E2E tests

Use Playwright.

Flow:

```text
Open application
→ New Search
→ Enter Mumbai
→ Select Salon
→ Select Fresha
→ Set 80
→ Start
→ Wait for completion
→ Open Matched
→ Open score
→ Export
→ Verify 5 sheets
```

---

# 24. Failure E2E

Simulate:

```text
website timeout
platform 404
platform 500
browser crash
cancel run
restart app
resume run
```

---

# 25. Data-integrity tests

After every test run:

```text
matched + google_unmatched <= google_records
matched + platform_unmatched <= platform_records
```

If one Google record can map to multiple platform listings intentionally, test cardinality rules explicitly.

---

# 26. Performance targets

For laptop operation:

### Startup

```text
< 5 seconds
```

### UI interactions

```text
< 200 ms for local state
< 1 second for normal API query
```

### Database

Paginated queries:

```text
< 500 ms target
```

### Browser

No more than:

```text
2–4 concurrent contexts
```

unless memory tests demonstrate safety.

---

# 27. Memory management

Avoid:

```python
all_pages = []
all_html = []
all_records = []
```

for the entire run.

Instead:

```text
stream
normalize
persist
release
```

Use database pagination.

Do not keep thousands of browser pages alive.

---

# 28. CPU management

Use:

```text
HTTP tasks = high concurrency
browser tasks = low concurrency
matching = batched
export = streaming-ish row writes
```

Matching should first generate candidates rather than compare every Google record against every platform record.

---

# 29. Candidate generation optimization

Naive:

```text
N Google × M Platform
```

is expensive.

Use blocking keys:

```text
city
postal code
phone suffix
domain
name prefix
category
```

Example:

```text
Google Mumbai Salon
 ↓
only compare to Mumbai Salon candidates
```

Then calculate expensive fuzzy similarity.

---

# 30. Matching performance

Pipeline:

```text
Stage 1: exact domain/phone
Stage 2: city/category block
Stage 3: name similarity
Stage 4: address similarity
Stage 5: final score
```

This prevents unnecessary pairwise comparisons.

---

# 31. Caching

Cache:

```text
website fetch
platform profile
city resolution
category mapping
```

with timestamps.

Do not cache volatile availability indefinitely.

Availability cache should be short-lived.

---

# 32. Browser reuse

Preferred:

```text
Browser process
 ├── Context 1
 ├── Context 2
 └── Context 3
```

instead of:

```text
Chrome 1
Chrome 2
Chrome 3
...
```

---

# 33. Crash recovery

On application startup:

```text
find RUNNING jobs
 ↓
mark interrupted
 ↓
requeue retryable jobs
```

Do not mark them successful.

---

# 34. Bugs to explicitly guard against

### Bug 1 — failed scrape treated as no website

Fix:

```text
FAILED != NOT_FOUND
```

### Bug 2 — duplicate business branches merged

Fix:

```text
coordinates/address branch identity
```

### Bug 3 — score changes after run

Fix:

```text
store threshold + component scores
```

### Bug 4 — frontend displays stale status

Fix:

```text
WebSocket + REST reconciliation
```

### Bug 5 — browser process leak

Fix:

```text
context/page finally blocks
browser health checks
```

### Bug 6 — export does not equal database

Fix:

```text
export validation
```

### Bug 7 — platform-specific fields lost

Fix:

```text
raw_payload JSON
```

### Bug 8 — same business matched twice

Fix:

```text
one-to-many constraints + conflict resolution
```

---

# 35. Production readiness scorecard

Initial target:

| Area | Target |
|---|---:|
| Architecture | 95% |
| Database | 95% |
| Business rules | 95% |
| Matching | 90% |
| Google discovery | 90% |
| Website enrichment | 90% |
| Platform adapters | 85% per adapter |
| Availability | 80% per platform |
| Backend API | 95% |
| Workers | 90% |
| WebSocket | 90% |
| Frontend | 90% |
| Excel export | 95% |
| Security | 90% |
| Testing | 90% |
| Performance | 85% |
| Recovery | 90% |

The overall product should not be called production-ready until critical-path E2E tests pass.

---

# 36. Remediation priority

## P0 — must fix

- database corruption
- incorrect matching
- silent data loss
- wrong business merge
- wrong export
- credential leakage
- uncontrolled browser process creation
- run state inconsistency

## P1

- platform failures
- browser fallback
- availability reliability
- resume support
- WebSocket synchronization

## P2

- UI polish
- additional filters
- advanced analytics
- additional platform adapters

---

# 37. Definition of done

The application is ready for daily use when:

```text
[ ] City input works
[ ] Category selection works
[ ] All-category mode works
[ ] Platform directory works
[ ] Manual platform URL works
[ ] Google discovery works
[ ] Website enrichment works
[ ] Social extraction works
[ ] Platform discovery works
[ ] Availability works where supported
[ ] Matching works
[ ] Threshold is configurable
[ ] Match explanations work
[ ] Unmatched sheets work
[ ] Five-sheet export works
[ ] Resume works
[ ] Cancel works
[ ] Errors are visible
[ ] Browser memory is controlled
[ ] Database integrity tests pass
[ ] E2E tests pass
[ ] No critical P0 bugs remain
```

---

# 38. Final remediation philosophy

Do not solve every failure by adding more retries.

The correct order is:

```text
classify failure
 ↓
retry if transient
 ↓
fallback if appropriate
 ↓
record exact failure
 ↓
continue independent jobs
```

This prevents the scraper from becoming an infinite-retry application.
