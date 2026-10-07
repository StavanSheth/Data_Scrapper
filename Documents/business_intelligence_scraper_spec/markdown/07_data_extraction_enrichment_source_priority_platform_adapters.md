# Document 7 — Data Extraction, Enrichment, Source Priority & Platform Adapter Specification

**Project:** Local Single-User Business Intelligence Scraper  
**Document:** 07  
**Status:** Implementation Specification  
**Scope:** Google Maps + configurable business platforms + conditional official-website enrichment  
**Primary principle:** Deterministic, field-aware extraction without requiring an LLM/API key.

---

## 1. Purpose

This document defines exactly **what data is extracted, from which source, how missing fields are enriched, when the official website is visited, how platform presence is determined, how values are normalized, how provenance is retained, and how the final data is exposed to the database, frontend, and Excel exports**.

This document closes the field-level gap between the architectural documents and the actual extraction implementation.

### 1.1 Core requirements

The system shall:

1. Accept one city, multiple cities, or a supported city input.
2. Accept one, multiple, or all configured business categories.
3. Scrape Google Maps independently.
4. Scrape each selected business platform independently.
5. Use the same city/category input for Google and platform discovery.
6. Determine whether a business is **present on a platform**.
7. Match Google businesses against platform businesses using a configurable deterministic confidence threshold.
8. Send below-threshold/ambiguous records to unmatched outputs.
9. Extract contact and social fields from Google/platform sources where available.
10. Enrich missing fields from the official business website **only when required by the selected enrichment policy**.
11. Never discard a business simply because a website, contact field, or platform match is missing.
12. Preserve source provenance for every extracted field.
13. Show the same normalized result state in frontend, database, and exports.
14. Keep appointment-slot availability separate from current platform-presence requirements.

---

# 2. Scope Boundary: Presence vs Appointment Availability

## 2.1 Current requirement

**Platform availability means platform presence.**

Example:

> “Is Business X listed on Fresha?”

Current answer:

- `PRESENT`
- `NOT_FOUND`
- `UNCERTAIN`
- `ERROR`

It does **not** require:

- next appointment slot,
- live calendar availability,
- booking slot count,
- booking date/time.

## 2.2 Future optional availability layer

Appointment availability can later be implemented as a separate capability:

```text
Platform Presence
        |
        +---- PRESENT
                  |
                  +---- Optional Bookability Check
                              |
                              +---- Bookable
                              +---- Not Bookable
                              +---- Next Available
```

Do not mix these concepts in the core matching pipeline.

---

# 3. End-to-End Data Pipeline

```text
USER INPUT
  |
  +-- City
  +-- Category
  +-- Confidence Threshold
  +-- Platform Selection
  +-- Enrichment Policy
  +-- Requested Fields
  |
  v
RUN CONFIGURATION
  |
  +---------------------------+
  |                           |
  v                           v
GOOGLE MAPS DISCOVERY     PLATFORM DISCOVERY
  |                           |
  v                           v
GOOGLE NORMALIZATION       PLATFORM NORMALIZATION
  |                           |
  +------------+--------------+
               |
               v
       FIELD COMPLETENESS
               |
               v
      CONDITIONAL WEBSITE
          ENRICHMENT
               |
               v
       SOURCE MERGE + PROVENANCE
               |
               v
        DETERMINISTIC MATCHING
               |
       +-------+-------+
       |               |
       v               v
   MATCHED         UNMATCHED
       |               |
       +-------+-------+
               |
               v
        FINAL DATABASE
               |
       +-------+--------+
       |       |        |
       v       v        v
    FRONTEND  EXPORT   AUDIT
```

Google and platform scraping are independent branches. Website enrichment is a field-completeness branch, not merely a “platform failed” fallback.

---

# 4. User Configuration

## 4.1 Required inputs

| Input | Type | Default | Validation |
|---|---|---:|---|
| City | string/list | Required | Non-empty |
| Category | string/list/all | Required | Valid configured category |
| Match threshold | integer/float | 80% | 0–100 |
| Platforms | list | User-selected | Must exist in directory |
| Enrichment mode | enum | `MISSING_ONLY` | Valid enum |
| Enrichment fields | list | Contact + social | Valid field IDs |

## 4.2 Enrichment modes

### `MISSING_ONLY` — default

Only visit the official website if at least one requested field remains missing.

### `ALWAYS`

Visit the official website even if all requested fields already exist.

### `NEVER`

Never visit the official website.

## 4.3 Field selection

