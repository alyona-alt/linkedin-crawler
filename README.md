# LinkedIn Job Scraper

## Overview

This project scrapes job listings from LinkedIn using Selenium and cookie-based login. It filters jobs by language, detects tags, and extracts structured fields.

## Features

- Uses real LinkedIn session (via cookies)
- Filters jobs by English language using `langdetect`
- Tags jobs containing German language mentions
- Extracts the following fields:
  - jobURL
  - title
  - experienceLevel
  - company name
  - applicationCount
  - postedTime
  - location
  - companyURL
  - remote? (remote, on-site, hybrid)
  - easyApply? (yes/no)
  - tag (language)

## Filters Supported

| Filter             | Values / Description                               |
|--------------------|----------------------------------------------------|
| **Date Posted**     | Any time, Past 24h, Past Week, Past Month          |
| **Experience Level**| Internship, Entry level, Associate, Mid, Senior, Director|
| **Job Type**        | Full-time, Part-time, Contract, Temporary          |
| **Remote**          | On-site, Hybrid, Remote                            |
| **Location**        | Any country, city, or region                       |
| **Keyword**         | Free-text (e.g., "CRM", "Salesforce")              |
| **Easy Apply**      | Whether "Easy Apply" is enabled                    |

## Setup

1. Install dependencies:
```
pip install -r requirements.txt
```

2. Log into LinkedIn manually in Chrome.
3. Export cookies for `linkedin.com` using a browser extension.
4. Save cookies as `linkedin_cookies.json`.

5. Run script:
```python
from scraper import setup_driver_with_cookies

driver = setup_driver_with_cookies("linkedin_cookies.json")
driver.get("https://www.linkedin.com/jobs/search/?keywords=CRM")
# Add scraping logic here
```
