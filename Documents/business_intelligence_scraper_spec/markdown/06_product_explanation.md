# Document 6 — Product Explanation

## 1. Product definition

This application is a **local business intelligence discovery, enrichment, platform verification and matching system**.

A user enters:

```text
City
Categories
Confidence threshold
Platforms
```

The system then builds a structured business dataset by combining:

- Google Maps
- business websites
- social profiles
- selected booking/business platforms
- platform availability information where supported

The result is not simply a list of businesses.

It is a **cross-platform verified business dataset**.

---

# 2. Core problem solved

A normal Google Maps scraper gives:

```text
Business
Phone
Address
Website
Rating
```

But the user wants more:

```text
Business
   ↓
Website
   ↓
Phone
Email
Instagram
Facebook
LinkedIn
   ↓
Booking/platform presence
   ↓
Availability
   ↓
Cross-platform verification
   ↓
Confidence score
   ↓
Clean merged dataset
```

This application automates that entire chain.

---

# 3. Example

Input:

```text
City:
Mumbai

Categories:
Salon + Spa

Confidence:
80%

Platforms:
Automatic + Fresha
```

The system might discover:

### Google

```text
ABC Hair Studio
Phone: +91...
Website: abc.com
Instagram: @abchair
Address: Andheri West
```

### Fresha

```text
ABC Hair Studio
Phone: +91...
Profile: fresha.com/...
Address: Andheri W
Bookable: Yes
Next slot: ...
```

Matching:

```text
Name: 96%
Phone: 100%
Address: 90%
Website: 100%
Category: 100%
```

Final:

```text
Match Score = 96%
Threshold = 80%
Decision = MATCHED
```

The combined record appears in Sheet 3.

---

# 4. Why five sheets?

The five sheets deliberately separate source truth from merged intelligence.

```text
Sheet 1
Google source

Sheet 2
Platform source

Sheet 3
Verified combination

Sheet 4
Google records without verified platform match

Sheet 5
Platform records without verified Google match
```

This prevents data loss.

---

# 5. Why not directly merge everything?

Suppose:

```text
Google:
ABC Salon
Mumbai

Fresha:
ABC Salon
Mumbai

Booksy:
ABC Salon
Mumbai
```

These may be the same business.

But:

```text
Google:
ABC Salon
Andheri

Fresha:
ABC Salon
Bandra
```

may be different branches.

The system therefore calculates identity rather than assuming identity.

---

# 6. Confidence score

The score is not an AI-generated guess.

It is a deterministic mathematical result.

Example:

```text
Phone = 100%
Domain = 100%
Name = 94%
Address = 86%
City = 100%
Category = 80%
Social = 60%
```

Weighted:

```text
25 + 20 + 18.8 + 17.2 + 5 + 4 + 3
= 93%
```

If threshold is:

```text
80%
```

then:

```text
93 >= 80
→ MATCHED
```

If threshold is:

```text
95%
```

then:

```text
93 < 95
→ UNMATCHED
```

The same underlying data can therefore be evaluated with different thresholds without scraping again.

---

# 7. Platform directory

The platform directory is a major part of the product.

Instead of hardcoding:

```text
Salon → Fresha
```

the system stores:

```text
Platform
Categories
Country
Discovery capability
Availability capability
Adapter
Priority
```

Example:

```text
Fresha
├── Salon
├── Spa
├── Wellness
└── Beauty

Platform B
├── Restaurant
└── Cafe
```

Then:

```text
User chooses Salon
 ↓
Platform directory
 ↓
Fresha
 ↓
other mapped platforms
```

---

# 8. User can override automatic selection

The user may say:

```text
Category:
Salon

Automatic platforms:
Fresha
Booksy
Treatwell

Manual:
https://example.com
```

The system runs:

```text
Automatic platforms
+
manual platforms
```

This makes the platform directory useful without making it restrictive.

---

# 9. All-business mode

When the user selects:

```text
ALL BUSINESSES
```

the application uses the category registry.

Conceptually:

```text
All
├── Food
├── Beauty
├── Healthcare
├── Automotive
├── Professional Services
├── Retail
├── Real Estate
├── Education
├── Finance
├── Travel
├── Entertainment
└── Other
```

The system generates bounded searches per category.

This is much safer than sending an uncontrolled "all businesses" crawl.

---

# 10. Website enrichment

Google may provide:

```text
Website: abc.com
```

The system opens the website.

It searches:

```text
Homepage
Contact
About
Footer
Structured data
```

It may extract:

```text
Phone
Email
Instagram
Facebook
LinkedIn
YouTube
TikTok
WhatsApp
```

If no website was found:

```text
Website = No website found
```

But the system can still discover social/platform presence independently.

---

# 11. Platform verification

The system independently searches the selected platform.

Example:

```text
Google
Mumbai → Salons

Fresha
Mumbai → Salons
```

Both datasets are then normalized.

This is important.

The system should **not** simply take Google businesses and search their names one-by-one as its only discovery mechanism.

Independent platform discovery allows the system to find businesses that exist on the platform but were not discovered on Google.

---

# 12. Availability

Availability has two levels.

### Level 1 — presence

```text
Business exists on Fresha
```

### Level 2 — bookability

```text
Business allows booking
```

### Level 3 — slot

```text
Next available:
Today 5:30 PM
```

The system stores all three separately.

---

# 13. Availability is time-dependent

Suppose:

```text
10:00 AM
Next slot = 2:00 PM
```

At:

```text
1:30 PM
```

that may no longer be true.

Therefore:

```text
checked_at
```

is mandatory.

The dataset says:

> This was the availability state when checked.

It does not claim permanent availability.

---

# 14. Frontend as operator console

The frontend answers:

### What did I ask for?

```text
Mumbai
Salon
80%
Fresha
```

### What happened?

```text
1,240 Google
870 platform
```

### What succeeded?

```text
1,010 websites
710 matches
```

### What failed?

```text
12 errors
1 platform blocked
```

### Why did a match happen?

```text
93%
Phone + domain + name + address
```

### What remains unmatched?

```text
530 Google
160 platform
```

---

# 15. Excel as final business output

The UI is for operating the scraper.

Excel is for using the resulting data elsewhere.

Example uses:

```text
Lead research
Market research
Competitor analysis
Local business mapping
Platform presence analysis
Booking availability research
Business directory building
Sales research
```

The application itself does not need to perform outreach.

---

# 16. Why no LLM?

The problem is primarily deterministic.

For example:

```text
Does URL contain instagram.com?
```

No LLM required.

```text
Does phone match?
```

No LLM.

```text
Are domains identical?
```

No LLM.

```text
How similar are two addresses?
```

Use deterministic similarity.

```text
Does category map to a platform?
```

Use a directory/rule.

```text
Is a listing bookable?
```

Use platform adapter rules.

LLM can be added later for optional ambiguous classification, but the core product should not depend on it.

---

# 17. Why the architecture uses multiple scraping technologies

There is no single perfect scraper for every site.

### Google Maps scraper

Specialized discovery.

### Scrapling

Fast/adaptive website extraction and browser-backed fallback. citeturn0search1

### Playwright

Complex browser interactions.

### Crawlee

Optional orchestration/crawling framework with queues, retries, storage and browser management. citeturn0search0turn0search12

### Agent-Reach

Optional platform capability connector where useful, especially for supported social/platform backends. It is not the core Google/website crawler. citeturn0search3turn0search14

---

# 18. Why not use one giant scraper?

A giant scraper becomes:

```text
if website == X
if website == Y
if website == Z
...
```

This becomes difficult to maintain.

The adapter architecture instead creates:

```text
PlatformRegistry
      ↓
FreshaAdapter
BooksyAdapter
PlatformXAdapter
PlatformYAdapter
```

Each adapter owns its platform-specific logic.

---

# 19. How a new platform is added

Suppose tomorrow the user wants:

```text
NewPlatform.com
```

Implementation:

```text
platforms/
└── new_platform/
    ├── adapter.py
    ├── parser.py
    ├── discovery.py
    ├── availability.py
    └── tests/
```

Register:

```text
platform
category mappings
capabilities
adapter
```

The rest of the system remains unchanged.

---

# 20. How the complete system behaves

```text
                 USER
                  │
                  ▼
          SEARCH CONFIGURATION
                  │
       ┌──────────┴───────────┐
       ▼                      ▼
   GOOGLE MAPS          PLATFORM DIRECTORY
       │                      │
       │                 selected platforms
       │                      │
       ▼                      ▼
 GOOGLE RECORDS        PLATFORM RECORDS
       │                      │
       └──────────┬───────────┘
                  ▼
             NORMALIZATION
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
 WEBSITE ENRICHMENT    AVAILABILITY
        │                   │
        └─────────┬─────────┘
                  ▼
           MATCHING ENGINE
                  │
          ┌───────┴────────┐
          ▼                ▼
       MATCHED          UNMATCHED
          │                │
          └───────┬────────┘
                  ▼
             EXPORT ENGINE
                  │
       ┌──────────┼──────────┐
       ▼          ▼          ▼
   Google     Platform    Matched
       │
       ├── Google Unmatched
       └── Platform Unmatched
```

---

# 21. What the product is NOT

It is not:

- a SaaS product
- a CRM
- an email marketing system
- an LLM agent
- a generic browser agent
- an unrestricted anti-bot bypass system
- a cloud scraping farm

It is a:

> **local, deterministic, multi-source business intelligence and platform-verification application.**

---

# 22. Recommended implementation phases

## Phase 1 — Core

```text
Database
Run system
Google Maps
Website extraction
Excel export
```

## Phase 2 — Matching

```text
Normalization
Candidate generation
Scoring
Unmatched
```

## Phase 3 — Platform framework

```text
Platform directory
Generic adapter
One real platform
```

## Phase 4 — Availability

```text
Presence
Bookability
Slots
Timestamp
```

## Phase 5 — Frontend

```text
Run creation
Live progress
Data tables
Matching explanations
Exports
```

## Phase 6 — Reliability

```text
Retry
Resume
Cancellation
Memory control
Testing
```

## Phase 7 — Platform expansion

```text
Fresha
Booksy
Treatwell
Industry-specific platforms
```

---

# 23. Final product success criteria

The application succeeds when a user can say:

> "Find all salons in Mumbai, search Google and my selected booking platforms, collect their website/contact/social information, check platform presence and availability, match the same businesses at 80% confidence, show me why they matched, separate everything else into unmatched datasets, and give me a clean five-sheet Excel file."

And the system performs that workflow without requiring manual copying between websites.

---

# 24. Final architecture principle

The most important design decision is:

```text
DISCOVER
   ↓
ENRICH
   ↓
NORMALIZE
   ↓
VERIFY
   ↓
MATCH
   ↓
CLASSIFY
   ↓
EXPORT
```

Each stage is independent, observable, resumable and testable.

That makes the application maintainable as the number of supported business categories and platforms grows.