Recommended frontend controls:

```text
Website Enrichment

Mode:
(o) Only when information is missing
( ) Always enrich
( ) Never enrich

Fields to enrich:
[x] Phone
[x] Email
[x] Instagram
[x] Facebook
[x] LinkedIn
[x] WhatsApp
[x] Other social
```

The field list must control the actual crawler. The crawler must not collect unnecessary fields when the user has explicitly disabled them.

---

# 5. Canonical Business Record

The normalized internal business object should contain:

```text
BusinessRecord
├── identity
│   ├── business_id
│   ├── canonical_name
│   ├── normalized_name
│   ├── category
│   └── subcategory
│
├── location
│   ├── address
│   ├── street
│   ├── locality
│   ├── city
│   ├── state
│   ├── postal_code
│   ├── country
│   ├── latitude
│   └── longitude
│
├── contact
│   ├── phone
│   ├── alternate_phones
│   ├── email
│   └── whatsapp
│
├── web
│   ├── website
│   ├── website_status
│   └── website_domain
│
├── social
│   ├── instagram
│   ├── facebook
│   ├── linkedin
│   ├── youtube
│   ├── x
│   └── other
│
├── google
│   ├── place_id
│   ├── profile_url
│   ├── rating
│   ├── review_count
│   ├── opening_hours
│   └── status
│
├── platform
│   ├── platform_name
│   ├── listing_id
│   ├── listing_url
│   └── presence_status
│
├── provenance
│   └── field-level source metadata
│
└── audit
    ├── first_seen_at
    ├── scraped_at
    ├── extraction_run_id
    └── processing_status
```

---

# 6. Field-Level Extraction Dictionary

## 6.1 Identity fields

| Field | Primary source | Fallback | Validation |
|---|---|---|---|
| Business Name | Google/platform | Website title | Non-empty |
| Normalized Name | Internal | — | Deterministic |
| Category | Google/platform | User input | Category mapping |
| Subcategory | Source | Website | Optional |
| Listing ID | Platform/Google | URL-derived | Unique per source |
| Profile URL | Source | — | Valid URL |

### Name normalization

Apply:

1. Unicode normalization.
2. Lowercase.
3. Trim whitespace.
4. Collapse repeated whitespace.
5. Remove unnecessary punctuation.
6. Normalize `&` and `and`.
7. Remove obvious legal suffixes only through configurable rules.
8. Preserve meaningful words.
9. Store both original and normalized values.

Never overwrite the original source name.

---

# 7. Location Extraction

## 7.1 Required fields

- Full address
- Street
- Locality
- City
- State
- Postal code
- Country
- Latitude
- Longitude

## 7.2 Normalization

Normalize:

```text
"123, MG Road, Andheri West, Mumbai - 400058"
```

into:

```text
street       = 123 MG Road
locality     = Andheri West
city         = Mumbai
state        = Maharashtra
postal_code  = 400058
country      = India
```

The parser must be tolerant of missing components.

## 7.3 Geospatial checks

If coordinates exist:

- Validate latitude range `[-90, 90]`.
- Validate longitude range `[-180, 180]`.
- Detect impossible zero coordinates.
- Optionally calculate distance between Google and platform records.

Coordinates should contribute to matching when available, but absence must not invalidate the record.

---

# 8. Phone Extraction

## 8.1 Sources

Priority should be field-specific:

1. Google Maps
2. Official website
3. Platform
4. Other explicitly configured trusted source

## 8.2 Extraction methods

Website:

- `tel:` links
- visible phone text
- JSON-LD `telephone`
- contact-page structured data
- footer/header contact information

## 8.3 Normalization

Store:

```text
raw_phone
normalized_phone
country_code
phone_type
source
```

For India, normalize valid numbers toward E.164 where country context is known.

Do not blindly treat every 10-digit sequence as a phone number.

## 8.4 Validation

Reject obvious:

- dates,
- order IDs,
- postal codes,
- tracking IDs,
- repeated digit noise.

Multiple valid phones should be stored rather than silently discarded.

---

# 9. Email Extraction

## 9.1 Sources

1. Official website
2. Platform listing
3. Google-derived email where available

## 9.2 Extraction

Search:

- `mailto:`
- visible email strings
- JSON-LD
- contact/about pages
- footer/header
- structured metadata

## 9.3 Validation

Use a conservative email parser.

Store:

```text
email
normalized_email
is_verified_format
source_url
extraction_method
```

Format validation is not proof that the mailbox exists.

