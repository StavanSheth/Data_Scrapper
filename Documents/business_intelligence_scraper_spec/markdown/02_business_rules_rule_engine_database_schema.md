# Document 2 — Business Rules + Rule Engine + Database + Data Integrity + Database Schema

## 1. Purpose

This document defines the business logic that turns scraped records into trustworthy business entities.

The core rule is:

> A business is not considered successfully matched merely because two names look similar. Matching must be explainable, deterministic, configurable and reproducible.

---

# 2. Core entities

The system must distinguish:

1. Search Run
2. Business Entity
3. Source Record
4. Platform
5. Platform Listing
6. Website
7. Contact
8. Social Profile
9. Availability Snapshot
10. Match Candidate
11. Match Decision
12. Scrape Job
13. Scrape Event
14. Export
15. Category
16. Platform-Category Mapping

---

# 3. Database schema

SQLite is the default for the single-user laptop architecture.

## 3.1 `runs`

```sql
CREATE TABLE runs (
    id TEXT PRIMARY KEY,
    city_input TEXT NOT NULL,
    city_normalized TEXT NOT NULL,
    confidence_threshold REAL NOT NULL DEFAULT 0.80,
    category_mode TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    cancelled_at TEXT,
    total_google_records INTEGER DEFAULT 0,
    total_platform_records INTEGER DEFAULT 0,
    total_matched INTEGER DEFAULT 0,
    total_google_unmatched INTEGER DEFAULT 0,
    total_platform_unmatched INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);
```

---

## 3.2 `categories`

```sql
CREATE TABLE categories (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    parent_id TEXT,
    normalized_name TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY(parent_id) REFERENCES categories(id)
);
```

Example hierarchy:

```text
Beauty
├── Salon
├── Hair Salon
├── Nail Salon
└── Spa

Automotive
├── Garage
├── Car Repair
├── Car Detailing
└── Tyre Shop
```

---

## 3.3 `platforms`

```sql
CREATE TABLE platforms (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    base_url TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    discovery_supported INTEGER NOT NULL DEFAULT 0,
    availability_supported INTEGER NOT NULL DEFAULT 0,
    website_enrichment_supported INTEGER NOT NULL DEFAULT 0,
    generic_adapter_supported INTEGER NOT NULL DEFAULT 0,
    adapter_name TEXT,
    notes TEXT
);
```

---

## 3.4 `platform_category_mappings`

```sql
CREATE TABLE platform_category_mappings (
    id TEXT PRIMARY KEY,
    platform_id TEXT NOT NULL,
    category_id TEXT NOT NULL,
    priority INTEGER DEFAULT 100,
    enabled INTEGER DEFAULT 1,
    FOREIGN KEY(platform_id) REFERENCES platforms(id),
    FOREIGN KEY(category_id) REFERENCES categories(id),
    UNIQUE(platform_id, category_id)
);
```

This is what enables:

```text
Salon
 → Fresha
 → Booksy
 → Treatwell

Garage
 → Automotive platform A
 → Automotive platform B
```

---

# 4. Source records

A source record represents exactly what a platform returned.

```sql
CREATE TABLE source_records (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    platform_id TEXT,
    source_type TEXT NOT NULL,
    source_url TEXT,
    external_id TEXT,
    raw_name TEXT,
    raw_address TEXT,
    raw_phone TEXT,
    raw_email TEXT,
    raw_website TEXT,
    raw_category TEXT,
    raw_latitude REAL,
    raw_longitude REAL,
    raw_rating REAL,
    raw_review_count INTEGER,
    raw_payload TEXT,
    extraction_status TEXT NOT NULL,
    scraped_at TEXT NOT NULL,
    FOREIGN KEY(run_id) REFERENCES runs(id),
    FOREIGN KEY(platform_id) REFERENCES platforms(id)
);
```

`raw_payload` stores platform-specific fields as JSON.

---

# 5. Business entity

A normalized business is separate from source records.