---

# 10. Website Extraction

## 10.1 Website acquisition

Initial website URL should normally come from the trusted source record, especially Google Maps or the platform listing.

Do not automatically invent a domain from the business name.

## 10.2 Website status

Use:

```text
FOUND
REACHABLE
REDIRECTED
BLOCKED
TIMEOUT
INVALID
NO_WEBSITE
PARTIAL
```

## 10.3 Domain normalization

Normalize:

```text
https://www.example.com/
http://example.com
example.com
```

to one canonical domain representation while retaining the original URL.

---

# 11. Conditional Website Enrichment Engine

This is one of the most important rules in the system.

## 11.1 Default rule

**The website must NOT always be scraped.**

The system first checks whether the requested fields are already complete.

### Decision tree

```text
FOR EACH BUSINESS

1. Read requested enrichment fields.

2. Check current values from Google + platforms + other
   trusted sources.

3. Are all requested fields complete?
      YES
        |
        +--> MISSING_ONLY mode?
        |       |
        |       +--> YES: SKIP WEBSITE
        |       +--> NO: continue according to mode
        |
        NO
        |
        v
4. Is official website available?
      NO
        |
        +--> Mark NO_WEBSITE
        +--> Keep business
        +--> Do not discard
      YES
        |
        v
5. Is enrichment mode NEVER?
      YES --> SKIP
      NO  --> SCRAPE TARGETED WEBSITE FIELDS
```

## 11.2 Explicit states

```text
SKIPPED_COMPLETE
SKIPPED_NEVER_MODE
REQUIRED
NO_WEBSITE
FAILED
PARTIAL
COMPLETED
```

---

# 12. Website Crawl Levels

The website crawler must progressively increase scope.

## Level 0 — No request

Condition:

```text
All requested fields complete
AND mode = MISSING_ONLY
```

Action:

```text
Do not visit website.
```

## Level 1 — Homepage

Extract only requested missing fields.

Typical sources:

- header
- footer
- visible contact section
- JSON-LD
- social links
- `mailto`
- `tel`

## Level 2 — Targeted contact pages

Try likely paths:

```text
/contact
/contact-us
/about
/about-us
/reach-us
/get-in-touch
```

Only when fields remain missing.

## Level 3 — Targeted business pages

Use only if necessary:

```text
/locations
/services
/book
/booking
```

Do not crawl the whole website by default.

## Level 4 — Browser fallback

Use a browser-backed crawler only when normal HTTP fetching cannot expose the required information.

Examples:

- JavaScript-rendered contact section
- client-side navigation
- dynamic social links

This level is intentionally expensive.

---

# 13. Field-Driven Crawl Rules

| Missing field | Pages to prioritize |
|---|---|
| Phone | Homepage → Contact → About |
| Email | Homepage → Contact → About |
| Instagram | Homepage → Footer → Contact → About |
| Facebook | Homepage → Footer → Contact |
| LinkedIn | Homepage → Footer → About |
| WhatsApp | Homepage → Contact → `wa.me`/WhatsApp links |
| Other social | Homepage → Footer → Contact/About |

If only Instagram is missing, the crawler should not scan unrelated service pages.

---

# 14. Website Social Extraction

Recognize official profile URLs for:

- Instagram
- Facebook
- LinkedIn
- YouTube
- X/Twitter
- WhatsApp
- TikTok
- Other configured platforms

## 14.1 Link normalization

Example:

```text
https://www.instagram.com/businessname/?hl=en
```

Normalize to the canonical profile URL while retaining the raw URL.

## 14.2 Official-link preference

A social URL directly linked from the official website receives higher trust than a guessed or externally discovered profile.

Do not assume a similarly named social account belongs to the business without sufficient evidence.

---

# 15. Platform Directory

The platform directory is the authoritative configuration source for platform adapters.

## 15.1 Platform record

```text
Platform
├── platform_id
├── name
├── base_url
├── enabled
├── categories
├── search_strategy
├── adapter_name
├── supported_fields
├── presence_method
├── rate_limit_config
└── notes
```

## 15.2 Category mapping

A platform can support:

```text
Beauty
Salon
Spa
Dental
Fitness
Healthcare
Restaurants
Hotels
Professional Services
...
```

Mappings should be configurable rather than hardcoded in business logic.

---

# 16. Platform Adapter Contract

Every platform adapter should implement a common interface.

```python
class PlatformAdapter:
    platform_name: str

    def supports_category(self, category) -> bool:
        ...

    def discover(self, city, category, config) -> list:
        ...

    def normalize(self, raw_record) -> PlatformRecord:
        ...

    def validate(self, record) -> ValidationResult:
        ...

    def get_presence(self, business_candidate) -> PresenceResult:
        ...

    def get_source_url(self, record) -> str:
        ...
```

Optional future interface:

```python
def get_booking_availability(record):
    ...
```

This must remain separate from `get_presence()`.

---

# 17. Platform Presence Logic

## 17.1 Presence states

```text
PRESENT
NOT_FOUND
UNCERTAIN
ERROR
```

## 17.2 Presence determination

A business should be considered present when the platform returns a sufficiently strong listing candidate and the identity can be validated.

Signals may include:

- business name
- address
- phone
- website
- city
- platform listing ID
- platform profile URL

## 17.3 No platform match

If no match is found:

```text
platform_presence = NOT_FOUND
```

The business remains in the dataset.

It must NOT be deleted.

---

# 18. Google Maps Extraction

Google Maps should be treated as an independent source.

Recommended canonical fields:

```text
Google Place ID
Business Name
Category
Address
City
Postal Code
Latitude
Longitude
Phone
Website
Rating
Review Count
Opening Hours
Google Profile URL
Status
Email (when available)
Images/thumbnail (optional)
Other Google metadata (optional)
```

A Google Maps scraper such as Gosom can provide a broad set of business fields and optional email extraction from business websites; the implementation should still map only the fields required by this specification. citeturn0search0

---

# 19. Website Scraper Technology Contract

The website enrichment layer should support:

```text
HTTP fetch
    ↓
HTML parser
    ↓
CSS/XPath/regex extraction
    ↓
Structured-data extraction
    ↓
Browser fallback if necessary
```

Scrapling is suitable for this layer because it supports HTTP fetching, dynamic/browser-backed fetching, adaptive extraction and CSS/XPath/regex-style selection. citeturn0search1

Recommended strategy:

```text
HTTP first
  ↓
Targeted pages
  ↓
Structured data
  ↓
Browser fallback
```

Do not start every website with a browser.

---

# 20. Source Provenance

Every meaningful field should retain provenance.

Minimum structure:

```text
FieldValue
├── value
├── source_type
├── source_url
├── source_record_id
├── extracted_at
├── extraction_method
├── confidence
└── verified
```

Example:

```json
{
  "field": "phone",
  "value": "+91XXXXXXXXXX",
  "source_type": "website",
  "source_url": "https://example.com/contact",
  "extraction_method": "tel_link",
  "confidence": 0.98,
  "verified": true
}
```

This prevents the system from losing the origin of merged values.

---

# 21. Field-Level Source Priority

There should not be one universal source priority.

## Phone

```text
Google / official website / platform
```

## Email

```text
Official website / platform / other trusted source
```

## Instagram/Facebook/LinkedIn

```text
Official website linked profile
    >
Platform-linked profile
    >
Other trusted source
```

## Address

```text
Google / platform
```

## Platform presence

```text
The platform itself
```

## Website

```text
Google/platform supplied official website
```

The merge engine must allow field-specific source priority.

---

# 22. Merge Rules

For each field:

```text
1. Collect all candidate values.
2. Normalize them.
3. Validate them.
4. Score source reliability.
5. Select canonical value.
6. Retain all credible alternatives.
7. Record provenance.
```

Never simply use:

```python
final_value = google_value or platform_value
```

because field-specific source reliability matters.

---

# 23. Missing Data States

Use explicit states rather than empty strings.

```text
FOUND
MISSING
NOT_APPLICABLE
NOT_REQUESTED
NO_WEBSITE
SCRAPE_FAILED
INVALID
CONFLICTING
```

Example:

```text
Instagram = MISSING
Website = FOUND
Website enrichment = REQUIRED
```

versus:

```text
Instagram = NOT_REQUESTED
```

These must not be treated as equivalent.

---

# 24. Matching Specification

## 24.1 Baseline weights

Recommended starting model:

| Signal | Weight |
|---|---:|
| Phone | 25% |
| Website/domain | 20% |
| Business name | 20% |
| Address | 20% |
| City | 5% |
| Category | 5% |
| Social/profile | 5% |
| **Total** | **100%** |

Weights must be configurable.

## 24.2 Decision

```text
best_score >= configured_threshold
AND
best_score - second_best_score >= ambiguity_margin
```

Recommended default ambiguity margin:

```text
5 percentage points
```