```sql
CREATE TABLE businesses (
    id TEXT PRIMARY KEY,
    canonical_name TEXT NOT NULL,
    normalized_name TEXT NOT NULL,
    category_id TEXT,
    address TEXT,
    city TEXT,
    postal_code TEXT,
    country TEXT,
    latitude REAL,
    longitude REAL,
    phone_primary TEXT,
    email_primary TEXT,
    website_url TEXT,
    website_status TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(category_id) REFERENCES categories(id)
);
```

---

# 6. Business contacts

```sql
CREATE TABLE contacts (
    id TEXT PRIMARY KEY,
    business_id TEXT NOT NULL,
    type TEXT NOT NULL,
    value TEXT NOT NULL,
    normalized_value TEXT,
    source_record_id TEXT,
    confidence REAL,
    verified INTEGER DEFAULT 0,
    FOREIGN KEY(business_id) REFERENCES businesses(id)
);
```

Types:

```text
phone
email
website
```

---

# 7. Social profiles

```sql
CREATE TABLE social_profiles (
    id TEXT PRIMARY KEY,
    business_id TEXT NOT NULL,
    platform TEXT NOT NULL,
    profile_url TEXT NOT NULL,
    username TEXT,
    source_record_id TEXT,
    confidence REAL,
    verified INTEGER DEFAULT 0,
    FOREIGN KEY(business_id) REFERENCES businesses(id),
    UNIQUE(business_id, platform, profile_url)
);
```

Supported initial values:

```text
instagram
facebook
linkedin
youtube
x
tiktok
whatsapp
other
```

---

# 8. Platform listings

```sql
CREATE TABLE platform_listings (
    id TEXT PRIMARY KEY,
    business_id TEXT,
    platform_id TEXT NOT NULL,
    external_id TEXT,
    profile_url TEXT,
    listing_name TEXT,
    listing_category TEXT,
    listing_address TEXT,
    listing_phone TEXT,
    listing_rating REAL,
    listing_review_count INTEGER,
    presence_status TEXT NOT NULL,
    match_status TEXT NOT NULL,
    source_record_id TEXT,
    FOREIGN KEY(business_id) REFERENCES businesses(id),
    FOREIGN KEY(platform_id) REFERENCES platforms(id),
    FOREIGN KEY(source_record_id) REFERENCES source_records(id)
);
```

`business_id` remains nullable until matching is complete.

---

# 9. Availability snapshots

```sql
CREATE TABLE availability_snapshots (
    id TEXT PRIMARY KEY,
    platform_listing_id TEXT NOT NULL,
    availability_status TEXT NOT NULL,
    bookable INTEGER,
    next_available_at TEXT,
    timezone TEXT,
    checked_at TEXT NOT NULL,
    source_url TEXT,
    raw_payload TEXT,
    FOREIGN KEY(platform_listing_id) REFERENCES platform_listings(id)
);
```

Possible statuses:

```text
NOT_CHECKED
NOT_SUPPORTED
NOT_FOUND
FOUND_NOT_BOOKABLE
BOOKABLE
NO_SLOTS
TEMPORARILY_UNAVAILABLE
BLOCKED
FAILED
```

---

# 10. Match candidates

```sql
CREATE TABLE match_candidates (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    google_record_id TEXT NOT NULL,
    platform_record_id TEXT NOT NULL,
    name_score REAL,
    phone_score REAL,
    address_score REAL,
    domain_score REAL,
    city_score REAL,
    category_score REAL,
    social_score REAL,
    final_score REAL NOT NULL,
    threshold REAL NOT NULL,
    decision TEXT NOT NULL,
    explanation TEXT,
    created_at TEXT NOT NULL
);
```

---

# 11. Match rules

Recommended baseline weights:

| Signal | Weight |
|---|---:|
| Phone | 25 |
| Website/domain | 20 |
| Business name | 20 |
| Address | 20 |
| City | 5 |
| Category | 5 |
| Social/profile | 5 |
| **Total** | **100** |

Score is normalized to `0–100`.

### Strong identity overrides

If:

```text
phone exact match
AND
city compatible
```

then candidate can receive a strong-match boost.

If:

```text
website domain exact match
AND
name similarity >= 0.80
```

then strong candidate.

Never automatically merge solely because names match.