Otherwise:

```text
AMBIGUOUS
```

## 24.3 Threshold

Default:

```text
80%
```

Store the threshold used for every run.

---

# 25. Match Explanation

Every match must be explainable.

Example:

```text
Match Score: 91%

Phone:        +25
Website:      +20
Name:         +18
Address:      +18
City:          +5
Category:      +3
Social:        +2

Decision: MATCHED
Threshold: 80%
```

For unmatched:

```text
Best Candidate: XYZ Salon
Best Score: 73%
Threshold: 80%
Reason: BELOW_THRESHOLD
```

---

# 26. Unmatched Logic

## Google unmatched

Google record has no platform candidate above threshold.

## Platform unmatched

Platform record has no Google candidate above threshold.

## Ambiguous

A candidate exists but the confidence separation is insufficient.

## Error

Matching could not be evaluated because required source data was unavailable or processing failed.

---

# 27. Database Mapping

Recommended tables:

```text
businesses
business_contacts
business_social_profiles
source_records
platform_listings
platform_presence
website_enrichment_runs
field_provenance
match_candidates
match_results
```

## 27.1 `field_provenance`

Recommended fields:

```text
id
business_id
field_name
field_value
source_type
source_record_id
source_url
extraction_method
confidence
verified
extracted_at
run_id
```

## 27.2 `website_enrichment_runs`

```text
id
business_id
website_url
mode
requested_fields
crawl_level
status
pages_visited
fields_found
started_at
completed_at
error
```

---

# 28. Excel Output Mapping

## Sheet 1 — Google Data

Required:

```text
Run ID
Google Place ID
Business Name
Normalized Name
Category
Address
City
Postal Code
Latitude
Longitude
Phone
Email
Website
Website Status
Instagram
Facebook
LinkedIn
Other Socials
Rating
Review Count
Opening Hours
Google Profile URL
Source Status
Scraped At
```

## Sheet 2 — Platform Data

Required:

```text
Run ID
Platform
Platform Listing ID
Business Name
Normalized Name
Category
Address
City
Phone
Email
Website
Instagram
Facebook
LinkedIn
Platform URL
Presence Status
Platform Rating
Review Count
Source Status
Scraped At
```

## Sheet 3 — Matched / Combined

Required:

```text
Run ID
Match ID
Business Name
Google Name
Platform Name
Category
Google URL
Platform URL
Google Phone
Platform Phone
Google Website
Platform Website
Google Email
Platform Email
Google Address
Platform Address
Google Instagram
Platform Instagram
Match Score
Threshold
Match Decision
Match Explanation
Platform Presence
```

## Sheet 4 — Google Unmatched

Include:

```text
Google Record
Best Platform Candidate
Best Score
Threshold
Unmatched Reason
```

## Sheet 5 — Platform Unmatched

Include:

```text
Platform
Platform Record
Best Google Candidate
Best Score
Threshold
Unmatched Reason
```

---

# 29. Frontend Representation

Frontend must display the same canonical state as the backend.

For each business:

```text
Business
├── Source
│   ├── Google
│   └── Platform
│
├── Contact completeness
│   ├── Phone
│   ├── Email
│   └── Social
│
├── Website enrichment
│   ├── Required / Skipped
│   ├── Crawl level
│   └── Result
│
├── Platform presence
│   ├── Present
│   ├── Not found
│   ├── Uncertain
│   └── Error
│
└── Match
    ├── Score
    ├── Threshold
    ├── Decision
    └── Explanation
```

The frontend must not independently recompute authoritative business states.

---

# 30. API Contract

## Start run

```http
POST /api/runs
```

Payload:

```json
{
  "city": "Mumbai",
  "categories": ["Salon"],
  "platforms": ["fresha"],
  "match_threshold": 80,
  "enrichment": {
    "mode": "MISSING_ONLY",
    "fields": [
      "phone",
      "email",
      "instagram",
      "facebook",
      "linkedin",
      "whatsapp"
    ]
  }
}
```

## Business detail

```http
GET /api/runs/{run_id}/businesses/{business_id}
```

## Enrichment status

```http
GET /api/runs/{run_id}/businesses/{business_id}/enrichment
```

## Platform presence

```http
GET /api/runs/{run_id}/businesses/{business_id}/platforms
```

## Match explanation

```http
GET /api/runs/{run_id}/businesses/{business_id}/matches
```

---

# 31. Worker Flow

```text
RunWorker
 |
 +--> GoogleWorker
 |
 +--> PlatformWorker(s)
 |
 +--> NormalizeWorker
 |
 +--> CompletenessWorker
 |
 +--> WebsiteEnrichmentWorker
 |
 +--> MergeWorker
 |
 +--> MatchWorker
 |
 +--> ExportWorker
```

Website enrichment must only receive businesses whose policy evaluation says it is required.

---

# 32. Conditional Enrichment Pseudocode

```python
def should_enrich(business, requested_fields, mode):
    if mode == "NEVER":
        return False, "SKIPPED_NEVER_MODE"

    missing = [
        field for field in requested_fields
        if not is_complete(business, field)
    ]

    if not missing:
        if mode == "MISSING_ONLY":
            return False, "SKIPPED_COMPLETE"

    if not business.website:
        return False, "NO_WEBSITE"

    return True, missing
```

Then:

```python
should_run, reason_or_fields = should_enrich(
    business,
    requested_fields,
    enrichment_mode
)

if should_run:
    result = targeted_website_enrichment(
        business.website,
        missing_fields=reason_or_fields
    )
else:
    record_enrichment_state(reason_or_fields)
```

---

# 33. Important Business Scenarios

## Scenario A — Everything available from Google

```text
Google:
Phone ✓
Email ✓
Instagram ✓
Website ✓

Mode:
MISSING_ONLY

Result:
Website scraping = SKIPPED_COMPLETE
```

## Scenario B — Phone missing

```text
Google:
Phone ✗
Website ✓

Result:
Website enrichment = REQUIRED
Target:
Phone only
```

## Scenario C — No platform match

```text
Google = FOUND
Platform = NOT_FOUND
Website = FOUND
Email = MISSING
Instagram = MISSING

Result:
Platform presence = NOT_FOUND
Website enrichment = REQUIRED
Business retained
```

## Scenario D — No website

```text
Google = FOUND
Platform = NOT_FOUND
Website = NO_WEBSITE
Phone = MISSING
Email = MISSING

Result:
Website enrichment = NO_WEBSITE
Business retained
Missing fields remain explicitly missing
```

## Scenario E — Platform has phone, website has Instagram

```text
Google phone = missing
Platform phone = found
Website = found
Instagram = missing

Result:
Phone comes from platform
Website is scraped for Instagram
Both provenance records retained
```

## Scenario F — Always enrich

```text
Mode = ALWAYS

Even if:
Phone ✓
Email ✓
Instagram ✓

Website is visited.

Reason:
User explicitly requested full enrichment.
```

---

# 34. Performance Strategy

The enrichment layer must be conservative with laptop resources.

Recommended order:

```text
1. HTTP request
2. Parse HTML
3. Extract structured data
4. Visit only targeted pages
5. Browser fallback only when required
```

Recommended controls:

```text
max_concurrent_websites
max_pages_per_business
request_timeout
retry_count
crawl_delay
browser_concurrency
max_total_pages_per_run
```

For a 16 GB RAM laptop, browser concurrency should be deliberately capped and configurable.

---

# 35. Failure Handling

Every extraction step should be independently retryable.

Examples:

```text
GOOGLE_TIMEOUT
PLATFORM_TIMEOUT
WEBSITE_TIMEOUT
WEBSITE_BLOCKED
INVALID_WEBSITE
PARSER_ERROR
BROWSER_ERROR
MATCHING_ERROR
EXPORT_ERROR
```

A website failure must not fail the entire business record.

A platform failure must not fail Google extraction.

A Google failure must not prevent already completed platform records from being retained.

---

# 36. Deduplication

Deduplicate within each source before matching.

Priority signals:

```text
Google Place ID
Platform Listing ID
Canonical profile URL
Normalized phone
Normalized website domain
Name + address
```

Do not merge two businesses solely because names are identical.

---

# 37. Data Quality Rules

Every final record should receive:

```text
identity_quality
contact_quality
location_quality
website_quality
platform_quality
match_quality
overall_quality
```

Example:

```text
Identity: 100
Contact: 67
Location: 100
Website: 100
Platform: 100
Match: 92
Overall: 93
```

These scores are quality indicators, not match confidence.

---

# 38. Observability

Track:

```text
Businesses discovered
Businesses normalized
Platforms processed
Platform listings found
Businesses requiring website enrichment
Websites skipped
Websites crawled
Pages fetched
Fields recovered
Website failures
Matches
Unmatched Google
Unmatched platform
Ambiguous matches
Export rows
```

Frontend should show these metrics live.