---

# 12. Name normalization

Convert:

```text
"ABC Salon & Spa Pvt. Ltd."
```

to a normalized representation such as:

```text
abc salon spa
```

Rules:

- lowercase
- Unicode normalize
- remove punctuation
- normalize ampersands
- remove common legal suffixes
- collapse whitespace
- preserve meaningful tokens
- do not remove category words blindly

Legal suffix dictionary:

```text
pvt ltd
private limited
llp
ltd
limited
inc
corp
corporation
co
company
```

---

# 13. Phone normalization

Normalize:

```text
+91 98765 43210
091-9876543210
9876543210
```

into a canonical international representation when country is known.

Do not compare raw phone strings.

---

# 14. Website/domain matching

Normalize:

```text
https://www.example.com/
http://example.com/about
```

to:

```text
example.com
```

Compare registrable domains.

Subdomains should generally be treated as same parent domain unless platform semantics indicate otherwise.

---

# 15. Address matching

Normalize:

- punctuation
- apartment/unit notation
- street abbreviations
- whitespace
- city
- postal code

Use token-based similarity rather than exact text comparison.

Example:

```text
"12 MG Road, Andheri West, Mumbai"
```

and

```text
"12 Mahatma Gandhi Rd, Andheri W, Mumbai"
```

should receive high similarity.

---

# 16. Category matching

Create a synonym dictionary.

Example:

```text
hair salon
hairdresser
hair studio
salon
```

may map to:

```text
Beauty > Hair Salon
```

But:

```text
car dealer
car repair
car garage
```

must not automatically be treated as identical categories.

Category matching should have:

```text
EXACT
PARENT_CHILD_COMPATIBLE
SYNONYM
RELATED
CONFLICTING
UNKNOWN
```

---

# 17. Platform selection rules

### User-selected platforms

If user explicitly selects a platform:

```text
include platform
```

regardless of category mapping, unless platform is disabled/unavailable.

### Auto-selected platforms

If:

```text
platform.category_mapping = enabled
```

then include platform.

### All-platform mode

If user selects:

```text
ALL
```

then include all active platforms that support discovery for the selected geography/category.

---

# 18. Website rules

If Google provides no website:

```text
website_status = NOT_FOUND
```

Do not infer a website merely from a business name.

If a website URL exists:

```text
website_status = FOUND
```

Then attempt:

1. homepage
2. contact page
3. about page
4. footer
5. social links
6. structured metadata

---

# 19. Social extraction rules

Priority:

1. explicit social `<a href>`
2. JSON-LD / metadata
3. footer links
4. known platform URL patterns

Do not claim a profile belongs to a business without sufficient evidence.

Store:

```text
profile_url
platform
username
confidence
source_url
```

---

# 20. Availability rules

Presence and availability are different.

Example:

```text
Fresha Found = YES
Fresha Bookable = NO
```

must remain possible.

Availability must always include:

```text
checked_at
timezone
source_url
status
```

No availability claim should be treated as timeless.

---

# 21. Unmatched rules

### Google unmatched

Google record has no platform candidate above threshold.

### Platform unmatched

Platform record has no Google candidate above threshold.

### Multiple candidates

If several candidates exceed threshold:

```text
select highest score
```

only if margin over second candidate is sufficient.

Recommended ambiguity rule:

```text
best_score >= threshold
AND
best_score - second_best_score >= 5
```

Otherwise:

```text
AMBIGUOUS
```

and send to manual review.

---

# 22. Manual threshold

User may enter:

```text
70
75
80
85
90
95
```

Frontend displays:

```text
Confidence Threshold: 80%
```

The backend stores the threshold with the run.

Changing threshold after a run must **not rewrite the historical run**.

Instead create a new matching evaluation against the same source records.

---

# 23. Data integrity rules

### Rule 1

Raw data is immutable after ingestion.

### Rule 2

Normalized data may be recalculated.

### Rule 3

Match decisions must reference exact source records.

### Rule 4

Exports reference run IDs.

### Rule 5

A failed scrape never becomes a "not found" result.

These are distinct:

```text
NOT_FOUND
FAILED
BLOCKED
NOT_SUPPORTED
```

### Rule 6

An empty email field means unknown, not verified absence.

### Rule 7

Availability is timestamped.

### Rule 8

A website missing from Google does not prove the business has no website.

It means:

```text
Google website = NOT_FOUND
```

The system may still discover one elsewhere.

---

# 24. Transaction boundaries

Each source-record insertion must be transactional.

Matching should be transactional at candidate-decision level.

Export should read from a consistent completed-run snapshot.

---

# 25. Data lifecycle

```text
RAW SOURCE
   ↓
NORMALIZED SOURCE
   ↓
CANONICAL BUSINESS
   ↓
MATCH CANDIDATE
   ↓
MATCH DECISION
   ↓
MERGED RESULT
   ↓
EXPORT
```

No stage should skip backward and mutate an earlier stage.

---

# 26. Five-sheet output mapping

## Sheet 1 — Google Data

Required columns:

```text
Run ID
Google Place ID
Business Name
Normalized Name
Category
Subcategory
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
Bookable
Next Available
Availability Status
Availability Checked At
Platform Rating
Review Count
Source Status
Scraped At
```

## Sheet 3 — Matched / Combined

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
Google Rating
Platform Rating
Match Score
Threshold
Match Decision
Match Explanation
Platform Presence
Bookable
Next Available
Availability Checked At
```

## Sheet 4 — Google Unmatched

Same Google fields plus:

```text
Best Platform Candidate
Best Candidate Score
Threshold
Unmatched Reason
```

## Sheet 5 — Platform Unmatched

Same platform fields plus:

```text
Best Google Candidate
Best Candidate Score
Threshold
Unmatched Reason
```

---

# 27. Excel usability

Every sheet must have:

- AutoFilter
- frozen header row
- Excel table
- sensible column widths
- wrapped long text
- hyperlinks for URLs
- date/time formatting
- percentage formatting for scores
- filters enabled on every column
- no merged cells inside data regions
- top row frozen
- optional conditional formatting for score/status

Recommended filters:

```text
Category
Platform
Website Status
Presence Status
Availability Status
Match Decision
Match Score
```

---

# 28. Rule engine implementation

The rule engine should expose:

```python
evaluate_platform_selection(context)
evaluate_website_status(record)
evaluate_social_candidate(candidate)
generate_match_candidates(google, platform)
score_match(candidate)
decide_match(score, threshold)
classify_unmatched(record)
evaluate_availability(result)
```

Rules should be pure wherever possible.

Example:

```python
decision = match_engine.evaluate(
    google_record,
    platform_record,
    threshold=0.80
)
```

Return:

```json
{
  "score": 0.91,
  "decision": "MATCHED",
  "components": {
    "phone": 1.0,
    "domain": 1.0,
    "name": 0.94,
    "address": 0.86,
    "city": 1.0,
    "category": 0.8,
    "social": 0.0
  },
  "explanation": [
    "Phone matched exactly",
    "Website domain matched",
    "Business name similarity 94%"
  ]
}
```

---

# 29. Database indexes

Recommended:

```sql
CREATE INDEX idx_source_run ON source_records(run_id);
CREATE INDEX idx_source_external ON source_records(platform_id, external_id);
CREATE INDEX idx_business_name ON businesses(normalized_name);
CREATE INDEX idx_business_phone ON businesses(phone_primary);
CREATE INDEX idx_business_city ON businesses(city);
CREATE INDEX idx_listing_platform ON platform_listings(platform_id);
CREATE INDEX idx_listing_external ON platform_listings(platform_id, external_id);
CREATE INDEX idx_match_run ON match_candidates(run_id);
CREATE INDEX idx_match_score ON match_candidates(final_score);
CREATE INDEX idx_availability_listing ON availability_snapshots(platform_listing_id);
```

---

# 30. Final business-rule principle

The application must distinguish:

```text
No data found
        ≠
Scraper failed
        ≠
Website blocked
        ≠
Platform unsupported
        ≠
Business not present
```

This distinction is one of the most important integrity requirements in the entire system.