---

# 39. Audit Trail

For each business, retain:

```text
Run ID
Source record IDs
Extraction timestamps
Website pages visited
Fields extracted
Field sources
Normalization version
Matching version
Threshold
Final decision
```

This allows the same run to be reproduced/debugged.

---

# 40. Security and Access Boundaries

The scraper should only access publicly available business information and normal publicly reachable pages.

The implementation must not:

- bypass authentication,
- bypass access controls,
- defeat CAPTCHAs,
- evade platform security mechanisms,
- access private customer information.

Respect applicable platform terms, robots/access restrictions, and rate limits.

---

# 41. Test Matrix

## Google

- [ ] Business with complete record
- [ ] Business without phone
- [ ] Business without website
- [ ] Duplicate Google result
- [ ] Closed business
- [ ] Invalid coordinate
- [ ] Multiple phone numbers

## Platforms

- [ ] Exact listing match
- [ ] Similar name
- [ ] Different address
- [ ] No listing
- [ ] Platform timeout
- [ ] Duplicate listing
- [ ] Category mismatch

## Website

- [ ] Complete data → skip
- [ ] Missing phone → targeted phone crawl
- [ ] Missing email → contact page
- [ ] Missing social → footer/homepage
- [ ] No website → no crawl
- [ ] Broken website
- [ ] Redirect
- [ ] JS-only page
- [ ] Browser fallback
- [ ] Website contains unrelated social link

## Matching

- [ ] 95% match
- [ ] 80% exact threshold
- [ ] 79% unmatched
- [ ] 85% vs 84% ambiguity
- [ ] Same-name businesses
- [ ] Same phone across duplicate records

---

# 42. Implementation File/Folder Specification

Recommended structure:

```text
backend/
├── app/
│   ├── extraction/
│   │   ├── google/
│   │   │   ├── client.py
│   │   │   ├── parser.py
│   │   │   ├── normalizer.py
│   │   │   └── mapper.py
│   │   │
│   │   ├── platforms/
│   │   │   ├── base.py
│   │   │   ├── registry.py
│   │   │   ├── directory.py
│   │   │   └── adapters/
│   │   │       ├── fresha.py
│   │   │       └── ...
│   │   │
│   │   └── website/
│   │       ├── crawler.py
│   │       ├── policy.py
│   │       ├── page_selector.py
│   │       ├── contact_extractor.py
│   │       ├── social_extractor.py
│   │       ├── structured_data.py
│   │       └── browser_fallback.py
│   │
│   ├── normalization/
│   │   ├── name.py
│   │   ├── phone.py
│   │   ├── email.py
│   │   ├── address.py
│   │   └── url.py
│   │
│   ├── matching/
│   │   ├── scorer.py
│   │   ├── signals.py
│   │   ├── decision.py
│   │   └── explanation.py
│   │
│   ├── provenance/
│   │   ├── models.py
│   │   └── service.py
│   │
│   └── workers/
│       ├── google_worker.py
│       ├── platform_worker.py
│       ├── enrichment_worker.py
│       ├── merge_worker.py
│       └── match_worker.py
│
├── tests/
│   ├── extraction/
│   ├── website/
│   ├── platforms/
│   ├── normalization/
│   ├── matching/
│   └── e2e/
│
└── config/
    ├── platforms.yaml
    ├── categories.yaml
    └── enrichment.yaml
```

Frontend:

```text
frontend/
├── src/
│   ├── features/
│   │   ├── enrichment/
│   │   ├── platforms/
│   │   ├── matching/
│   │   └── businesses/
│   │
│   ├── components/
│   │   ├── EnrichmentPolicyForm.tsx
│   │   ├── BusinessSourceBadge.tsx
│   │   ├── PlatformPresenceBadge.tsx
│   │   ├── MatchScore.tsx
│   │   └── ProvenanceDrawer.tsx
│   │
│   └── api/
│       ├── runs.ts
│       ├── businesses.ts
│       ├── enrichment.ts
│       └── platforms.ts
```

---

# 43. Configuration Example

```yaml
enrichment:
  default_mode: MISSING_ONLY

  fields:
    phone: true
    email: true
    instagram: true
    facebook: true
    linkedin: true
    whatsapp: true

  crawl:
    max_level: 3
    max_pages_per_business: 5
    http_timeout_seconds: 15
    browser_fallback: true

matching:
  threshold: 80
  ambiguity_margin: 5
```

---

# 44. Definition of Done

Document 7 is considered implemented only when:

### Extraction

- [ ] Every canonical field has a defined source.
- [ ] Every field has normalization rules.
- [ ] Every field has validation rules.
- [ ] Original values are retained where necessary.

### Enrichment

- [ ] Default mode is `MISSING_ONLY`.
- [ ] Complete records skip website scraping.
- [ ] Missing fields trigger targeted website enrichment.
- [ ] `NEVER` mode prevents website access.
- [ ] `ALWAYS` mode explicitly overrides completeness.
- [ ] No website does not delete the business.
- [ ] Website failure does not delete the business.

### Platforms

- [ ] Platform directory exists.
- [ ] Platform adapters share one interface.
- [ ] Platform presence is independent of appointment availability.
- [ ] No-match status is persisted.

### Matching

- [ ] Threshold is configurable.
- [ ] Threshold is stored per run.
- [ ] Ambiguity is handled.
- [ ] Match explanation is generated.

### Provenance

- [ ] Every merged field can identify its source.
- [ ] Website page/source URL is retained.
- [ ] Extraction timestamp is retained.

### Frontend

- [ ] Frontend displays backend states.
- [ ] Enrichment state is visible.
- [ ] Platform presence is visible.
- [ ] Match score and explanation are visible.
- [ ] Missing-data states are distinguishable.

### Export

- [ ] Five sheets are generated.
- [ ] Export values match canonical database values.
- [ ] Unmatched records are preserved.
- [ ] Source provenance can be inspected.

---

# 45. Final Canonical Rule Set

The implementation team should treat these rules as authoritative:

1. **Google Maps and platforms are independent discovery sources.**
2. **Platform presence is not appointment availability.**
3. **A platform no-match never deletes a business.**
4. **Website scraping is conditional by default.**
5. **Website scraping is field-driven, not blanket crawling.**
6. **If requested fields are complete, skip the website in `MISSING_ONLY` mode.**
7. **If requested fields are missing and an official website exists, scrape only what is needed.**
8. **If no website exists, retain the business and mark `NO_WEBSITE`.**
9. **If website scraping fails, retain the business and mark the enrichment failure.**
10. **If a platform listing exists but fields are still missing, website enrichment may still run.**
11. **Every final field should retain provenance.**
12. **Matching is deterministic and threshold-driven.**
13. **Ambiguous matches must not be silently accepted.**
14. **Frontend, database and Excel must represent the same canonical state.**
15. **HTTP extraction comes before browser extraction.**
16. **Browser execution is a fallback, not the default.**
17. **No LLM is required for the core extraction, enrichment, normalization or matching pipeline.**
18. **All platform-specific logic belongs inside adapters/configuration, not scattered through core business logic.**
19. **Appointment availability is a future optional layer and must not contaminate the current presence model.**
20. **The system must preserve partial data rather than treating missing fields as failed businesses.**

---

# Appendix A — Recommended Source/Field Matrix

| Field | Google | Platform | Website | Required |
|---|---:|---:|---:|---:|
| Business Name | ✓ | ✓ | ✓ | Yes |
| Category | ✓ | ✓ | ✓ | Yes |
| Address | ✓ | ✓ | ✓ | Yes |
| Phone | ✓ | ✓ | ✓ | Requested |
| Email | Optional | ✓ | ✓ | Requested |
| Website | ✓ | ✓ | — | Optional |
| Instagram | Optional | Optional | ✓ | Requested |
| Facebook | Optional | Optional | ✓ | Requested |
| LinkedIn | Optional | Optional | ✓ | Requested |
| WhatsApp | Optional | Optional | ✓ | Requested |
| Rating | ✓ | ✓ | — | Optional |
| Review Count | ✓ | ✓ | — | Optional |
| Platform Presence | — | ✓ | — | Yes for selected platforms |
| Appointment Availability | — | Future | — | No |

---

# Appendix B — Minimal Implementation Sequence

```text
1. Implement canonical schemas.
2. Implement Google extraction.
3. Implement platform adapter contract.
4. Implement one platform adapter.
5. Implement normalization.
6. Implement field completeness.
7. Implement website MISSING_ONLY policy.
8. Implement targeted website extraction.
9. Implement provenance.
10. Implement deterministic matching.
11. Implement unmatched handling.
12. Expose API.
13. Mirror state in frontend.
14. Export five sheets.
15. Add tests.
16. Add browser fallback.
17. Add more platform adapters.
18. Add optional appointment availability later.
```

**End of Document 7**
